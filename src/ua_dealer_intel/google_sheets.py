"""Volitelna synchronizacia do Google Sheets."""

from __future__ import annotations

from pathlib import Path

import gspread
import pandas as pd


def upload_workbook_to_google_sheets(
    sheet_id: str,
    credentials_path: str | Path,
    dataframes: dict[str, pd.DataFrame],
) -> None:
    client = gspread.service_account(filename=str(credentials_path))
    spreadsheet = client.open_by_key(sheet_id)

    for sheet_name, dataframe in dataframes.items():
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            worksheet.clear()
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=50)

        values = [list(dataframe.columns)] + dataframe.fillna("").astype(str).values.tolist()
        worksheet.update(values=values, range_name="A1")

