#!/usr/bin/env python3
"""Measure whether a poster actually fits its sheet. No eyeballing.

Reports, in cm:
  - the sheet's real rendered size vs the size you claimed
  - page overflow (content wider/taller than the sheet)
  - every element whose content exceeds its box   <- the clipping bug
  - every element sitting past its own content box, into the padding
  - text ink outside its box or cut off by a clip-path (moves no scroll metric)
  - dead space at the bottom of each card         <- the "too much whitespace" bug
  - images that failed to load, and webfonts that did not load
  - images letterboxing inside a wrong-aspect container
  - with --conformance: font sizes and spacing lengths the stylesheet never
    declares, i.e. values typed at a use site instead of taken from the template

Exit code 1 if anything is clipped, mis-sized, a resource failed, or (under
--conformance) a value was typed instead of declared, so it can gate a build.
A selector that matches nothing is an ERROR, never a silent pass.

Usage:
  S=<this-skill>/scripts   # wherever this skill is installed
  uv run $S/audit_fit.py poster.html --sheet 84.1x118.9 --root '#poster'
  uv run $S/audit_fit.py poster.html --sheet 84.1x118.9 --root '#poster' --conformance
  uv run $S/audit_fit.py poster.html --sheet 84.1x118.9 --root '#poster' --scan-scale
"""
import argparse, html as _html, http.server, json, math, os, re, socket, socketserver, subprocess, sys, threading

