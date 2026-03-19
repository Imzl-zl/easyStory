from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from pathlib import Path

import yaml

from app.shared.runtime.errors import ConfigurationError, UnknownModelError

MODEL_TOKEN_RATIOS: dict[str, float] = {
    "default": 1.5,
}
DEFAULT_PRICING_PATH = Path(__file__).resolve().parents[5] / "config" / "model_pricing.yaml"


@dataclass(frozen=True)
class ModelPrice:
    input_per_1k: float
    output_per_1k: float
    context_window: int


class TokenCounter:
    def count(self, text: str, model: str = "default") -> int:
        return self.estimate(text, model)

    def estimate(self, text: str, model: str = "default") -> int:
        ratio = MODEL_TOKEN_RATIOS.get(model, MODEL_TOKEN_RATIOS["default"])
        return max(1, ceil(len(text) / ratio))


class ModelPricing:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or DEFAULT_PRICING_PATH
        self.version: str | None = None
        self._prices: dict[str, ModelPrice] = {}
        self._load(self.config_path)

    def _load(self, path: Path) -> None:
        if not path.exists():
            raise ConfigurationError(f"Model pricing config not found: {path}")
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        self.version = data.get("version")
        for model_name, info in data.get("models", {}).items():
            self._prices[model_name] = ModelPrice(**info)
        if not self._prices:
            raise ConfigurationError(f"Model pricing config has no models: {path}")

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        price = self._get_price(model)
        return (
            input_tokens * price.input_per_1k / 1000
            + output_tokens * price.output_per_1k / 1000
        )

    def get_context_window(self, model: str) -> int:
        return self._get_price(model).context_window

    def _get_price(self, model: str) -> ModelPrice:
        price = self._prices.get(model)
        if price is None:
            raise UnknownModelError(model)
        return price
