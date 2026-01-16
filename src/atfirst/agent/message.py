from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Self
from uuid import uuid4

from .openai import ToolCall

if TYPE_CHECKING:
    from .openai import ChatCompletion, MessageParam, ToolCallParam


__all__ = ("Message",)


@dataclass
class Message:
    role: Literal["system", "assistant", "user", "tool"]

    content_type: Literal["text"]
    text: str | list[str] | None = field(default=None)

    tool_calls: list["ToolCallParam"] = field(default_factory=list)

    id: str = field(default_factory=lambda: uuid4().hex)

    @classmethod
    def from_completion(cls, completion: "ChatCompletion") -> Self:
        return cls(
            role="assistant",
            content_type="text",
            text=completion.choices[0].message.content,
            tool_calls=[
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in completion.choices[0].message.tool_calls or []  # type: ignore
                if isinstance(tool_call, ToolCall)
            ],
        )

    def to_openai_message(self, tool_call_id: str | None = None) -> "MessageParam":
        message: MessageParam = {"role": self.role, "content": []}  # type: ignore

        if self.role == "assistant" and self.tool_calls:
            message["tool_calls"] = self.tool_calls  # type: ignore

        match self.content_type:
            case "text":
                if self.text is None:
                    raise Exception("Text is required for text content type")

                if self.role == "tool":
                    # TODO: For deepseek tool schema
                    if tool_call_id is None:
                        raise Exception("Tool call id is required for tool role")

                    message["content"] = self.text  # type: ignore
                    message["tool_call_id"] = tool_call_id  # type: ignore

                else:
                    if isinstance(self.text, str):
                        self.text = [self.text]

                    message["content"] = [{"type": "text", "text": text} for text in self.text]  # type: ignore

                return message

            case _ as content_type:
                raise ValueError(f"Unknown content type: {content_type}")
