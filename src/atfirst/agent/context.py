from collections.abc import Generator
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Self

from .toolcall import wrap

if TYPE_CHECKING:
    from .message import Message
    from .openai import MessageParam, ToolAnnotation
    from .toolcall import ToolWrapper


__all__ = ("Context",)


@dataclass
class _Lifecycle:
    _max_steps: int = field(default=5)
    _current_step: int = field(default=0)

    _is_terminated: bool = field(default=False)

    @property
    def is_terminated(self) -> bool:
        return self._is_terminated

    def terminate(self) -> None:
        """Terminate the lifecycle."""

        self._is_terminated = True

    def move_forward(self) -> None:
        self._current_step += 1

        if self._current_step >= self._max_steps:
            self.terminate()


@dataclass
class Context:
    """Context for openai based agent"""

    _system_messages: list["Message"] = field(default_factory=list)
    _recordings: list["Message"] = field(default_factory=list)

    _tools: dict[str, "ToolWrapper"] = field(default_factory=dict)

    @classmethod
    def build_context(cls) -> Self:
        return cls()

    @contextmanager
    def build_lifecycle(self) -> Generator[_Lifecycle, None, None]:
        life_cycle = _Lifecycle()

        self._tools["terminate"] = wrap(life_cycle.terminate)

        try:
            yield life_cycle

        finally:
            life_cycle.terminate()

    def build_message(self) -> list["MessageParam"]:
        return [
            msg.to_openai_message(
                msg.id,
            )
            if msg.role == "tool"
            else msg.to_openai_message()
            for msg in [
                *deepcopy(self._system_messages),
                *deepcopy(self._recordings),
            ]
        ]

    def add_message(self, *message: "Message") -> None:
        for msg in message:
            if msg.role == "system":
                self._system_messages.append(msg)
            else:
                self._recordings.append(msg)

    def list_message(self) -> list["Message"]:
        return deepcopy(self._recordings)

    def get_last_message(self) -> "Message":
        if not self._recordings:
            raise ValueError("No message available")

        return deepcopy(self._recordings[-1])

    def add_tool(self, *tool: "ToolWrapper") -> None:
        for t in tool:
            if t.name in self._tools:
                raise ValueError(f"Tool `{t.name}` already exists")

            self._tools[t.name] = t

    def get_tool(self, name: str) -> "ToolWrapper | None":
        return self._tools.get(name)

    def list_tool(self) -> list["ToolWrapper"]:
        # Sequence fixed
        return sorted(deepcopy(self._tools).values(), key=lambda t: t.name)

    def list_tool_annotation(self) -> list["ToolAnnotation"]:
        return [tool.annotation for tool in self._tools.values()]
