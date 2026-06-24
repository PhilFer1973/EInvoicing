from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.models.country_pack import CountryPack


REPO_ROOT = Path(__file__).resolve().parents[3]
COUNTRY_PACK_ROOT = REPO_ROOT / "country_packs"


class CountryPackNotFound(ValueError):
    pass


@lru_cache(maxsize=1)
def load_country_packs() -> tuple[CountryPack, ...]:
    packs: list[CountryPack] = []
    for pack_path in sorted(COUNTRY_PACK_ROOT.glob("*/pack.json")):
        with pack_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        packs.append(CountryPack(**data, raw=data))
    return tuple(sorted(packs, key=lambda pack: pack.display_name))


def get_country_pack(pack_id: str) -> CountryPack:
    for pack in load_country_packs():
        if pack.country_pack_id == pack_id:
            return pack
    raise CountryPackNotFound(f"Unknown country pack: {pack_id}")

