from __future__ import annotations

from app.shared.runtime.token_counter import ModelPricing, TokenCounter

from .context_builder import ContextBuilder
from .source_loader import ContextSourceLoader
from .truncation import ContextTruncator


def create_context_builder(
    *,
    token_counter: TokenCounter | None = None,
    model_pricing: ModelPricing | None = None,
    source_loader: ContextSourceLoader | None = None,
    truncator: ContextTruncator | None = None,
) -> ContextBuilder:
    resolved_token_counter = token_counter or TokenCounter()
    resolved_model_pricing = model_pricing or ModelPricing()
    resolved_source_loader = source_loader or ContextSourceLoader()
    resolved_truncator = truncator or ContextTruncator(
        resolved_token_counter,
        resolved_model_pricing,
    )
    return ContextBuilder(
        token_counter=resolved_token_counter,
        model_pricing=resolved_model_pricing,
        source_loader=resolved_source_loader,
        truncator=resolved_truncator,
    )
