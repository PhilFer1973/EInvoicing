from __future__ import annotations

from app.adapters.base import CountryAdapter
from app.services.country_packs import get_country_pack


def get_adapter(country_pack_id: str) -> CountryAdapter:
    return CountryAdapter(get_country_pack(country_pack_id))

