from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import audit, country_packs, templates, uploads


app = FastAPI(
    title="E-Invoicing Workbench API",
    version="0.1.0",
    description="Milestone 1 API skeleton for workbook upload, canonical JSON and evidence-bundle previews.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(country_packs.router)
app.include_router(uploads.router)
app.include_router(audit.router)
app.include_router(templates.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
