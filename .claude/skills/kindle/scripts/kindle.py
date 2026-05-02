# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "pymupdf>=1.24,<2",
#   "Pillow>=10.0,<12",
# ]
# ///
"""Prepare a PDF for Kindle: analyze, clean, convert to EPUB, open in Kindle Previewer 3."""
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def analyze_pdf_images(pdf_path: Path) -> list[dict]:
    """
    Inspect every image in the PDF.

    Returns a list of dicts with keys:
        page         — 0-based page index
        index        — image index on the page
        width/height — pixel dimensions
        colorspace   — e.g. "DeviceRGB"
        low_res      — True if shorter side < 150 px (likely blurry on Kindle)
    """
    import fitz

    doc = fitz.open(str(pdf_path))
    results = []

    for page_num, page in enumerate(doc):
        for img_index, img_info in enumerate(page.get_images(full=True)):
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            w, h = base_image["width"], base_image["height"]
            results.append({
                "page": page_num,
                "index": img_index,
                "width": w,
                "height": h,
                "colorspace": str(base_image.get("colorspace", "unknown")),
                "low_res": min(w, h) < 150,
            })

    doc.close()
    low_res_count = sum(1 for r in results if r["low_res"])
    print(f"[analyze] Found {len(results)} images ({low_res_count} low-res) across PDF.")
    return results


def clean_pdf(pdf_path: Path, out_dir: Path) -> Path:
    """Crop 10% from the top and bottom of every page to remove headers/footers."""
    import fitz

    output_path = out_dir / (pdf_path.stem + "_cleaned.pdf")
    doc = fitz.open(str(pdf_path))

    for page in doc:
        rect = page.rect
        page.set_cropbox(fitz.Rect(
            rect.x0,
            rect.y0 + rect.height * 0.10,
            rect.x1,
            rect.y1 - rect.height * 0.10,
        ))

    doc.save(str(output_path))
    doc.close()
    print(f"[clean] Cleaned PDF → {output_path.name}")
    return output_path


def extract_cover(pdf_path: Path, out_dir: Path) -> Path:
    """
    Extract the cover image from the PDF.

    Strategy:
    1. Pull the largest embedded image from page 0.
    2. Fall back to rendering page 0 at 2× resolution.
    """
    import io
    import fitz
    from PIL import Image

    output_path = out_dir / (pdf_path.stem + "_cover.png")
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    images = page.get_images(full=True)

    if images:
        largest = max(
            images,
            key=lambda info: doc.extract_image(info[0])["width"] * doc.extract_image(info[0])["height"],
        )
        base_image = doc.extract_image(largest[0])
        img = Image.open(io.BytesIO(base_image["image"]))
        img.save(str(output_path), "PNG")
        print(f"[cover] Extracted embedded cover → {output_path.name}")
    else:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        pix.save(str(output_path))
        print(f"[cover] Rendered page 1 as cover → {output_path.name}")

    doc.close()
    return output_path


def pdf_to_epub(pdf_path: Path, cover_path: Path, out_dir: Path) -> Path:
    """Convert a cleaned PDF to EPUB using Calibre's ebook-convert."""
    output_path = out_dir / (pdf_path.stem.removesuffix("_cleaned") + ".epub")

    result = subprocess.run(
        [
            "ebook-convert",
            str(pdf_path),
            str(output_path),
            "--output-profile", "kindle",
            "--cover", str(cover_path),
            "--margin-top", "10",
            "--margin-bottom", "10",
            "--margin-left", "10",
            "--margin-right", "10",
            "--level1-toc", "//h:h1",
            "--level2-toc", "//h:h2",
            "--no-chapters-in-toc",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ebook-convert failed:\n{result.stderr.strip()}")

    print(f"[convert] EPUB → {output_path.name}")
    return output_path


def preview_in_kindle_previewer(epub_path: Path) -> None:
    """Open the EPUB in Kindle Previewer 3 on macOS."""
    subprocess.run(["open", "-a", "Kindle Previewer 3", str(epub_path)])


def main():
    parser = argparse.ArgumentParser(description="Prepare a PDF for Kindle.")
    parser.add_argument("pdf_path", help="Path to the input PDF file")
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path).expanduser().resolve()
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = pdf_path.parent / f"{pdf_path.stem}_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== Kindle Formatter: {pdf_path.name} ===")
    print(f"    Output dir: {out_dir}\n")

    image_report = analyze_pdf_images(pdf_path)
    low_res = [r for r in image_report if r["low_res"]]
    if low_res:
        pages = sorted({r["page"] + 1 for r in low_res})
        print(f"  Warning: {len(low_res)} low-resolution image(s) on page(s) {pages} — may appear blurry on Kindle.")

    cleaned_pdf = clean_pdf(pdf_path, out_dir)
    cover_path = extract_cover(pdf_path, out_dir)
    epub_path = pdf_to_epub(cleaned_pdf, cover_path, out_dir)
    preview_in_kindle_previewer(epub_path)

    print(f"\n[done] EPUB ready for upload: {epub_path}")


if __name__ == "__main__":
    main()
