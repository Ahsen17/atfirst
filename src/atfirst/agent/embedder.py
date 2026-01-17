from dataclasses import dataclass

from .model import Model


@dataclass
class Embedder:
    model: Model

    async def aembed(self, input: str | list[str]) -> list[list[float]]:  # noqa: A002
        return await self.model.aembed(input)
