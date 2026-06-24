from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.country_pack import CountryPack, CountryPackList
from app.services.country_packs import CountryPackNotFound, get_country_pack, load_country_packs


router = APIRouter(prefix="/api/country-packs", tags=["country-packs"])


@router.get("", response_model=CountryPackList)
def list_packs() -> CountryPackList:
    return CountryPackList(country_packs=list(load_country_packs()))


@router.get("/{pack_id}", response_model=CountryPack)
def read_pack(pack_id: str) -> CountryPack:
    try:
        return get_country_pack(pack_id)
    except CountryPackNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

