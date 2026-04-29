"""backend/pipeline/sheets.py — Google Sheets read/write helpers."""
from __future__ import annotations

from backend.pipeline.config import PipelineConfig


def column_name(index: int) -> str:
    """Chuyen 0-based index thanh ten cot Excel (A, B, ..., Z, AA, ...)."""
    if index < 0:
        raise ValueError("Column index must be >= 0")
    name = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def read_sheet(sheets_svc, config: PipelineConfig) -> list[list[str]]:
    """Doc du lieu tu Google Sheet."""
    end_col = column_name(max(config.video_url_col, config.thumb_col))
    result = (
        sheets_svc.spreadsheets()
        .values()
        .get(spreadsheetId=config.spreadsheet_id, range=f"{config.sheet_name}!A:{end_col}")
        .execute()
    )
    return result.get("values", [])


def write_thumb_links(sheets_svc, config: PipelineConfig, row_index: int, links: list[str]) -> None:
    """Ghi link thumbnail vao cot chi dinh trong Sheet."""
    col = column_name(config.thumb_col)
    sheets_svc.spreadsheets().values().update(
        spreadsheetId=config.spreadsheet_id,
        range=f"{config.sheet_name}!{col}{row_index}",
        valueInputOption="RAW",
        body={"values": [[",".join(links)]]},
    ).execute()
