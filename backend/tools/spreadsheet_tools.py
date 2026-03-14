import csv
import os
from pathlib import Path
from typing import Any

import openpyxl

_BASE = Path(__file__).parent.parent.parent / "workspace" / "spreadsheets"


def _ensure_base():
    _BASE.mkdir(parents=True, exist_ok=True)


def _safe_path(filename: str) -> Path:
    resolved = (_BASE / filename).resolve()
    if not str(resolved).startswith(str(_BASE.resolve())):
        raise PermissionError(f"Path traversal detected: {filename!r}")
    return resolved


def _normalize_data(data: list, headers: list | None) -> tuple[list | None, list[list]]:
    """Normalize data to rows. Returns (headers, rows)."""
    if not data:
        return headers, []
    if isinstance(data[0], dict):
        if headers is None:
            headers = list(data[0].keys())
        rows = [[row.get(h, "") for h in headers] for row in data]
    else:
        rows = [list(row) for row in data]
    return headers, rows


def generate_xlsx(filename: str, data: list, headers: list | None = None) -> str:
    """Generate an .xlsx file in workspace/spreadsheets. Returns the file path."""
    _ensure_base()
    if not filename.endswith(".xlsx"):
        filename += ".xlsx"
    path = _safe_path(filename)

    headers, rows = _normalize_data(data, headers)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"

    if headers:
        ws.append(headers)
    for row in rows:
        ws.append(row)

    wb.save(str(path))
    return str(path)


def generate_csv(filename: str, data: list, headers: list | None = None) -> str:
    """Generate a .csv file in workspace/spreadsheets. Returns the file path."""
    _ensure_base()
    if not filename.endswith(".csv"):
        filename += ".csv"
    path = _safe_path(filename)

    headers, rows = _normalize_data(data, headers)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if headers:
            writer.writerow(headers)
        for row in rows:
            writer.writerow(row)

    return str(path)
