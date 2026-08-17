#!/usr/bin/env python3
"""Measure whether a poster actually fits its sheet. No eyeballing.

Reports, in cm:
  - the sheet's real rendered size vs the size you claimed
  - page overflow (content wider/taller than the sheet)
  - every element whose content exceeds its box   <- the clipping bug
  - dead space at the bottom of each card         <- the "too much whitespace" bug
  - images that failed to load, and webfonts that did not load
  - images letterboxing inside a wrong-aspect container

Exit code 1 if anything is clipped, mis-sized, or a resource failed, so it can
gate a build. A selector that matches nothing is an ERROR, never a silent pass.

Usage:
  S=<this-skill>/scripts   # wherever this skill is installed
  uv run $S/audit_fit.py poster.html --sheet 84.1x118.9 --root '#poster'
  uv run $S/audit_fit.py poster.html --sheet 84.1x118.9 --root '#poster' --scan-scale
"""
import argparse, html as _html, http.server, json, os, re, socket, socketserver, subprocess, sys, threading

CHROME_CANDIDATES = [
    os.environ.get("CHROME_BIN", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    "/snap/bin/chromium",
]

PROBE = r"""
const ROOT=%(root)s, CARD=%(card)s, SHEET_H=%(sheet_h)f, SHEET_W=%(sheet_w)f, TOL=%(tol)f;
const root=document.querySelector(ROOT);
if(!root){document.title='AUDITNOROOT';throw new Error('no root');}
const r=root.getBoundingClientRect();
const CM_PX=96/2.54;                       // CSS px per cm, fixed by spec
const cmH=r.height/SHEET_H, cmW=r.width/SHEET_W;
const R=v=>Math.round(v*10)/10;
function snap(){
  const rr=root.getBoundingClientRect();
  const out={page:{},clipped:[],dead:[],images:[],letterbox:[],fonts:[],dpi:[],cardCount:0};
  // Measure the sheet itself -- otherwise --sheet is only a unit conversion and
  // a wrong physical size can never be detected.
  out.page.sheetW=R(rr.width/CM_PX); out.page.sheetH=R(rr.height/CM_PX);
  out.page.overflowW=R((root.scrollWidth-root.clientWidth)/cmW);
  out.page.overflowH=R((root.scrollHeight-root.clientHeight)/cmH);
  root.querySelectorAll('*').forEach(el=>{
    if(!el.clientHeight) return;
    const o=el.scrollHeight-el.clientHeight;
    if(o>TOL*cmH) out.clipped.push({by:R(o/cmH),
      what:(el.className&&el.className.baseVal===undefined?String(el.className):el.tagName).slice(0,40),
      text:(el.textContent||'').trim().replace(/\s+/g,' ').slice(0,44)});
  });
  const cards=root.querySelectorAll(CARD);
  out.cardCount=cards.length;
  cards.forEach(c=>{
    const k=[...c.children]; if(!k.length) return;
    const cs=getComputedStyle(c);
    const inner=c.getBoundingClientRect().bottom-parseFloat(cs.paddingBottom||0)-parseFloat(cs.borderBottomWidth||0);
    // lowest child by geometry, not last in DOM: row/wrap/order layouts differ
    const lowest=Math.max(...k.map(x=>x.getBoundingClientRect().bottom));
    const gap=(inner-lowest)/cmH;
    if(gap>1.0) out.dead.push({cm:R(gap),text:(c.textContent||'').trim().replace(/\s+/g,' ').slice(0,44)});
  });
  root.querySelectorAll('img').forEach(im=>{
    const src=(im.getAttribute('src')||'').split('/').pop();
    if(!im.naturalWidth){out.images.push({src,status:'FAILED TO LOAD'});return;}
    const b=im.getBoundingClientRect();
    if(b.width<2||b.height<2) return;
    // effective print resolution = source pixels / printed inches
    const inch=(b.width/CM_PX)/2.54;
    out.dpi.push({src,dpi:Math.round(im.naturalWidth/inch),cm:R(b.width/CM_PX)});
    const boxA=b.width/b.height, imgA=im.naturalWidth/im.naturalHeight;
    if(getComputedStyle(im).objectFit==='contain'&&Math.abs(boxA-imgA)/imgA>0.03){
      const shown=boxA>imgA?{w:b.height*imgA,h:b.height}:{w:b.width,h:b.width/imgA};
      out.letterbox.push({src,waste:R(Math.max(b.width-shown.w,b.height-shown.h)/cmH),
        fix:R((b.width/cmW)*(im.naturalHeight/im.naturalWidth))});
    }
  });
  // A substituted fallback font has different metrics and silently eats the fit
  // margin. document.fonts.check() is useless here: when the webfont CSS itself
  // fails to load there is no @font-face to test, so it returns true. Compare
  // rendered metrics against two generics instead - a real font differs from both.
  out.fonts=[...new Set([...root.querySelectorAll('*')]
    .map(e=>getComputedStyle(e).fontFamily.split(',')[0].replace(/['"]/g,'').trim()))]
    .filter(f=>f && !/^(sans-serif|serif|monospace|system-ui|-apple-system|ui-\w+)$/i.test(f))
    .filter(f=>{
      // Ask the registry, not a canvas: with unicode-range subsetting a canvas
      // probe never triggers the subset download and reports a false miss,
      // while document.fonts.check() reports a false hit when the CSS itself
      // 404s (no @font-face exists to test). Loaded faces are ground truth.
      const faces=[...document.fonts].filter(x=>x.family.replace(/['"]/g,'').trim()===f);
      if(faces.length) return !faces.some(x=>x.status==='loaded');
      // no @font-face at all -> confirm by metrics before accusing
      const probe='mmmmmmmmmmlliWWWWWW';
      const cx=document.createElement('canvas').getContext('2d');
      return ['monospace','sans-serif'].every(gen=>{
        cx.font=`72px ${gen}`;         const base=cx.measureText(probe).width;
        cx.font=`72px "${f}", ${gen}`; return cx.measureText(probe).width===base;
      });
    });
  return out;
}
%(extra)s
document.title='AUDIT'+JSON.stringify(RESULT);
"""

SCAN = """
const RESULT={scan:[]};
let best=null;
const LO=0.80, HI=1.30;
for(let s=LO;s<=HI+1e-9;s+=0.01){
  root.style.setProperty('--s',s.toFixed(2)); void root.offsetHeight;
  const m=snap();
  const over=Math.max(m.page.overflowH,0,...m.clipped.map(c=>c.by));
  const dead=Math.max(0,...m.dead.map(d=>d.cm));
  RESULT.scan.push({s:s.toFixed(2),over:R(over),dead:R(dead)});
  if(over<=0.15) best=(best===null?s:Math.max(best,s));   // largest, not last
}
RESULT.best=(best===null?null:best.toFixed(2));
RESULT.hitCeiling=(best!==null && best>=HI-1e-9);
RESULT.hitFloor=(best===null);
root.style.setProperty('--s',RESULT.best||'1');
RESULT.atBest=snap();
"""

ONCE = "const RESULT=snap();"


def find_chrome():
    from shutil import which
    for c in CHROME_CANDIDATES:
        if not c:
            continue
        if os.path.exists(c):
            return c
        w = which(c)
        if w:
            return w
    sys.exit("Chrome/Chromium not found (set CHROME_BIN to override)")


def serve(directory):
    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=directory, **k)
        def log_message(self, *a):
            pass
    srv = socketserver.TCPServer(("127.0.0.1", 0), H)   # loopback + ephemeral port
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("html")
    p.add_argument("--sheet", required=True, help="WxH in cm, e.g. 84.1x118.9")
    p.add_argument("--root", default="body > *", help="CSS selector for the sheet element")
    p.add_argument("--card", default=".card", help="CSS selector for boxes to check for dead space")
    p.add_argument("--tol", type=float, default=0.3, help="cm of overflow to ignore")
    p.add_argument("--min-dpi", type=float, default=150,
                   help="effective print resolution floor for embedded images")
    p.add_argument("--scan-scale", action="store_true",
                   help="sweep the --s type-scale var; report the largest that fits")
    a = p.parse_args()

    if not os.path.isfile(a.html):
        sys.exit(f"no such file: {a.html}")
    try:
        sw, sh = (float(x) for x in a.sheet.lower().split("x"))
    except ValueError:
        sys.exit("--sheet must look like 84.1x118.9")

    d = os.path.dirname(os.path.abspath(a.html)) or "."
    js = PROBE % {"root": json.dumps(a.root), "card": json.dumps(a.card),
                  "sheet_h": sh, "sheet_w": sw, "tol": a.tol,
                  "extra": SCAN if a.scan_scale else ONCE}

    # Inject into the real document. Transplanting via innerHTML would keep the
    # CSS but silently DROP every <script>, so a JS-built layout measures as
    # "clean" while overflowing in the browser.
    src = open(a.html, encoding="utf-8").read()
    inject = ("<script>window.addEventListener('load',()=>document.fonts.ready"
              ".then(()=>setTimeout(()=>{" + js + "},300)));</script>")
    probe_html = (src.replace("</body>", inject + "</body>", 1)
                  if "</body>" in src else src + inject)

    wrapper = os.path.join(d, f"._audit.{os.getpid()}.html")
    try:
        open(wrapper, "w", encoding="utf-8").write(probe_html)
    except PermissionError:
        sys.exit(f"cannot write {wrapper} - the poster's directory must be writable "
                 f"(the probe has to sit beside the HTML so relative <img src> resolves)")

    srv, port = serve(d)
    try:
        dom = subprocess.run([find_chrome(), "--headless", "--disable-gpu", "--no-sandbox",
                              "--virtual-time-budget=20000", "--dump-dom",
                              f"http://127.0.0.1:{port}/{os.path.basename(wrapper)}"],
                             capture_output=True, text=True, timeout=180).stdout
    finally:
        srv.shutdown()
        if os.path.exists(wrapper):
            os.remove(wrapper)

    if "<title>AUDITNOROOT</title>" in dom:
        sys.exit(f"--root {a.root!r} matched no element in {a.html}")
    m = re.search(r"<title>AUDIT(.*?)</title>", dom, re.S)
    if not m:
        sys.exit("probe did not run - Chrome may have failed to load the page")
    res = json.loads(_html.unescape(m.group(1)))   # decodes &lt; &gt; &amp; &quot; &nbsp;

    if a.scan_scale:
        for row in res["scan"]:
            print(f"  --s {row['s']}   clipped {row['over']:>5}cm   dead {row['dead']:>5}cm")
        if res["best"] is None:
            print("\nNothing fits even at --s 0.80: cut content, the type scale cannot save this.")
        else:
            note = "  (sweep ceiling - content may allow larger type)" if res.get("hitCeiling") else ""
            print(f"\nlargest type scale that fits: --s {res['best']}{note}")
        res = res["atBest"]

    bad = False
    pg = res["page"]
    print(f"\nsheet renders {pg['sheetW']} x {pg['sheetH']} cm (declared {sw} x {sh})")
    if abs(pg["sheetW"] - sw) > 0.3 or abs(pg["sheetH"] - sh) > 0.3:
        bad = True
        print("  SHEET SIZE MISMATCH - the CSS does not produce the sheet you asked for")
    print(f"page overflow: {pg['overflowW']}cm wide, {pg['overflowH']}cm tall")
    if max(pg["overflowW"], pg["overflowH"]) > a.tol:
        bad = True
    for c in res["clipped"]:
        bad = True
        print(f"  CLIPPED +{c['by']}cm  [{c['what']}] {c['text']}")
    for i in res["images"]:
        bad = True
        print(f"  IMAGE {i['status']}: {i['src']}")
    for f in res["fonts"]:
        bad = True
        print(f"  WEBFONT NOT LOADED: {f} - measurements use fallback metrics")
    if res.get("cardCount", 0) == 0:
        bad = True
        print(f"  CARD SELECTOR MATCHED NOTHING: --card {a.card!r} - the dead-space check "
              f"did not run; pass the selector your poster's boxes actually use")
    for d in sorted(res.get("dpi", []), key=lambda x: x["dpi"]):
        if d["dpi"] < a.min_dpi:
            bad = True
            print(f"  LOW RESOLUTION {d['dpi']}dpi  {d['src']}  (printed {d['cm']}cm wide; "
                  f"needs {a.min_dpi}dpi -> shrink to {d['cm']*d['dpi']/a.min_dpi:.1f}cm or get a bigger source)")
    for l in res["letterbox"]:
        print(f"  LETTERBOX {l['waste']}cm around {l['src']} -> set container height to {l['fix']}cm")
    for ds in res["dead"]:
        print(f"  DEAD SPACE {ds['cm']}cm at bottom of: {ds['text']}")
    if not bad and not res["dead"] and not res["letterbox"]:
        print("  clean: nothing clipped, no broken resources, no dead space")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
