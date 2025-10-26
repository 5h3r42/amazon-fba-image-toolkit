import os
import re
import requests
from pathlib import Path
from io import BytesIO
from PIL import Image

# ---------- SETTINGS ----------
BASE_DIR = Path(__file__).parent
INPUT_FILE = BASE_DIR / "urls_products.txt"       # your data file
OUT_ROOT   = BASE_DIR / "images"                  # root output folder
TIMEOUT    = 20                                   # seconds
TARGET_W, TARGET_H = 800, 800                     # exact size
WEBP_QUALITY = 85
USER_AGENT = "Mozilla/5.0"
# ------------------------------

def short_title_slug(title: str, max_words: int = 6, max_len: int = 48) -> str:
    """Make a short, filesystem-safe folder name from the product title."""
    title = title.strip()
    # keep only letters, numbers, spaces and dashes
    title = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE)
    # collapse whitespace
    title = re.sub(r"\s+", " ", title).strip()
    # take first N words
    words = title.split(" ")[:max_words]
    slug = "-".join(words).lower()
    # collapse multiple dashes and trim
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    # limit length
    slug = slug[:max_len].rstrip("-")
    return slug or "product"

def download_bytes(url: str) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    r = requests.get(url, timeout=TIMEOUT, headers=headers)
    r.raise_for_status()
    return r.content

def to_exact_canvas_webp(img_bytes: bytes, dest_path: Path):
    """Resize proportionally, center on 800x800 white canvas, save WEBP quality=85."""
    img = Image.open(BytesIO(img_bytes)).convert("RGB")
    # scale to fit within TARGET_W x TARGET_H
    img.thumbnail((TARGET_W, TARGET_H), Image.LANCZOS)
    # create white canvas and center the image
    canvas = Image.new("RGB", (TARGET_W, TARGET_H), (255, 255, 255))
    x = (TARGET_W - img.width) // 2
    y = (TARGET_H - img.height) // 2
    canvas.paste(img, (x, y))
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dest_path, "WEBP", quality=WEBP_QUALITY)

def ensure_unique_folder(root: Path, base_slug: str) -> Path:
    """If folder exists, append -2, -3, ..."""
    attempt = 1
    candidate = root / base_slug
    while candidate.exists():
        attempt += 1
        candidate = root / f"{base_slug}-{attempt}"
    return candidate

def process_line(line: str, idx: int):
    if "\t" in line:
        urls_part, title = line.split("\t", 1)
    else:
        urls_part, title = line, f"product-{idx:03d}"

    slug = short_title_slug(title)
    out_dir = ensure_unique_folder(OUT_ROOT, slug)

    urls = [u.strip() for u in urls_part.split(";") if u.strip()]
    if not urls:
        print(f"⚠️  Line {idx}: no URLs found, skipping.")
        return

    print(f"\n📦 {title.strip()}  →  {out_dir.name}  ({len(urls)} image(s))")
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, url in enumerate(urls, start=1):
        try:
            img_bytes = download_bytes(url)
            webp_path = out_dir / f"{i}.webp"
            to_exact_canvas_webp(img_bytes, webp_path)
            print(f"✅ {webp_path}")
        except Exception as e:
            print(f"❌ {url} -> {e}")

def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    if not INPUT_FILE.exists():
        print(f"❌ Input file not found: {INPUT_FILE}")
        return
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    for idx, line in enumerate(lines, start=1):
        process_line(line, idx)
    print(f"\n✅ Done. All product folders saved under:\n{OUT_ROOT}")

if __name__ == "__main__":
    main()