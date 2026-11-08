from dataclasses import dataclass, field


@dataclass
class RawLine:
    """One order line as extracted by either the LLM or the deterministic parser, before validation."""
    original_phrase: str
    raw_quantity: float | None = None        # the number the customer wrote, if any
    unit: str = "unknown"                    # "case" | "piece" | "unknown"
    sku: str | None = None
    confidence: float = 0.0
    alternative_skus: list[str] = field(default_factory=list)
    source: str = "keyword"                  # "alias" | "keyword" | "llm"
    ambiguous: bool = False
    notes: list[str] = field(default_factory=list)
