import shutil
import uuid
from pathlib import Path

import pytest

from app.shared.runtime.errors import ConfigurationError, UnknownModelError
from app.shared.runtime.token_counter import ModelPricing, TokenCounter

PROJECT_ROOT = Path(__file__).resolve().parents[4]
API_ROOT = Path(__file__).resolve().parents[2]
MODEL_PRICING_PATH = PROJECT_ROOT / "config" / "model_pricing.yaml"


def test_token_counter_estimate_uses_repository_default_ratio() -> None:
    counter = TokenCounter()

    assert counter.estimate("天地玄黄", "default") == 3


def test_token_counter_count_delegates_to_estimate() -> None:
    counter = TokenCounter()

    assert counter.count("hello", "default") == counter.estimate("hello", "default")


def test_model_pricing_loads_repository_config() -> None:
    pricing = ModelPricing(MODEL_PRICING_PATH)

    assert pricing.version == "2026-03-16"
    assert pricing.get_context_window("gpt-4o") == 128000


def test_model_pricing_calculates_cost() -> None:
    pricing = ModelPricing(MODEL_PRICING_PATH)

    cost = pricing.calculate_cost("gpt-4o", input_tokens=1000, output_tokens=500)

    assert cost == pytest.approx(0.0125)


def test_model_pricing_rejects_unknown_model() -> None:
    pricing = ModelPricing(MODEL_PRICING_PATH)

    with pytest.raises(UnknownModelError, match="unknown-model"):
        pricing.calculate_cost("unknown-model", 1, 1)


def test_model_pricing_rejects_missing_config() -> None:
    temp_root = API_ROOT / ".pytest-tmp" / uuid.uuid4().hex
    temp_root.mkdir(parents=True, exist_ok=True)
    missing_path = temp_root / "missing.yaml"

    try:
        with pytest.raises(ConfigurationError, match="not found"):
            ModelPricing(missing_path)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
