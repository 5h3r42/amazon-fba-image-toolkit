from pathlib import Path
from typing import List

import gspread
from google.oauth2.service_account import Credentials

CREDS_FILE = Path("google-service-account.json")  # make sure the file exists here
SPREADSHEET_ID = "1JUn34EdZ98LQznxNswvFTpMTqZrr4Qj0-3hBkfrNqVo"
WORKSHEET_NAME = "Sheet1"  # change if your tab is named differently
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def load_sheet_rows() -> List[str]:
    if not CREDS_FILE.exists():
        raise FileNotFoundError(f"Credentials file missing: {CREDS_FILE}")
    creds = Credentials.from_service_account_file(str(CREDS_FILE), scopes=SCOPES)
    client = gspread.authorize(creds)
    worksheet = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
    records = worksheet.get_all_records()

    lines: List[str] = []
    for row in records:
        title = row.get("Title", "").strip()
        urls = []
        for key, value in row.items():
            if key.lower().startswith("url") and value:
                urls.append(value.strip())
        if not urls or not title:
            continue
        line = ";".join(urls) + "\t" + title
        lines.append(line)
    return lines


if __name__ == "__main__":
    for line in load_sheet_rows():
        print(line)
