#!/usr/bin/env bash
# Render a poster HTML to print-ready PDF + PNG + a correctly sized PPTX.
#
#   export_poster.sh poster.html W_CM H_CM [outname]
#
# PDF is the file you send to the printer: text stays vector, images stay
# embedded at full resolution. PPTX wraps the raster render on a slide of the
# right physical size, for people who insist on PowerPoint.
set -euo pipefail

HTML="${1:?usage: export_poster.sh poster.html W_CM H_CM [outname]}"
W="${2:?width in cm}"; H="${3:?height in cm}"
[ -f "$HTML" ] || { echo "no such file: $HTML"; exit 1; }
OUT="${4:-$(basename "${HTML%.*}")}"
DIR="$(cd "$(dirname "$HTML")" && pwd)"
BASE="$(basename "$HTML")"
DPI="${DPI:-150}"

CHROME=""
for c in "${CHROME_BIN:-}" \
         "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
         "/Applications/Chromium.app/Contents/MacOS/Chromium" \
         "$(command -v google-chrome || true)" \
         "$(command -v google-chrome-stable || true)" \
         "$(command -v chromium || true)" \
         "$(command -v chromium-browser || true)" \
         /snap/bin/chromium; do
  [ -n "$c" ] && [ -x "$c" ] && CHROME="$c" && break
done
[ -n "$CHROME" ] || { echo "Chrome/Chromium not found (set CHROME_BIN)"; exit 1; }

# Serve over http: file:// blocks the webfont and some subresources.
# Bind loopback on an EPHEMERAL port. A hardcoded port that is already taken
# makes python exit instantly and Chrome then silently renders whoever owns
# that port -- producing a correctly sized PDF of somebody else's poster.
cd "$DIR"
PORT="$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1]);s.close()')"
python3 -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null || true' EXIT INT TERM HUP   # EXIT alone leaks on Ctrl-C
for _ in $(seq 40); do
  curl -fsS -o /dev/null "http://127.0.0.1:$PORT/$BASE" && break
  kill -0 $SRV 2>/dev/null || { echo "local server died"; exit 1; }
  sleep 0.1
done

echo "-> PDF"
"$CHROME" --headless --disable-gpu --no-sandbox --no-pdf-header-footer \
  --print-to-pdf="$DIR/$OUT.pdf" --virtual-time-budget=20000 \
  "http://127.0.0.1:$PORT/$BASE" 2>/dev/null

# The @page size in the CSS drives the sheet size. Verify, don't assume.
python3 - "$DIR/$OUT.pdf" "$W" "$H" <<'PY'
import re,sys
try:
    d=open(sys.argv[1],'rb').read()
except OSError:
    sys.exit("Chrome wrote no PDF")
m=re.search(rb'/MediaBox\s*\[([^\]]+)\]',d)
if not m: sys.exit("no MediaBox in the PDF - Chrome may have failed to render")
b=[float(x) for x in m.group(1).split()]
w,h=(b[2]-b[0])/72*2.54,(b[3]-b[1])/72*2.54
tw,th=float(sys.argv[2]),float(sys.argv[3])
ok = abs(w-tw)<0.3 and abs(h-th)<0.3
print(f"   {w:.1f} x {h:.1f} cm  (target {tw} x {th})  {'OK' if ok else 'MISMATCH -- check @page in the CSS'}")
sys.exit(0 if ok else 1)
PY

echo "-> PNG (${DPI}dpi)"
pdftocairo -png -r "$DPI" -f 1 -l 1 "$DIR/$OUT.pdf" "$DIR/$OUT"
PNG="$(ls "$DIR/$OUT"-*.png | head -1)"

echo "-> PPTX"
uv run --quiet --with python-pptx python - "$PNG" "$DIR/$OUT.pptx" "$W" "$H" <<'PY'
import sys
from pptx import Presentation
from pptx.util import Cm
png,out,w,h = sys.argv[1],sys.argv[2],float(sys.argv[3]),float(sys.argv[4])
if max(w,h) > 142.24:
    sys.exit(f"PowerPoint caps a slide at 142.24 cm; {max(w,h)} cm will not fit "
             f"(the PDF and PNG above are still valid)")
p = Presentation(); p.slide_width, p.slide_height = Cm(w), Cm(h)
p.slides.add_slide(p.slide_layouts[6]).shapes.add_picture(png, 0, 0, Cm(w), Cm(h))
p.save(out)
print(f"   slide {w} x {h} cm")
PY

echo
for f in "$DIR/$OUT.pdf" "$DIR/$OUT.pptx" "$PNG"; do
  printf '   %s  %s\n' "$f" "$(du -h "$f" | cut -f1)"
done
