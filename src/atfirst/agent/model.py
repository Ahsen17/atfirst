import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pydantic import BaseModel

from .message import Message
from .openai import AsyncOpenAI, BadRequestError, omit

if TYPE_CHECKING:
    from .context import Context


__all__ = ("Model",)


@dataclass
class Model:
    id: str = field(default="not-provided")

    base_url: str = field(default="")
    api_key: str = field(default="")

    logitbias: dict[str, int] | None = field(default=None)
    top_p: float | None = field(default=None)
    temperature: float | None = field(default=None)
    max_tokens: int | None = field(default=None)

    attempt: int | None = field(default=None)
    timeout: float | None = field(default=None)

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = os.getenv("OPENAI_API_KEY", "not-provided")

        if self.attempt is None:
            self.attempt = 1

    @property
    def aclient(self) -> AsyncOpenAI:
        return AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
            max_retries=(self.attempt or 1) - 1,
        )

    async def aresponse(
        self,
        ctx: "Context",
        output_schema: type[BaseModel] | None = None,
    ) -> None:
        try:
            completion = await self.aclient.chat.completions.create(
                model=self.id,
                messages=ctx.build_message(),
                tools=ctx.list_tool_annotation(),
                logit_bias=self.logitbias if self.logitbias is not None else omit,
                top_p=self.top_p if self.top_p is not None else omit,
                temperature=self.temperature if self.temperature is not None else omit,
                max_tokens=self.max_tokens if self.max_tokens is not None else omit,
                response_format={
                    # TODO: deepseek openai api special json output schema
                    "type": "json_object",
                }
                if output_schema
                else omit,
                stream=False,
            )
        except BadRequestError as e:
            raise e

        ctx.add_message(Message.from_completion(completion))
