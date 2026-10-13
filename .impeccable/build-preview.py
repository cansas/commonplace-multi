#!/usr/bin/env python3
"""Generate .impeccable/design-preview.html from .impeccable/design.json.

Standalone, no server, no npm: themes.css and design.json are inlined so the
file works from file:// (fetch() on file:// is blocked by CORS).
Regenerate after any DESIGN.md / design.json change:

    cd ~/Documents/commonplace-multi && python3 .impeccable/build-preview.py
"""
import json
import os
import re
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESIGN_JSON = os.path.join(ROOT, ".impeccable", "design.json")
DESIGN_MD = os.path.join(ROOT, "DESIGN.md")
THEMES_CSS = os.path.join(ROOT, "app", "static", "themes.css")
OUT = os.path.join(ROOT, ".impeccable", "design-preview.html")

design = json.load(open(DESIGN_JSON))
themes_css = open(THEMES_CSS).read()


def load_frontmatter(path):
    """Typography lives in DESIGN.md's YAML frontmatter, not in the sidecar."""
    text = open(path).read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise SystemExit("DESIGN.md has no YAML frontmatter")
    try:
        import yaml
        return yaml.safe_load(m.group(1))
    except ImportError:
        raise SystemExit("pyyaml is required to read DESIGN.md frontmatter")


frontmatter = load_frontmatter(DESIGN_MD)

def safe(blob: str) -> str:
    """Keep an inlined </script> or </style> from closing its tag early."""
    return blob.replace("</", "<\\/")

VIEWER_CSS = """
*{box-sizing:border-box}
body{margin:0;background-color:var(--bg-page);color:var(--text-primary);font-family:var(--font-body);-webkit-font-smoothing:antialiased;transition:background-color .3s ease,color .3s ease}
.wrap{max-width:72rem;margin:0 auto;padding:2rem 1.5rem 6rem}
header.top{border-bottom:1px solid var(--border-subtle);padding-bottom:1.25rem}
h1{font-size:1.875rem;font-weight:700;margin:0 0 .35rem;letter-spacing:-.01em}
.sub{color:var(--text-muted);font-size:.875rem;margin:0}
h2{font-size:1.25rem;font-weight:600;margin:3.5rem 0 1rem;padding-top:1.75rem;border-top:1px solid var(--border-subtle)}
h3{font-size:.75rem;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--text-muted);margin:0 0 .75rem}
.meta{color:var(--text-muted-lighter);font-size:.75rem;margin-top:.6rem}
.tile{background-color:var(--bg-card);border:1px solid var(--border-card);border-radius:12px;padding:1.25rem}
.grid{display:grid;gap:.9rem}
.cols-sw{grid-template-columns:repeat(auto-fill,minmax(16rem,1fr))}
.cols-comp{grid-template-columns:repeat(auto-fill,minmax(20rem,1fr))}
.themebar{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:1.25rem}
.tbtn{padding:6px 14px;border-radius:8px;border:1px solid var(--border-card);background-color:var(--bg-card);color:var(--text-secondary);font-family:inherit;font-size:.8125rem;font-weight:500;cursor:pointer;transition:background-color .15s ease,color .15s ease,border-color .15s ease}
.tbtn:hover{background-color:var(--bg-page-alt);color:var(--text-primary)}
.tbtn[aria-pressed="true"]{background-color:var(--btn-primary-bg);color:var(--btn-primary-text);border-color:transparent}
.sw-name{font-size:.875rem;font-weight:600;color:var(--text-primary);margin:0}
.sw-hex{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.75rem;color:var(--text-muted)}
.chip{display:inline-block;padding:1px 8px;border-radius:9999px;border:1px solid var(--border-card);color:var(--text-muted);font-size:.65rem;font-weight:600;letter-spacing:.05em;text-transform:uppercase}
.ramp{display:flex;height:16px;border-radius:4px;overflow:hidden;margin-top:.7rem;border:1px solid var(--border-subtle)}
.ramp span{flex:1}
.specimen{padding:.9rem 0;border-bottom:1px dashed var(--border-subtle)}
.specimen:last-child{border-bottom:none}
.specimen .lead{color:var(--text-primary)}
.specimen .lbl{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.75rem;color:var(--text-muted);margin-bottom:.35rem}
.specimen .use{font-size:.75rem;color:var(--text-muted);margin-top:.4rem}
.motion{border:1px solid var(--border-card);border-radius:12px;padding:1rem;background-color:var(--bg-card)}
.mbox{width:100%;height:34px;border-radius:8px;background:linear-gradient(90deg,var(--color-accent),transparent);opacity:.85;margin-bottom:.6rem}
.motion:hover .m-lift{transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,.06)}
.motion:hover .m-press{transform:scale(.99)}
.motion:hover .m-state{background-color:var(--color-accent-hover)}
.m-lift,.m-press,.m-state{transition:transform .2s ease,box-shadow .2s ease,background-color .15s ease}
.sh-tile{height:70px;border-radius:12px;background-color:var(--bg-card);border:1px solid var(--border-card);display:flex;align-items:flex-end;padding:.6rem}
.rule{padding:.75rem 0;border-bottom:1px dashed var(--border-subtle)}
.rule:last-child{border-bottom:none}
.rule b{color:var(--text-primary)}
.rule .sec{font-size:.65rem;letter-spacing:.05em;text-transform:uppercase;color:var(--text-muted-lighter);margin-left:.4rem}
.rule p{margin:.3rem 0 0;color:var(--text-secondary);font-size:.875rem;line-height:1.6}
ul.dd{margin:0;padding-left:1.1rem;color:var(--text-secondary);font-size:.875rem;line-height:1.65}
ul.dd li{margin-bottom:.45rem}
ul.dd.dont{color:var(--text-secondary)}
.comp-head{display:flex;align-items:baseline;justify-content:space-between;gap:.5rem;margin-bottom:.2rem}
.comp-name{font-size:.9375rem;font-weight:600;margin:0}
.comp-desc{color:var(--text-muted);font-size:.8125rem;margin:.2rem 0 .9rem;line-height:1.55}
.stage{padding:1.25rem;border-radius:8px;background-color:var(--bg-page-alt);border:1px dashed var(--border-subtle);overflow-x:auto}
details{margin-top:.85rem}
summary{cursor:pointer;font-size:.75rem;color:var(--text-muted);font-weight:600;letter-spacing:.03em}
details pre{margin:.6rem 0 0;padding:.8rem;background-color:var(--bg-page-alt);border:1px solid var(--border-subtle);border-radius:8px;overflow-x:auto;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.75rem;color:var(--text-secondary);white-space:pre-wrap;word-break:break-word}
.foot{margin-top:4rem;padding-top:1.5rem;border-top:1px solid var(--border-subtle);color:var(--text-muted);font-size:.8125rem;line-height:1.7}
.foot code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background-color:var(--bg-page-alt);padding:1px 5px;border-radius:4px}
@media (prefers-reduced-motion: reduce){*{transition:none!important;animation:none!important}}
"""

