from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import gspread
from gspread.exceptions import WorksheetNotFound
from google.oauth2.service_account import Credentials

from download_images_by_product import short_title_slug

# --- Configuration ---
CREDS_FILE = Path("google-service-account.json")
SPREADSHEET_ID = "1JUn34EdZ98LQznxNswvFTpMTqZrr4Qj0-3hBkfrNqVo"
WORKSHEET_NAME = "Sheet1"
OUTPUT_WORKSHEET_NAME = "Product Metadata"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
FULL_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

STOP_WORDS = {
    "the",
    "and",
    "with",
    "for",
    "from",
    "into",
    "your",
    "this",
    "that",
    "a",
    "an",
    "of",
    "to",
    "on",
    "ml",
    "pack",
    "set",
}

GENDER_KEYWORDS = [
    ("women", "Women"),
    ("woman", "Women"),
    ("ladies", "Women"),
    ("female", "Women"),
    ("girls", "Women"),
    ("men", "Men"),
    ("man's", "Men"),
    ("male", "Men"),
    ("boys", "Men"),
    ("kids", "Unisex"),
    ("children", "Unisex"),
    ("unisex", "Unisex"),
]


def fetch_records() -> Tuple[List[Dict[str, str]], gspread.Spreadsheet]:
    if not CREDS_FILE.exists():
        raise FileNotFoundError(
            f"Credentials file missing. Expected at {CREDS_FILE.resolve()}"
        )
    try:
        creds = Credentials.from_service_account_file(str(CREDS_FILE), scopes=FULL_SCOPES)
    except ValueError:
        creds = Credentials.from_service_account_file(str(CREDS_FILE), scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
    records = worksheet.get_all_records()
    return records, spreadsheet


def trim_to_length(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    words = text.split()
    trimmed: List[str] = []
    total = 0
    for word in words:
        extra = len(word) if not trimmed else len(word) + 1
        if total + extra > limit - 1:
            break
        trimmed.append(word)
        total += extra
    return " ".join(trimmed).rstrip(",.;:-") + "…"


def normalise_price(value: str) -> str:
    if not value:
        return ""
    if isinstance(value, (int, float)):
        return f"£{value:.2f}"
    value = str(value).strip()
    if not value:
        return ""
    if value.startswith("£"):
        return value
    try:
        return f"£{float(value):.2f}"
    except ValueError:
        return value


def build_keywords(title: str, brand: str, category: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9']+", f"{brand} {title} {category}")
    keywords: List[str] = []
    seen = set()
    for token in tokens:
        normalised = token.lower()
        if normalised in STOP_WORDS or len(normalised) <= 2:
            continue
        if normalised not in seen:
            keywords.append(normalised)
            seen.add(normalised)
    return ", ".join(keywords[:15])


def detect_gender(title: str) -> str:
    lower = title.lower()
    for token, gender in GENDER_KEYWORDS:
        if re.search(rf"\b{re.escape(token)}\b", lower):
            return gender
    return "Unisex"


def compose_short_description(title: str, brand: str, category: str, price: str) -> str:
    parts = [
        f"{brand} {title}".strip(),
        f"{category} essential".strip(),
    ]
    if price:
        parts.append(f"Priced at {price}")
    return " | ".join(filter(None, parts))


def compose_long_description(
    title: str, brand: str, category: str, rating: str, asin: str
) -> str:
    lines = [
        f"Experience {title} from {brand}—a trusted {category.lower()} favourite.",
    ]
    if rating:
        lines.append(f"Customers rate it {rating} out of 5 for quality and results.")
    lines.append("Perfect for Amazon FBA listings with reliable performance data.")
    if asin:
        lines.append(f"ASIN: {asin}")
    return " ".join(lines)


def best_price(record: Dict[str, str]) -> str:
    return (
        normalise_price(record.get("Buy Box 🚚: Current"))
        or normalise_price(record.get("New: Current"))
        or normalise_price(record.get("List Price: Current"))
    )


def extract_main_image(record: Dict[str, str]) -> str:
    raw = record.get("Image", "")
    if not raw:
        return ""
    parts = [part.strip() for part in raw.split(";") if part.strip()]
    return parts[0] if parts else ""


def _as_str(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def build_rows(records: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for record in records:
        title = _as_str(record.get("Title", "")).strip()
        if not title:
            continue
        brand = _as_str(record.get("Brand", "")).strip() or "Unknown"
        category = _as_str(record.get("Categories: Root", "")).strip() or "General"
        price = best_price(record)
        rating = _as_str(record.get("Reviews: Rating", "")).strip()
        asin = _as_str(record.get("ASIN", "")).strip()
        slug = short_title_slug(title)
        main_image_url = extract_main_image(record)

        row = {
            "Product Title": title,
            "SEO Title (<=60)": trim_to_length(title, 60),
            "Meta Description (<=160)": trim_to_length(
                f"Shop {title} by {brand}, a standout in {category.lower()} on Amazon. "
                "Great choice for FBA sellers seeking steady demand.",
                160,
            ),
            "Short Description": compose_short_description(
                title, brand, category, price
            ),
            "Long Description": compose_long_description(
                title, brand, category, rating, asin
            ),
            "Keywords": build_keywords(title, brand, category),
            "Category (Suggested)": category,
            "Target Gender": detect_gender(title),
            "Brand": brand,
            "Image Folder": f"images/{slug}",
            "Main Image File": "1.webp",
            "Price": price,
            "Main Image Source": main_image_url,
        }
        rows.append(row)
    return rows


def write_csv(rows: List[Dict[str, str]]) -> Path:
    raise NotImplementedError("CSV export is no longer supported; data is pushed to Sheets.")


def push_to_sheet(spreadsheet: gspread.Spreadsheet, rows: List[Dict[str, str]]) -> None:
    if not rows:
        raise ValueError("No data rows generated from the sheet.")
    headers = list(rows[0].keys())
    data = [headers] + [[row[h] for h in headers] for row in rows]
    try:
        worksheet = spreadsheet.worksheet(OUTPUT_WORKSHEET_NAME)
    except WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=OUTPUT_WORKSHEET_NAME, rows=str(len(data) + 20), cols=str(len(headers) + 5)
        )
    worksheet.clear()
    worksheet.resize(rows=len(data), cols=len(headers))
    worksheet.update("A1", data)


def main() -> None:
    records, spreadsheet = fetch_records()
    rows = build_rows(records)
    push_to_sheet(spreadsheet, rows)
    print(
        f"✅ Exported {len(rows)} product rows to worksheet '{OUTPUT_WORKSHEET_NAME}' "
        f"in spreadsheet {SPREADSHEET_ID}"
    )


if __name__ == "__main__":
    main()
