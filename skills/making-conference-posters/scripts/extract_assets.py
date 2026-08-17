#!/usr/bin/env python3
"""Extract figures and tables from a paper PDF as poster-ready images.

Why not `pdfimages`: journal PDFs composite a raster panel with VECTOR text
drawn on top (column headers, axis labels, per-panel metrics). pdfimages
returns only the raster layer, so you silently get a figure with no labels.
Rendering the page and cropping keeps both layers.

Usage:
  S=<this-skill>/scripts   # wherever this skill is installed

  # 1. see what is on which page
  uv run --with pillow $S/extract_assets.py survey paper.pdf

  # 2. eyeball a whole page to find the crop box (coords are PIXELS in this render)
  uv run --with pillow $S/extract_assets.py crop paper.pdf --page 11 \
      --out /tmp/page.png --whole --ref-dpi 150

  # 3. cut the region out; --box is in pixels of a --ref-dpi render
  uv run --with pillow $S/extract_assets.py crop paper.pdf --page 11 \
      --out fig3.png --box 252,148,1150,710 --ref-dpi 150
  uv run --with pillow $S/extract_assets.py crop paper.pdf --page 13 \
      --out table2.png --text        # 1-bit PNG for black-on-white tables
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("needs Pillow:  uv run --with pillow extract_assets.py ...")

RENDER_DPI = 400  # source resolution for all crops


def need_file(p):
    if not os.path.isfile(p):
        sys.exit(f"no such file: {p}")


def page_count(pdf):
    try:
        out = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
    except FileNotFoundError:
        return None
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    return int(m.group(1)) if m else None


def render(pdf, page, dpi):
    """Render one page. Returns a detached copy so the temp dir can be removed."""
    need_file(pdf)
    n = page_count(pdf)
    if n and not 1 <= page <= n:
        sys.exit(f"--page {page} out of range (PDF has {n} pages)")
    with tempfile.TemporaryDirectory() as d:
        stem = os.path.join(d, "pg")
        r = subprocess.run(
            ["pdftocairo", "-png", "-r", str(dpi), "-f", str(page), "-l", str(page), pdf, stem],
            capture_output=True, text=True,
        )
        hits = sorted(f for f in os.listdir(d) if f.endswith(".png"))
        if r.returncode != 0 or not hits:
            sys.exit(f"pdftocairo failed on page {page}: {r.stderr.strip()[:200]}")
        return Image.open(os.path.join(d, hits[0])).copy()


def autotrim(im, pad=18, thresh=25):
    """Shrink to the ink. Guards the #1 crop bug: clipping the last table column
    or row because the box was eyeballed slightly too small."""
    g = ImageOps.invert(im.convert("L")).point(lambda p: 255 if p > thresh else 0)
    bb = g.getbbox()
    if not bb:
        return im
    return im.crop((max(0, bb[0] - pad), max(0, bb[1] - pad),
                    min(im.width, bb[2] + pad), min(im.height, bb[3] + pad)))


def cmd_survey(a):
    need_file(a.pdf)
    r = subprocess.run(["pdftotext", "-layout", a.pdf, "-"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"pdftotext failed: {r.stderr.strip()[:200]}")
    # Split on form feed FIRST. str.splitlines() treats \x0c as a line break and
    # consumes it, so counting "\f" per line always yields zero and every caption
    # gets reported as page 1.
    found = False
    for page, text in enumerate(r.stdout.split("\f"), 1):
        for line in text.splitlines():
            s = line.strip()
            if s.startswith(("Figure ", "Table ", "FIGURE ", "TABLE ")):
                found = True
                print(f"  pdf page {page}: {s[:96]}")
    if not found:
        print("  No captions found. Either this PDF has no text layer (scanned),")
        print("  or its captions do not start with 'Figure'/'Table'.")
        return
    print("\nPage numbers above are absolute PDF pages (a cover sheet shifts them")
    print("relative to the article's own numbering). Confirm with --whole before cropping.")


def cmd_crop(a):
    if a.text and os.path.splitext(a.out)[1].lower() != ".png":
        sys.exit("--text writes a 1-bit image; --out must end in .png "
                 "(JPEG/WebP silently demote it to 8-bit grey)")
    if a.ref_dpi <= 0:
        sys.exit("--ref-dpi must be > 0")

    im = render(a.pdf, a.page, RENDER_DPI)
    full_w = im.width

    if a.box:
        try:
            x0, y0, x1, y1 = (float(v) for v in a.box.split(","))
        except ValueError:
            sys.exit("--box must be x0,y0,x1,y1")
        s = RENDER_DPI / a.ref_dpi
        box = (max(0, int(x0 * s)), max(0, int(y0 * s)),
               min(im.width, int(x1 * s)), min(im.height, int(y1 * s)))
        if box[2] <= box[0] or box[3] <= box[1]:
            sys.exit(f"--box does not intersect the page "
                     f"({im.width}x{im.height}px at {RENDER_DPI}dpi; your box maps to {box})")
        im = im.crop(box)

    if not a.whole:
        im = autotrim(im)
    im = im.convert("RGB")

    if a.max_width and im.width > a.max_width:
        im = im.resize((a.max_width, round(a.max_width * im.height / im.width)), Image.LANCZOS)

    if a.text:
        im.convert("L").point(lambda p: 255 if p > a.thresh else 0, mode="1").save(a.out, optimize=True)
    else:
        im.save(a.out, optimize=True)

    w, h = Image.open(a.out).size
    print(f"{a.out}  {w}x{h}px  {os.path.getsize(a.out)/1024:.0f}KB")
    print(f"  -> CSS:  #id {{ aspect-ratio: {w}/{h} }}   (height = column width x {h/w:.4f})")
    if a.whole:
        # The emitted page is capped by --max-width, so its pixels are NOT --ref-dpi
        # pixels. Boxes measured on THIS image only land correctly at this dpi.
        print(f"  -> measure your --box on this image, then pass "
              f"--ref-dpi {RENDER_DPI * w / full_w:.6g}")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("survey", help="list figure/table captions and their PDF pages")
    s.add_argument("pdf")
    s.set_defaults(func=cmd_survey)

    c = sub.add_parser("crop", help="render a page and cut out one figure/table")
    c.add_argument("pdf")
    c.add_argument("--page", type=int, required=True, help="PDF page number (1-based, absolute)")
    c.add_argument("--out", required=True)
    c.add_argument("--box", help="x0,y0,x1,y1 in PIXELS of a --ref-dpi render")
    c.add_argument("--ref-dpi", type=float, default=150, help="dpi the --box was measured at")
    c.add_argument("--whole", action="store_true", help="skip autotrim; use to eyeball a full page")
    c.add_argument("--text", action="store_true", help="1-bit PNG: for tables/pseudocode")
    c.add_argument("--thresh", type=int, default=176, help="bilevel cutoff")
    c.add_argument("--max-width", type=int, default=2200)
    c.set_defaults(func=cmd_crop)

    a = p.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