VIEWER_JS = """
const DATA = JSON.parse(document.getElementById('design-data').textContent);
const E = (tag, cls, txt) => { const n = document.createElement(tag); if (cls) n.className = cls; if (txt != null) n.textContent = txt; return n; };
const hex = v => (v || '').replace(/"/g, '');

/* ---- theme switcher: the six shelves ---- */
const THEMES = ['modern','reader','dark','glass','contemporary','contemporary-dark'];
document.getElementById('themes').append(...THEMES.map(name => {
  const b = E('button', 'tbtn', name);
  b.type = 'button';
  b.setAttribute('aria-pressed', String(name === 'modern'));
  b.onclick = () => {
    document.body.className = 'theme-' + name;
    document.body.dataset.theme = name;
    [...document.querySelectorAll('.tbtn')].forEach(x => x.setAttribute('aria-pressed', String(x === b)));
  };
  return b;
}));

/* ---- colors + ramps ---- */
const cm = DATA.extensions.colorMeta;
const sw = document.getElementById('swatches');
Object.entries(cm).forEach(([key, c]) => {
  const t = E('div', 'tile');
  const head = E('div');
  head.style.cssText = 'display:flex;align-items:center;justify-content:space-between;gap:.5rem';
  head.append(E('p', 'sw-name', c.displayName));
  head.append(E('span', 'chip', c.role));
  t.append(head);
  const vals = E('div');
  vals.style.cssText = 'display:flex;align-items:center;gap:.6rem;margin-top:.5rem';
  const dot = E('span');
  dot.style.cssText = 'width:22px;height:22px;border-radius:6px;border:1px solid var(--border-subtle);flex:none';
  dot.style.backgroundColor = c.canonical;
  vals.append(dot, E('span', 'sw-hex', c.canonical + '  ' + key));
  t.append(vals);
  const ramp = E('div', 'ramp');
  (c.tonalRamp || []).forEach(h => { const s = E('span'); s.style.backgroundColor = h; s.title = h; ramp.append(s); });
  t.append(ramp);
  sw.append(t);
});

/* ---- typography specimens ---- */
const typo = document.getElementById('typo');
Object.entries(DATA.extensions.typographyMeta).forEach(([key, meta]) => {
  const spec = E('div', 'specimen');
  const lead = E('div', 'lead', 'The unexamined life is not worth living.');
  lead.style.fontFamily = 'var(--font-body)';
  lead.style.fontSize = 'var(--spec-size)';
  spec.style.setProperty('--spec-size', (DATA.__frontmatter.typography[key] || {}).fontSize || '1rem');
  lead.style.fontWeight = (DATA.__frontmatter.typography[key] || {}).fontWeight || 400;
  lead.style.lineHeight = (DATA.__frontmatter.typography[key] || {}).lineHeight || 1.5;
  lead.style.letterSpacing = (DATA.__frontmatter.typography[key] || {}).letterSpacing || 'normal';
  if ((DATA.__frontmatter.typography[key] || {}).letterSpacing) lead.style.textTransform = 'uppercase';
  const fam = (DATA.__frontmatter.typography[key] || {}).fontFamily;
  if (fam) lead.style.fontFamily = fam;
  if (key === 'quote') lead.textContent = '"The unexamined life is not worth living." - Socrates';
  if (key === 'mono') lead.textContent = 'K KOREADER readwise 1,284';
  const lbl = E('div', 'lbl', key + '  |  ' + fam + '  |  ' + (DATA.__frontmatter.typography[key].fontSize) + '  |  weight ' + DATA.__frontmatter.typography[key].fontWeight + '  |  lh ' + DATA.__frontmatter.typography[key].lineHeight + (DATA.__frontmatter.typography[key].letterSpacing ? '  |  ls ' + DATA.__frontmatter.typography[key].letterSpacing : ''));
  const use = E('div', 'use', meta.purpose);
  spec.append(lbl, lead, use);
  typo.append(spec);
});

/* ---- shadows ---- */
const sh = document.getElementById('shadows');
DATA.extensions.shadows.forEach(s => {
  const t = E('div', 'tile');
  const box = E('div', 'sh-tile');
  box.style.boxShadow = s.value;
  box.append(E('span', 'sw-hex', s.name));
  t.append(box, E('div', 'use', s.purpose));
  const code = E('div', 'sw-hex');
  code.style.marginTop = '.45rem';
  code.textContent = s.value;
  t.append(code);
  sh.append(t);
});

/* ---- motion ---- */
const mo = document.getElementById('motion');
DATA.extensions.motion.forEach(m => {
  const t = E('div', 'motion');
  const cls = m.name.indexOf('lift') > -1 ? 'm-lift' : m.name.indexOf('press') > -1 ? 'm-press' : 'm-state';
  const box = E('div', 'mbox ' + cls);
  t.append(box, E('div', 'comp-name', m.name));
  t.append(E('div', 'use', m.value + ' - ' + m.purpose));
  mo.append(t);
});

/* ---- breakpoints ---- */
DATA.extensions.breakpoints.forEach(b => {
  const row = E('div');
  row.style.cssText = 'display:flex;gap:1rem;align-items:baseline;padding:.5rem 0;border-bottom:1px dashed var(--border-subtle)';
  const name = E('span', 'sw-name', b.name);
  name.style.minWidth = '13rem';
  row.append(name, E('span', 'sw-hex', b.value));
  document.getElementById('breakpoints').append(row);
});

/* ---- components: one shadow root each, CSS as shipped in the sidecar ---- */
const host = document.getElementById('components');
DATA.components.forEach(c => {
  const t = E('div', 'tile');
  const head = E('div', 'comp-head');
  head.append(E('p', 'comp-name', c.name), E('span', 'chip', c.kind));
  t.append(head, E('div', 'comp-desc', c.description));
  const stage = E('div', 'stage');
  const el = document.createElement('div');
  el.style.cssText = 'display:block';
  stage.append(el);
  const root = el.attachShadow({ mode: 'open' });
  const style = document.createElement('style');
  style.textContent = c.css;
  root.append(style);
  const holder = document.createElement('div');
  holder.innerHTML = c.html;
  root.append(holder);
  t.append(stage);
  const det = document.createElement('details');
  det.append(E('summary', null, 'html + css'));
  const pre = E('pre', null, c.html + '\\n\\n' + c.css);
  det.append(pre);
  t.append(det);
  host.append(t);
});

/* ---- narrative: rules, do's, don'ts ---- */
DATA.narrative.rules.forEach(r => {
  const box = E('div', 'rule');
  const b = E('b', null, 'The ' + r.name.replace(/^The /, ''));
  box.append(b, E('span', 'sec', r.section), E('p', null, r.body));
  document.getElementById('rules').append(box);
});
const dos = document.getElementById('dos');
DATA.narrative.dos.forEach(d => dos.append(E('li', null, d)));
const donts = document.getElementById('donts');
DATA.narrative.donts.forEach(d => donts.append(E('li', null, d)));

/* ---- header meta ---- */
document.getElementById('overview').textContent = DATA.narrative.overview.replace(/\\n\\n/g, ' ');
"""

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Commonplace - design system preview</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@100..900&family=Jost:wght@100..900&family=Source+Serif+4:wght@400..700&family=Overpass+Mono&display=swap" rel="stylesheet">
<style id="project-themes">
__THEMES_CSS__
</style>
<style>
__VIEWER_CSS__
</style>
</head>
<body class="theme-modern" data-theme="modern">
<div class="wrap">
  <header class="top">
    <h1>Commonplace - design system preview</h1>
    <p class="sub">Rendered from <strong>.impeccable/design.json</strong> over the real <strong>app/static/themes.css</strong>. North Star: <strong>__NORTH_STAR__</strong>.</p>
    <p class="meta">__META__ - this file is generated; regenerate with <code>python3 .impeccable/build-preview.py</code></p>
    <div class="themebar" id="themes"></div>
  </header>

  <p class="sub" id="overview" style="margin-top:1.5rem;line-height:1.75;color:var(--text-secondary)"></p>

  <h2>Colors <span class="chip">__NCOLORS__ tokens x 8-step OKLCH ramps</span></h2>
  <div class="grid cols-sw" id="swatches"></div>

  <h2>Typography</h2>
  <div class="tile" id="typo"></div>

  <h2>Elevation &amp; Depth</h2>
  <div class="grid cols-comp" id="shadows"></div>

  <h2>Motion <span class="chip">hover each tile</span></h2>
  <div class="grid cols-comp" id="motion"></div>

  <h2>Breakpoints</h2>
  <div class="tile" id="breakpoints"></div>

  <h2>Components <span class="chip">__NCOMP__ - live shadow DOM, re-themes with the switcher</span></h2>
  <div class="grid cols-comp" id="components"></div>

  <h2>Named Rules</h2>
  <div class="tile" id="rules"></div>

  <h2>Do's and Don'ts</h2>
  <div class="grid cols-comp">
    <div class="tile"><h3>Do</h3><ul class="dd" id="dos"></ul></div>
    <div class="tile"><h3>Don't</h3><ul class="dd dont" id="donts"></ul></div>
  </div>

  <div class="foot">
    Generated __GENERATED__ from <code>.impeccable/design.json</code> and <code>app/static/themes.css</code>.<br>
    Switch themes above to check a change on all six shelves - the tiles use the project's own <code>var()</code> tokens, so what you see is what the app does.<br>
    Named rules, Do's and Don'ts are quoted verbatim from <code>DESIGN.md</code>.
  </div>
</div>
<script type="application/json" id="design-data">__DESIGN_JSON__</script>
<script>
__VIEWER_JS__
</script>
</body>
</html>
"""

payload = dict(design)
payload["__frontmatter"] = {"typography": frontmatter.get("typography", {})}
n_colors = len(design["extensions"]["colorMeta"])
n_comp = len(design["components"])
generated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
html = (HTML
        .replace("__THEMES_CSS__", safe(themes_css))
        .replace("__VIEWER_CSS__", VIEWER_CSS)
        .replace("__VIEWER_JS__", VIEWER_JS)
        .replace("__DESIGN_JSON__", safe(json.dumps(payload)))
        .replace("__NORTH_STAR__", design["narrative"]["northStar"])
        .replace("__META__", "%d color tokens, %d components, %d rules, %d do's / %d don'ts" % (
            n_colors, n_comp, len(design["narrative"]["rules"]),
            len(design["narrative"]["dos"]), len(design["narrative"]["donts"])))
        .replace("__NCOLORS__", str(n_colors))
        .replace("__NCOMP__", str(n_comp))
        .replace("__GENERATED__", generated))

open(OUT, "w").write(html)
print("wrote", OUT, len(html), "bytes")
