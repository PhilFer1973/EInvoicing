from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from openpyxl import Workbook

from app.services.workbook import REQUIRED_COLUMNS


router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("/workbook")
def download_workbook_template() -> StreamingResponse:
    workbook = Workbook()
    workbook.remove(workbook.active)

    for sheet_name, columns in REQUIRED_COLUMNS.items():
        sheet = workbook.create_sheet(sheet_name)
        sheet.append(columns)
        for column_index, column_name in enumerate(columns, start=1):
            sheet.cell(row=1, column=column_index).style = "Headline 3"
            sheet.column_dimensions[sheet.cell(row=1, column=column_index).column_letter].width = max(
                16,
                min(34, len(column_name) + 4),
            )

    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="e-invoicing-v1-template.xlsx"'},
    )

