"""DeepEval Ollama judge with reasoning disabled for short, structured scores."""

from __future__ import annotations

from deepeval.models import OllamaModel
from pydantic import BaseModel


class NoThinkingOllamaModel(OllamaModel):
    def _decode(self, content: str, schema: type[BaseModel] | None):
        return schema.model_validate_json(content) if schema else content

    def generate(self, prompt: str, schema: type[BaseModel] | None = None):
        response = self.load_model().chat(
            model=self.name,
            messages=[{"role": "user", "content": prompt}],
            think=False,
            format=schema.model_json_schema() if schema else None,
            options={"temperature": self.temperature, "num_predict": 768},
        )
        return self._decode(response.message.content or "", schema), 0

    async def a_generate(self, prompt: str, schema: type[BaseModel] | None = None):
        response = await self.load_model(async_mode=True).chat(
            model=self.name,
            messages=[{"role": "user", "content": prompt}],
            think=False,
            format=schema.model_json_schema() if schema else None,
            options={"temperature": self.temperature, "num_predict": 768},
        )
        return self._decode(response.message.content or "", schema), 0
