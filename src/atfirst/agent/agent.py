from collections.abc import Awaitable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from msgspec import json

from .context import Context
from .message import Message
from .util import Jinja2Renderer

if TYPE_CHECKING:
    from pydantic import BaseModel

    from .model import Model
    from .tool import ToolWrapper


__all__ = ("Agent",)


@dataclass
class Agent:
    model: "Model"

    description: str | None = field(default=None)
    instruction: str | None = field(default=None)

    output_schema: type["BaseModel"] | None = field(default=None)
    tools: list["ToolWrapper"] = field(default_factory=list)

    ctx: Context = field(default_factory=Context.build_context)

    def __post_init__(self) -> None:
        # Register tools
        self.ctx.add_tool(*self.tools)

    def _pre_configure(self) -> None:
        # Build system message
        self.ctx.add_message(
            Message(
                role="system",
                content_type="text",
                text=Jinja2Renderer.new("template").render(
                    "system",
                    description=self.description,
                    instruction=self.instruction,
                    tools=self.ctx.list_tool(),
                ),
            )
        )

    def _handle_input(self, input: str | Message | list[Message]) -> None:  # noqa: A002
        match input:
            case str():
                messages = [Message(role="user", content_type="text", text=input)]
            case Message():
                messages = [input]
            case list():
                messages = input
            case _:
                raise TypeError("Invalid input type")

        self.ctx.add_message(*messages)

    async def _handle_tool_calls(self) -> None:
        tool_call_msg = self.ctx.get_last_message()

        for tool_call in tool_call_msg.tool_calls:
            tool_name = tool_call["function"]["name"]
            tool_args = tool_call["function"]["arguments"]

            tool = self.ctx.get_tool(tool_name)

            if tool is None:
                # Tool not found
                tool_msg = f"Tool `{tool_name}` is not exist."

            else:
                # Execute tool function
                try:
                    result = tool.function(**json.decode(tool_args, type=dict[str, Any]))
                    tool_msg = await result if isinstance(result, Awaitable) else result

                except Exception as e:  # noqa: BLE001
                    tool_msg = f"Error executing tool {tool_name}: {e!s}."

            # Append tool message
            self.ctx.add_message(
                Message(
                    role="tool",
                    content_type="text",
                    text=tool_msg or "Tool execution success.",
                    id=tool_call["id"],
                )
            )

    async def _handle_output(self) -> "str | BaseModel | None":
        def _format(content: str | list[str] | None) -> str | None:
            match content:
                case str() as output:
                    return output
                case list() as output:
                    return "\n".join(output)
                case None:
                    return None

        answer: Message | None = None

        for msg in reversed(self.ctx.list_message()):
            if msg.role != "assistant":
                continue

            answer = msg

            break

        if answer is None or answer.text is None:
            return None

        if self.output_schema is None:
            return _format(answer.text)

        # Convert into request format
        ctx = Context.build_context()
        ctx.add_message(
            Message(
                role="system",
                content_type="text",
                text=[
                    "Collect information of assistant's information and convert into request format.",
                    f"<output_format type='json'>\n  {self.output_schema.model_json_schema()}\n</output_format>",
                ],
            ),
            Message(role="assistant", content_type="text", text=answer.text),
        )

        await self.model.aresponse(ctx, self.output_schema)
        if (output := _format(ctx.get_last_message().text)) is None:
            return None

        return self.output_schema.model_validate_json(output)

    async def arun(
        self,
        input: str | Message | list[Message],  # noqa: A002
    ) -> "str | BaseModel | None":
        with self.ctx.build_lifecycle() as life_cycle:
            self._pre_configure()
            self._handle_input(input)

            while not life_cycle.is_terminated:
                await self.model.aresponse(self.ctx)
                await self._handle_tool_calls()

                life_cycle.move_forward()

        return await self._handle_output()
