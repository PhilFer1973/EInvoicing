from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TaxSummaryLine(BaseModel):
    tax_category_code: str
    tax_rate: str
    taxable_amount: str
    tax_amount: str


class CanonicalInvoice(BaseModel):
    invoice: dict[str, Any] = Field(default_factory=dict)
    seller: dict[str, Any] = Field(default_factory=dict)
    buyer: dict[str, Any] = Field(default_factory=dict)
    lines: list[dict[str, Any]] = Field(default_factory=list)
    tax_summary: list[TaxSummaryLine] = Field(default_factory=list)
    totals: dict[str, Any] = Field(default_factory=dict)
    source: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

