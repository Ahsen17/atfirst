from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from docstring_parser import Docstring, parse

if TYPE_CHECKING:
    from ._openai import ToolAnnotation


__all__ = (
    "ToolWrapper",
    "wrap",
)


TYPE_MAPPING = {
    int: "integer",
    str: "string",
    bool: "boolean",
    float: "number",
    list: "array",
    dict: "object",
    int | None: "integer",
    str | None: "string",
    bool | None: "boolean",
    float | None: "number",
    list | None: "array",
    dict | None: "object",
    "int": "integer",
    "str": "string",
    "bool": "boolean",
    "float": "number",
    "list": "array",
    "dict": "object",
    "int | None": "integer",
    "str | None": "string",
    "bool | None": "boolean",
    "float | None": "number",
    "list | None": "array",
    "dict | None": "object",
}


@dataclass
class ToolWrapper:
    name: str
    description: str
    annotation: "ToolAnnotation"
    function: Callable[..., str | None | Awaitable[str | None]]


def _is_tool_anno_valid(docs: Docstring) -> bool:
    if docs.description is None:
        return False

    return all(param.type_name for param in docs.params)


def wrap(
    func: Callable[..., str | None | Awaitable[str | None]],
) -> ToolWrapper:
    """Wrap a function as a tool with metadata."""

    name: str = func.__name__

    if (document := func.__doc__) is None or not _is_tool_anno_valid(
        parsed_docs := parse(document),
    ):
        raise ValueError("Function tool must have full annotated docstring.")

    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    for param in parsed_docs.params:
        if param.type_name not in TYPE_MAPPING:
            raise ValueError(f"Unsupported type: {param.type_name}")

        type_name = TYPE_MAPPING[param.type_name]

        if "None" not in type_name:
            parameters["required"].append(param.arg_name)

        parameters["properties"][param.arg_name] = {
            "type": type_name,
            "description": param.description,
        }

    anno: ToolAnnotation = {
        "type": "function",
        "function": {
            "name": name,
            "description": parsed_docs.description.strip(),  # type: ignore
            "parameters": parameters,
            "strict": True,
        },
    }

    return ToolWrapper(
        name,
        parsed_docs.description.strip(),  # type: ignore
        anno,
        func,
    )