CHROME_CANDIDATES = [
    os.environ.get("CHROME_BIN", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    "/snap/bin/chromium",
]

PROBE = r"""
const ROOT=%(root)s, CARD=%(card)s, SHEET_H=%(sheet_h)f, SHEET_W=%(sheet_w)f, TOL=%(tol)f;
const CONF=%(conf)s;
const root=document.querySelector(ROOT);
if(!root){document.title='AUDITNOROOT';throw new Error('no root');}
const r=root.getBoundingClientRect();
const CM_PX=96/2.54;                       // CSS px per cm, fixed by spec
const cmH=r.height/SHEET_H, cmW=r.width/SHEET_W;
const R=v=>Math.round(v*10)/10;
const PROBE_ID='_auditProbe';
const what=el=>(el.className&&el.className.baseVal===undefined?String(el.className):el.tagName).slice(0,40);
const txt=el=>(el.textContent||'').trim().replace(/\s+/g,' ').slice(0,44);
// One offscreen element, attached INSIDE the root, so calc(29pt * var(--s)) and
// var(--gap-cap) resolve in the same variable context the poster renders in.
function pel(){
  let p=document.getElementById(PROBE_ID);
  if(!p){p=document.createElement('span'); p.id=PROBE_ID;
         p.style.cssText='position:absolute;left:-9999px;top:0;visibility:hidden';
         root.appendChild(p);}
  return p;
}
function resolve(prop,v){                  // any declared value -> used px, or null
  if(v==null) return null; v=String(v).trim(); if(!v) return null;
  const p=pel(); p.style.removeProperty(prop); p.style.setProperty(prop,v);
  if(!p.style.getPropertyValue(prop)) return null;          // not valid for this property
  const px=parseFloat(getComputedStyle(p)[prop==='margin-top'?'marginTop':'fontSize']);
  p.style.removeProperty(prop);
  return isNaN(px)?null:px;
}
const toPx=v=>resolve('margin-top',v);     // margin-top takes negatives; width/height do not
const toFs=v=>resolve('font-size',v);
// Absolute units only. An em or percentage literal is contextual, so it is judged as a
// relative factor (below), never as a length.
const LEN_LIT=/(-?\d*\.?\d+)(cm|mm|q|in|pt|pc|px)\b/gi;
const has=(set,v)=>set.some(a=>Math.abs(a-v)<0.05);

function ink(el){                          // union of the element's OWN text fragments
  let b=null; const rg=document.createRange();
  for(const n of el.childNodes){
    if(n.nodeType!==3||!n.nodeValue.trim()) continue;
    rg.selectNodeContents(n); const q=rg.getBoundingClientRect();
    if(!q.width||!q.height) continue;
    b=b?{l:Math.min(b.l,q.left),t:Math.min(b.t,q.top),r:Math.max(b.r,q.right),b:Math.max(b.b,q.bottom)}
       :{l:q.left,t:q.top,r:q.right,b:q.bottom};
  }
  return b;
}
function coord(tok,base){                  // '100%%' | '12.5px' | 'calc(100%% - 3.4cm)'
  tok=String(tok).replace(/calc\s*\(/gi,'(').replace(/[()]/g,' ');
  let sum=0,sign=1;
  for(const t of tok.trim().split(/\s+/)){
    if(t==='+'){sign=1;continue} if(t==='-'){sign=-1;continue}
    const m=/^(-?\d*\.?\d+)(.*)$/.exec(t); if(!m) continue;
    sum+=sign*(m[2]==='%%'?parseFloat(m[1])/100*base:(toPx(t)||0)); sign=1;
  }
  return sum;
}
function poly(cp,w,h){                     // computed clip-path -> border-box px points
  const m=/^polygon\(([^]*)\)$/i.exec(String(cp).trim()); if(!m) return null;
  const pts=[];
  for(const part of m[1].split(',')){
    const s=part.trim(); if(!s||/^(nonzero|evenodd)$/i.test(s)) continue;
    const xy=s.split(/\s+(?![^(]*\))/);    // a space inside calc(...) is not a separator
    if(xy.length<2) return null;
    pts.push([coord(xy[0],w),coord(xy[1],h)]);
  }
  return pts.length>2?pts:null;
}
function inPoly(x,y,P){
  let c=false;
  for(let i=0,j=P.length-1;i<P.length;j=i++){
    const xi=P[i][0],yi=P[i][1],xj=P[j][0],yj=P[j][1];
    if((yi>y)!==(yj>y) && x<(xj-xi)*(y-yi)/(yj-yi)+xi) c=!c;
  }
  return c;
}
function distPoly(x,y,P){                  // how far outside: nearest edge
  let d=Infinity;
  for(let i=0,j=P.length-1;i<P.length;j=i++){
    const xi=P[i][0],yi=P[i][1],dx=P[j][0]-xi,dy=P[j][1]-yi,L=dx*dx+dy*dy;
    let t=L?((x-xi)*dx+(y-yi)*dy)/L:0; t=Math.max(0,Math.min(1,t));
    d=Math.min(d,Math.hypot(x-(xi+t*dx),y-(yi+t*dy)));
  }
  return d;
}
function snap(){
  const rr=root.getBoundingClientRect();
  const out={page:{},clipped:[],past:[],ink:[],dead:[],images:[],letterbox:[],fonts:[],dpi:[],
             cardCount:0,bodyPt:null,worst:0,fails:false};
  // fails/worst are the sweep's fit predicate: set at exactly the sites that make
  // the audit exit 1 on geometry, on the raw value, so a scale the sweep calls
  // fitting cannot be a scale the audit then reports as clipped.
  const fail=cm=>{ out.fails=true; out.worst=Math.max(out.worst,cm); };
  // Measure the sheet itself -- otherwise --sheet is only a unit conversion and
  // a wrong physical size can never be detected.
  out.page.sheetW=R(rr.width/CM_PX); out.page.sheetH=R(rr.height/CM_PX);
  out.page.overflowW=R((root.scrollWidth-root.clientWidth)/cmW);
  out.page.overflowH=R((root.scrollHeight-root.clientHeight)/cmH);
  out.worst=Math.max(0,out.page.overflowW,out.page.overflowH);
  if(out.worst>TOL) out.fails=true;
  root.querySelectorAll('*').forEach(el=>{
    if(!el.clientHeight) return;
    const o=el.scrollHeight-el.clientHeight;
    if(o>TOL*cmH){ out.clipped.push({by:R(o/cmH),what:what(el),text:txt(el)}); fail(o/cmH); }
  });
  // clip-path removes glyphs without moving any scroll metric, and a line box can
  // sit outside its own box without either. Both are measured on the ink itself.
  root.querySelectorAll('*').forEach(el=>{
    if(el.id===PROBE_ID) return;
    const cs=getComputedStyle(el);
    if(cs.display==='inline') return;      // no box of its own: its rect IS its line boxes
    const k=ink(el); if(!k) return;
    const b=el.getBoundingClientRect();
    const f=v=>parseFloat(v)||0;
    // padding box, not content box: a hanging indent (text-indent:-0.75em against
    // padding-left) is legitimate and lands exactly on the padding edge. Clipping,
    // by overflow or by clip-path, bites at the padding box.
    const pb={l:b.left+f(cs.borderLeftWidth),t:b.top+f(cs.borderTopWidth),
              r:b.right-f(cs.borderRightWidth),b:b.bottom-f(cs.borderBottomWidth)};
    const o=Math.max(pb.l-k.l,k.r-pb.r,pb.t-k.t,k.b-pb.b);
    if(o>TOL*cmH){ out.ink.push({by:R(o/cmH),how:'outside its box',what:what(el),text:txt(el)});
                   fail(o/cmH); }
    if(cs.clipPath&&cs.clipPath!=='none'){
      const P=poly(cs.clipPath,b.width,b.height);
      if(P){
        let worst=0;
        [[k.l,k.t],[k.r,k.t],[k.r,k.b],[k.l,k.b]].forEach(c=>{
          const x=c[0]-b.left,y=c[1]-b.top;
          if(!inPoly(x,y,P)) worst=Math.max(worst,distPoly(x,y,P));
        });
        // --tol absorbs layout slop, and a clip-path has none to absorb: ink outside
        // the polygon is ink that does not print. Judge it at 0.5mm.
        const ctol=Math.min(TOL,0.05);
        if(worst>ctol*cmH){ out.ink.push({by:R(worst/cmH),how:'cut off by clip-path',
                                          what:what(el),text:txt(el)}); fail(worst/cmH); }
      }
    }
  });
  const cards=root.querySelectorAll(CARD);
  out.cardCount=cards.length;
  if(cards.length) out.bodyPt=R(parseFloat(getComputedStyle(cards[0]).fontSize)*0.75);
  cards.forEach(c=>{
    const k=[...c.children]; if(!k.length) return;
    const cs=getComputedStyle(c);
    const inner=c.getBoundingClientRect().bottom-parseFloat(cs.paddingBottom||0)-parseFloat(cs.borderBottomWidth||0);
    // lowest child by geometry, not last in DOM: row/wrap/order layouts differ
    const lowest=Math.max(...k.map(x=>x.getBoundingClientRect().bottom));
    const gap=(inner-lowest)/cmH;
    if(gap>1.0) out.dead.push({cm:R(gap),text:txt(c)});
    // the negative case is the blind spot: a child sitting up to a padding-height
    // past the content box moves no scroll metric, so nothing above sees it.
    else if(-gap>TOL){ out.past.push({cm:R(-gap),what:what(c),text:txt(c)}); fail(-gap); }
  });
  root.querySelectorAll('img').forEach(im=>{
    const src=(im.getAttribute('src')||'').split('/').pop();
    if(!im.naturalWidth){out.images.push({src,status:'FAILED TO LOAD'});return;}
    const b=im.getBoundingClientRect();
    if(b.width<2||b.height<2) return;
    // effective print resolution = source pixels / printed inches
    // unrounded: the remedy is computed from these, and rounding either one up
    // yields a "fix" that still fails the gate
    const inch=(b.width/CM_PX)/2.54;
    out.dpi.push({src,dpi:im.naturalWidth/inch,cm:b.width/CM_PX,nw:im.naturalWidth});
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

// The template owns every size and spacing value. Nothing geometric detects a
// violation, so this compares what the document DECLARES against what every
// element actually got. Absolute defects are elsewhere; this one is conformance.
function conformance(){
  const FS=[],FACT=[],LEN=[];
  function eachRule(list,fn){
    for(const rule of list){
      if(rule.styleSheet){ try{eachRule(rule.styleSheet.cssRules,fn)}catch(e){} }
      if(rule.cssRules) eachRule(rule.cssRules,fn);
      if(rule.style) fn(rule.style);
    }
  }
  for(const sh of document.styleSheets){
    let list=null;
    try{list=sh.cssRules}catch(e){continue}           // cross-origin webfont sheet
    if(!list) continue;
    eachRule(list,st=>{
      for(let i=0;i<st.length;i++){
        const prop=st[i], val=st.getPropertyValue(prop);
        if(prop.slice(0,2)==='--'){                   // a declared knob: --gap-cap etc
          const px=toPx(getComputedStyle(pel()).getPropertyValue(prop))??toPx(val);
          if(px!=null) LEN.push(px);
          continue;
        }
        if(prop==='font-size'){
          const rel=/^\s*(-?\d*\.?\d+)\s*(%%|em)\s*$/.exec(val);
          if(rel){ FACT.push(parseFloat(rel[1])/(rel[2]==='%%'?100:1)); continue; }
          const px=toFs(val); if(px!=null) FS.push(px);
          continue;
        }
        let m; LEN_LIT.lastIndex=0;
        while((m=LEN_LIT.exec(val))){ const px=toPx(m[0]); if(px!=null) LEN.push(px); }
      }
    });
  }
  const bad={fs:[],sp:[],declaredFs:FS.length,declaredLen:LEN.length};
  // font: an element owning text must have a declared size, its parent's size
  // (plain inheritance), or parent x a declared relative factor (sup/sub).
  root.querySelectorAll('*').forEach(el=>{
    if(el.id===PROBE_ID) return;
    if(![...el.childNodes].some(n=>n.nodeType===3&&n.nodeValue.trim())) return;
    const fs=parseFloat(getComputedStyle(el).fontSize);
    if(!fs||has(FS,fs)) return;
    const p=el.parentElement;
    if(p){
      const pfs=parseFloat(getComputedStyle(p).fontSize);
      if(Math.abs(pfs-fs)<0.05) return;               // inherited, blame the parent
      if(FACT.some(f=>Math.abs(pfs*f-fs)<0.05)) return;
    }
    bad.fs.push({pt:R(fs*0.75),what:what(el),text:txt(el)});
  });
  // A font-size typed into a style attribute is drift even on a container with
  // no text of its own: every descendant inherits it, and the inheritance test
  // above then excuses each of them by blaming a parent nothing ever checks.
  root.querySelectorAll('[style]').forEach(el=>{
    if(el.id===PROBE_ID) return;
    if(!/(^|;)\s*font-size\s*:/i.test(el.getAttribute('style')||'')) return;
    const fs=parseFloat(getComputedStyle(el).fontSize);
    if(!fs||has(FS,fs)) return;
    const p=el.parentElement;
    if(p){
      const pfs=parseFloat(getComputedStyle(p).fontSize);
      if(FACT.some(f=>Math.abs(pfs*f-fs)<0.05)) return;
    }
    if(bad.fs.some(b=>b.what===what(el)&&Math.abs(b.pt-R(fs*0.75))<0.01)) return;
    bad.fs.push({pt:R(fs*0.75),what:what(el),text:txt(el)||'(inline font-size on a container)'});
  });
  // spacing: a length typed at a use site. A var() reference is fine only if it
  // resolves to a declared value.
  root.querySelectorAll('[style]').forEach(el=>{
    if(el.id===PROBE_ID) return;
    for(const decl of (el.getAttribute('style')||'').split(';')){
      const c=decl.indexOf(':'); if(c<0) continue;
      const prop=decl.slice(0,c).trim().toLowerCase(), val=decl.slice(c+1);
      if(!prop||prop.slice(0,2)==='--'||prop==='font-size') continue;   // font is above
      let rest=val, m, seen;
      while((m=/var\(\s*(--[\w-]+)[^()]*\)/.exec(rest))){               // check, then strip
        const px=toPx(getComputedStyle(el).getPropertyValue(m[1]));
        if(px!=null&&!has(LEN,px)) bad.sp.push({lit:'var('+m[1]+')',prop,what:what(el),text:txt(el)});
        rest=rest.slice(0,m.index)+rest.slice(m.index+m[0].length);
      }
      LEN_LIT.lastIndex=0; seen=[];
      while((m=LEN_LIT.exec(rest))){
        if(parseFloat(m[1])===0||seen.indexOf(m[0])>=0) continue;       // 0 has no unit to drift
        seen.push(m[0]);
        // A literal typed at a use site is drift even when today it happens to
        // equal the template's value - that equality is what stops holding.
        const px=toPx(m[0]);
        bad.sp.push({lit:m[0],prop,what:what(el),text:txt(el),dup:px!=null&&has(LEN,px)});
      }
    }
  });
  const p=document.getElementById(PROBE_ID); if(p) p.remove();
  return bad;
}
%(extra)s
document.title='AUDIT'+JSON.stringify(RESULT);
"""

SCAN = """
const RESULT={scan:[]};
let best=null;
const LO=%(lo)f, HI=%(hi)f;
const was=root.style.getPropertyValue('--s');
for(let s=LO;s<=HI+1e-9;s+=0.01){
  root.style.setProperty('--s',s.toFixed(2)); void root.offsetHeight;
  const m=snap();
  // "fits" is not a second threshold here: it is snap()'s own verdict, raised at
  // the same sites and on the same raw values that make the audit exit 1. A
  // separate (or rounded) comparison lets the sweep bless a scale the audit
  // then reports as clipped, in the same output.
  const dead=Math.max(0,...m.dead.map(d=>d.cm));
  RESULT.scan.push({s:s.toFixed(2),over:R(m.worst),dead:R(dead),bodyPt:m.bodyPt});
  if(!m.fails) best=(best===null?s:Math.max(best,s));    // largest, not last
}
RESULT.best=(best===null?null:best.toFixed(2));
RESULT.hitCeiling=(best!==null && best>=HI-1e-9);
RESULT.hitFloor=(best!==null && best<=LO+1e-9);
RESULT.lo=LO; RESULT.hi=HI;
// Nothing fits: leave --s alone and take NO measurement. A block measured at some
// other scale, printed under the sweep, reads exactly like a real audit.
if(best===null){ root.style.setProperty('--s',was); }
else { root.style.setProperty('--s',RESULT.best);
       RESULT.atBest=snap(); if(CONF) RESULT.atBest.conf=conformance(); }
"""

ONCE = "const RESULT=snap(); if(CONF) RESULT.conf=conformance();"

SCAN_LO, SCAN_HI = 0.80, 1.30


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
    p.add_argument("--conformance", action="store_true",
                   help="also fail on any font size or spacing length the stylesheet "
                        "never declares (template drift); off by default because a "
                        "poster written with inline values fails it on every line")
    p.add_argument("--pt-floor", type=float, default=24,
                   help="body pt the sweep flags as too small to print")
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
                  "conf": "true" if a.conformance else "false",
                  "extra": SCAN % {"lo": SCAN_LO, "hi": SCAN_HI} if a.scan_scale else ONCE}

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
        def pt(row):
            b = row.get("bodyPt")
            if b is None:
                return "   body ?pt (--card matched nothing)"
            return f"   body {b}pt" + ("  BELOW THE {:g}pt FLOOR".format(a.pt_floor)
                                       if b < a.pt_floor else "")
        for row in res["scan"]:
            print(f"  --s {row['s']}   clipped {row['over']:>5}cm   dead {row['dead']:>5}cm{pt(row)}")
        if res["best"] is None:
            # No block below this line: printing one measured at some other scale
            # is indistinguishable from a real audit, which is how it gets believed.
            print(f"\nNOTHING FITS anywhere in --s {res['lo']:.2f}..{res['hi']:.2f}. "
                  f"No audit was taken and --s was left as it was;\nthe rows above are the "
                  f"whole result. Cut content - the type scale cannot save this.")
            sys.exit(1)
        note = "  (sweep ceiling - content may allow larger type)" if res.get("hitCeiling") else ""
        if res.get("hitFloor"):
            note = f"  (sweep floor {res['lo']:.2f} - nothing smaller was tried)"
        print(f"\nlargest type scale that fits: --s {res['best']}{note}")
        res = res["atBest"]
        if res.get("bodyPt") is not None and res["bodyPt"] < a.pt_floor:
            print(f"  but body text lands at {res['bodyPt']}pt, below the {a.pt_floor:g}pt "
                  f"floor - cut content instead of baking this in")

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
    for c in res.get("past", []):
        bad = True
        print(f"  PAST ITS CONTENT BOX +{c['cm']}cm into the padding of [{c['what']}] {c['text']}")
    for c in res.get("ink", []):
        bad = True
        print(f"  INK {c['how']} +{c['by']}cm  [{c['what']}] {c['text']}")
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
            # floor, never round: the widest placement that still clears the floor.
            # Rounding either the dpi or the remedy up prints a width that fails again.
            fix = math.floor(d["nw"] / a.min_dpi * 2.54 * 10) / 10
            print(f"  LOW RESOLUTION {math.floor(d['dpi'])}dpi  {d['src']}  "
                  f"(printed {d['cm']:.1f}cm wide; "
                  f"needs {a.min_dpi:g}dpi -> shrink to {fix}cm or get a bigger source)")
    for l in res["letterbox"]:
        print(f"  LETTERBOX {l['waste']}cm around {l['src']} -> set container height to {l['fix']}cm")
    for ds in res["dead"]:
        print(f"  DEAD SPACE {ds['cm']}cm at bottom of: {ds['text']}")
    conf = res.get("conf")
    if conf is not None:
        if not conf["declaredFs"]:
            bad = True
            print("  NO DECLARED FONT SIZES FOUND - the stylesheet is unreadable from the "
                  "probe (cross-origin?), so conformance was not checked")
        for c in conf["fs"]:
            bad = True
            print(f"  UNDECLARED FONT SIZE {c['pt']}pt  [{c['what']}] {c['text']}")
        for c in conf["sp"]:
            bad = True
            why = (" (duplicates a declared value - reference it instead of retyping)"
                   if c.get("dup") else "")
            print(f"  UNDECLARED SPACING {c['prop']}:{c['lit']}{why}  [{c['what']}] {c['text']}")
    if not bad and not res["dead"] and not res["letterbox"]:
        print("  clean: nothing clipped, no broken resources, no dead space")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
