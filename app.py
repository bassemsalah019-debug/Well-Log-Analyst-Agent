"""Well Log Analyst: a Streamlit front end that reproduces the Lovable design.

Run from this folder:
    uv run streamlit run app.py

The analysis code in phase1_training/ is used as it is. This file only shows what the existing
functions and the agent return. Theme colors are in .streamlit/config.toml (light) and
.streamlit/style.css (light and dark tokens, plus the page styling).
"""

import base64
import html
import math
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlencode

import numpy as np
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "phase1_training"))

from comparison import curve_difference, match_depths  # noqa: E402
from config import INPUT_CURVES, MEMORY_FILE, REPORTS_DIR  # noqa: E402
from las_io import available_wells, find_well, load_input  # noqa: E402
from memory import memory_settings  # noqa: E402
from petrophysics import evaluate_well, summarize  # noqa: E402
from tools import analyze_well, format_intervals  # noqa: E402

CSS_FILE = ROOT / ".streamlit" / "style.css"
ASSETS = Path(__file__).parent / "assets"
FAVICON = ASSETS / "favicon.ico"

# Curve names shown in the dictionary (Lovable src/lib/wells.ts); the mnemonics come from config.py.
CURVE_LABELS = {"GR": "Gamma ray", "RHOB": "Bulk density", "NPHI": "Neutron porosity", "RT": "Deep resistivity"}

# A difference above this is drawn in the warn color on the Lovable well page (d > 0.1),
# so a well with any such difference is listed as "Needs review".
REVIEW_LIMIT = 0.1

STATUS = {  # Lovable StatusBadge, with the tool's wording for wells without Hugin
    "ok": ("Matches Equinor", "text-ok", "bg-ok"),
    "review": ("Needs review", "text-warn", "bg-warn"),
    "none": ("No Hugin Fm.", "text-muted-foreground", "bg-muted-foreground"),
}

# Field schematic: display-only positions on a 0-100 square, reused from the Lovable layout.
# They are NOT survey coordinates (all nine wells were drilled from one platform).
SCHEMATIC_XY = {"F-1": (20, 30), "F-1_A": (28, 40), "F-1_B": (35, 26), "F-1_C": (45, 35), "F-11_A": (52, 72),
                "F-11_B": (66, 62), "F-11_T2": (58, 50), "F-12": (74, 40), "F-15_D": (82, 68)}
TARGET_OUTLINE = [(26, 20), (48, 18), (80, 30), (92, 65), (86, 80), (50, 84), (22, 48)]

# Lucide icons used by the Lovable design (inner SVG of a 24x24, 2px-stroke icon).
LUCIDE = {
    "activity": '<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>',
    "layout-dashboard": '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
    "bot": '<path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/>',
    "file-text": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    "waves": '<path d="M2 6c.6.5 1.2 1 2.5 1C7 7 7 5 9.5 5c2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M2 12c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M2 18c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>',
    "chevron-right": '<path d="m9 18 6-6-6-6"/>',
    "arrow-up-right": '<path d="M7 7h10v10"/><path d="M7 17 17 7"/>',
    "log-in": '<path d="m10 17 5-5-5-5"/><path d="M15 12H3"/><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>',
    "moon": '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "map-pin": '<path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/>',
    "arrow-right": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "arrow-left": '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
    "arrow-up": '<path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>',
    "sliders-horizontal": '<line x1="21" x2="14" y1="4" y2="4"/><line x1="10" x2="3" y1="4" y2="4"/><line x1="21" x2="12" y1="12" y2="12"/><line x1="8" x2="3" y1="12" y2="12"/><line x1="21" x2="16" y1="20" y2="20"/><line x1="12" x2="3" y1="20" y2="20"/><line x1="14" x2="14" y1="2" y2="6"/><line x1="8" x2="8" y1="10" y2="14"/><line x1="16" x2="16" y1="18" y2="22"/>',
    "pause": '<rect x="14" y="4" width="4" height="16" rx="1"/><rect x="6" y="4" width="4" height="16" rx="1"/>',
    "play": '<polygon points="6 3 20 12 6 21 6 3"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "x": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    "pencil": '<path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/><path d="m15 5 4 4"/>',
    "file-check": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="m9 15 2 2 4-4"/>',
    "plus": '<path d="M5 12h14"/><path d="M12 5v14"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
    "building-2": '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/><path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/><path d="M10 18h4"/>',
    "lock-keyhole": '<circle cx="12" cy="16" r="1"/><rect x="3" y="10" width="18" height="12" rx="2"/><path d="M7 10V7a5 5 0 0 1 10 0v3"/>',
    "eye": '<path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/>',
    "eye-off": '<path d="M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49"/><path d="M14.084 14.158a3 3 0 0 1-4.242-4.242"/><path d="M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143"/><path d="m2 2 20 20"/>',
}

# Client-side behavior that Lovable runs in React: the appearance toggle (same storage key and
# system-theme fallback as Appearance.tsx), the schematic pause button, the inventory search and
# filter, schematic well links, and the sign-in preview (nothing is sent anywhere).
PAGE_SCRIPT = """<script>
(function () {
  var KEY = "well-log-appearance", root = document.documentElement;
  function label(t) { return t === "dark" ? "Switch to light mode" : "Switch to dark mode"; }
  function apply(t) {
    root.classList.toggle("dark", t === "dark");
    root.style.colorScheme = t;
    document.querySelectorAll(".wl-theme-toggle").forEach(function (b) { b.setAttribute("aria-label", label(t)); b.title = label(t); });
  }
  function filterInventory(box) {
    var q = box.querySelector(".wl-inv-search").value.toLowerCase(), s = box.querySelector(".wl-inv-filter").value, n = 0;
    box.querySelectorAll("tbody tr").forEach(function (tr) {
      var show = tr.dataset.name.toLowerCase().indexOf(q) >= 0 && (s === "all" || tr.dataset.status === s);
      tr.style.display = show ? "" : "none"; if (show) n++;
    });
    box.querySelector(".wl-inv-count").textContent = n;
    box.querySelector(".wl-inv-empty").style.display = n ? "none" : "block";
  }
  function signIn(form) {
    var fields = form.querySelectorAll("input");
    for (var i = 0; i < fields.length; i++) { if (!fields[i].reportValidity()) return; }
    var msg = form.querySelector(".wl-auth-message");
    msg.textContent = "Company sign-in is not connected yet. This preview does not authenticate or save account data.";
    msg.style.display = "block";
  }
  if (!window.__wellLogUi) {
    window.__wellLogUi = true;
    var t = "light";
    try {
      var saved = localStorage.getItem(KEY);
      t = saved === "dark" || (saved !== "light" && window.matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light";
    } catch (e) { /* Use the light theme when storage is unavailable. */ }
    apply(t);
    new MutationObserver(function () { apply(root.classList.contains("dark") ? "dark" : "light"); })
      .observe(document.body, { childList: true, subtree: true });
    document.addEventListener("click", function (e) {
      var b = e.target.closest(".wl-theme-toggle");
      if (b) {
        var next = root.classList.contains("dark") ? "light" : "dark";
        apply(next);
        try { localStorage.setItem(KEY, next); } catch (err) { /* Theme still works without storage. */ }
        return;
      }
      var p = e.target.closest(".wl-map-toggle");
      if (p) {
        var map = p.closest(".wl-schematic").querySelector(".field-schematic"), paused = map.classList.toggle("map-paused");
        var l = paused ? "Resume map animation" : "Pause map animation";
        p.setAttribute("aria-label", l); p.title = l; p.classList.toggle("is-paused", paused);
        return;
      }
      var eye = e.target.closest(".wl-eye");
      if (eye) {
        var input = eye.parentElement.querySelector("input"), visible = input.type === "password";
        input.type = visible ? "text" : "password"; eye.classList.toggle("is-visible", visible);
        var el = visible ? "Hide password" : "Show password"; eye.setAttribute("aria-label", el); eye.title = el;
        return;
      }
      var go = e.target.closest(".wl-signin");
      if (go) { signIn(go.closest(".wl-auth-form")); return; }
      var w = e.target.closest("[data-href]");
      if (w) { window.location.href = w.getAttribute("data-href"); }
    });
    document.addEventListener("keydown", function (e) {
      var w = e.target.closest && e.target.closest("[data-href]");
      if (w && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); window.location.href = w.getAttribute("data-href"); }
      var f = e.target.closest && e.target.closest(".wl-auth-form");
      if (f && e.key === "Enter" && e.target.tagName === "INPUT") { e.preventDefault(); signIn(f); }
    });
    ["input", "change"].forEach(function (ev) {
      document.addEventListener(ev, function (e) {
        if (e.target.matches && e.target.matches(".wl-inv-search, .wl-inv-filter")) filterInventory(e.target.closest(".wl-inventory"));
      });
    });
  }
})();
</script>"""


# ── Small HTML helpers ─────────────────────────────────────────────────────────
def esc(text) -> str:
    return html.escape(str(text), quote=True)


def icon(name: str, size: int = 16, cls: str = "") -> str:
    return (f'<svg class="{cls}" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{LUCIDE[name]}</svg>')


def mask(name: str) -> str:
    """A lucide icon as a CSS mask image, so Streamlit buttons and links can show it in currentColor."""
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' "
           f"stroke-linecap='round' stroke-linejoin='round'>{LUCIDE[name]}</svg>")
    return f'url("data:image/svg+xml,{quote(svg)}")'


def widget_icon(key: str, name: str, size: int = 16, side: str = "before", rotate: int = 0) -> None:
    """Add a lucide icon before or after the label of the button/link with this key."""
    turn = f"transform:rotate({rotate}deg);" if rotate else ""
    css = (f".st-key-{key} :is(button, a)::{side}{{content:'';flex:none;width:{size}px;height:{size}px;"
           f"background:currentColor;-webkit-mask:{mask(name)} center/contain no-repeat;mask:{mask(name)} center/contain no-repeat;{turn}}}")
    st.session_state.setdefault("_css", []).append(css)


def html_block(body: str, width="stretch") -> None:
    """Raw HTML through st.markdown (st.html would strip the SVG). Newlines become entities so a blank
    line in a report cannot end the HTML block, and links stay in this tab."""
    body = body.replace("\n", "&#10;").replace("<a href=", '<a target="_self" href=')
    st.markdown(f'<div class="wl">{body}</div>', unsafe_allow_html=True, width=width)


def nav_link(page, label: str, key: str, ico: str | None = None, side: str = "before", size: int = 16,
             query: dict | None = None, width="content") -> None:
    """A Streamlit page link (keeps the session) styled by its key prefix in style.css."""
    with st.container(key=key, width=width, gap=None):
        st.page_link(page, label=label, query_params=query, width="stretch" if width == "stretch" else "content")
    if ico:
        widget_icon(key, ico, size, side)


def url(path: str, **params) -> str:
    """Relative link to another page. HTML links reload the page; the theme is kept in browser storage."""
    return path + ("?" + urlencode(params) if params else "")


def display_name(well: str) -> str:
    """'F-15_D' -> 'F-15 D', the way the Lovable design writes well names."""
    return well.replace("_", " ")


def natural_key(well: str) -> list:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", well)]


def badge(status: str) -> str:
    text, color, _ = STATUS[status]
    return (f'<span class="inline-flex items-center gap-1.5 whitespace-nowrap text-[11px] {color}">'
            f'<span class="size-1 rounded-full bg-current"></span>{text}</span>')


@st.cache_resource(show_spinner=False)
def image_uri(name: str) -> str | None:
    path = ASSETS / name
    if not path.exists():
        return None
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()


def cover_image(name: str, alt: str, cls: str) -> str:
    src = image_uri(name)
    return f'<img src="{src}" alt="{esc(alt)}" class="{cls}">' if src else f'<div class="{cls} bg-shell"></div>'


# ── Data: only the existing project functions, cached per AGENTS.md version ───────────────────
def memory_stamp() -> float:
    """AGENTS.md is read on every tool call, so a change to it must refresh the cached numbers."""
    return MEMORY_FILE.stat().st_mtime


def wells() -> list[str]:
    return sorted(available_wells(), key=natural_key)


@st.cache_data(show_spinner=False)
def well_facts(well: str, stamp: float) -> dict:
    """Hugin results of one well from the functions behind analyze_well and compare_with_equinor."""
    facts = {"name": well, "status": "none", "note": None, "intervals": None,
             "ng": None, "phif": None, "sw": None, "k_arith": None, "k_geo": None, "diff": None}
    settings = memory_settings()["wells"]
    p = settings.get(well)
    _, found, _ = load_input(well)
    if p is None or any(c not in found for c in INPUT_CURVES):
        facts["note"] = analyze_well.invoke({"well_name": well})   # the tool's own wording
        if well not in settings or p is not None:
            facts["status"] = "missing"
        return facts

    df, _, p, _ = evaluate_well(well)
    s = summarize(df)
    if s is None:
        facts["note"], facts["status"] = analyze_well.invoke({"well_name": well}), "missing"
        return facts
    both = match_depths(well)
    diff = {}
    for curve in ("VSH", "PHIF", "SW"):
        d = curve_difference(both, curve)
        diff[curve.lower()] = None if d is None else float(d["mae"])
    review = any(v is not None and v > REVIEW_LIMIT for v in diff.values())
    facts.update(status="review" if review else "ok", intervals=p["intervals"], ng=float(s["ng"]),
                 phif=float(s["phif_net"]), sw=float(s["sw_net"]), k_arith=float(s["k_arith"]),
                 k_geo=float(s["k_geo"]), diff=diff)
    return facts


@st.cache_data(show_spinner=False)
def well_tracks(well: str, stamp: float) -> dict:
    """Curves for the log viewer: raw logs (load_input) and, in the Hugin zone, this agent's
    VSH/PHIF/SW next to Equinor's (match_depths). Thinned to about 600 samples for drawing."""
    raw, _, _ = load_input(well)
    p = memory_settings()["wells"].get(well)
    if p:
        top, base = min(t for t, _ in p["intervals"]), max(b for _, b in p["intervals"])
        lo, hi = top - 120, base + 120                  # same 120 m margin as the Lovable viewer
    else:
        lo, hi = float(raw.index.min()), float(raw.index.max())
    window = raw.loc[(raw.index >= lo) & (raw.index <= hi)]
    k = max(1, math.ceil(len(window) / 600))
    shown = window.iloc[::k]
    out = {"lo": lo, "hi": hi, "intervals": p["intervals"] if p else [],
           "depth": shown.index.to_numpy(float), "raw": {c: shown[c].to_numpy(float) for c in shown.columns}}
    if p:
        both = match_depths(well).iloc[::k]
        out["hugin_depth"] = both["DEPTH"].to_numpy(float)
        out["interp"] = {c: both[c].to_numpy(float) for c in both.columns if c != "DEPTH" and both[c].dtype.kind == "f"}
    return out


def report_files() -> list[Path]:
    REPORTS_DIR.mkdir(exist_ok=True)
    return sorted(REPORTS_DIR.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)


# ── Shell: sidebar, header, footer (Lovable __root.tsx) ─────────────────────────────────────
NAV = [("index", "Field overview", "layout-dashboard"), ("agent", "Analysis agent", "bot"),
       ("reports", "Reports", "file-text"), ("dictionary", "Curve dictionary", "waves")]


def sidebar(current: str) -> None:
    with st.sidebar, st.container(key="sb", gap=None):
        html_block(
            f'<a href="{url("./")}" class="flex items-center gap-3 px-6 py-8 sb-logo">{icon("activity", 28, "text-heritage")}'
            '<span class="font-display text-lg leading-tight">Well Log<span class="mt-1 block font-sans text-xs text-shell-muted">Analyst workspace</span></span></a>'
            '<div class="mx-6 mb-6 border-t border-shell-muted/20 pt-6"><p class="text-[10px] uppercase text-shell-muted">Active asset</p>'
            '<div class="mt-2 flex items-center justify-between text-sm">Volve field <span class="size-1.5 rounded-full bg-ok"></span></div>'
            '<p class="mt-1 text-xs text-shell-muted">North Sea, Norway</p></div>')
        with st.container(key="sb-nav", gap=None):
            for name, label, ico in NAV:
                state = "navon" if name == current else "navoff"
                nav_link(PAGES[name], label, f"lk-{state}-{name}", ico, width="stretch")
        with st.container(key="sb-foot", gap=None):
            html_block(
                '<div class="px-6 py-6"><div class="border-t border-shell-muted/20 pt-5">'
                '<p class="flex items-center gap-2 text-xs"><span class="size-1.5 rounded-full bg-warn"></span>Preview workspace</p>'
                '<p class="mt-2 text-[11px] leading-relaxed text-shell-muted">Illustrative data · not for operational use</p></div>'
                '<div class="mt-6 flex items-center gap-3"><span class="grid size-8 place-items-center rounded-full bg-shell-foreground/10 text-xs">PE</span>'
                '<div><p class="text-xs">Petrophysics</p><p class="text-[10px] text-shell-muted">Interpretation workspace</p></div></div></div>')


def theme_toggle() -> str:
    return (f'<button type="button" class="wl-theme-toggle btn-ghost size-8" aria-label="Switch to dark mode" '
            f'title="Switch to dark mode">{icon("moon", 16, "i-moon")}{icon("sun", 16, "i-sun")}</button>')


def header(current: str) -> None:
    with st.container(key="wl-header", horizontal=True, vertical_alignment="center", gap=None):
        html_block(f'<div class="flex items-center gap-2 text-xs text-muted-foreground">{icon("activity", 20, "text-primary lg:hidden")}'
                   f'<span class="hidden sm:inline">Workspace</span>{icon("chevron-right", 12, "hidden sm:inline")}'
                   '<span class="text-foreground">Volve field</span></div>')
        html_block('<div class="flex items-center gap-1 sm:gap-3"><span class="label-mono hidden xl:inline">Hugin formation</span>'
                   '<span class="hidden border-l pl-3 text-xs text-muted-foreground sm:inline">From Volve LAS files</span>'
                   f'{theme_toggle()}</div>', width="content")
        nav_link(PAGES["agent"], "Open agent", "lk-ghost-openagent", "arrow-up-right", side="after")
        nav_link(PAGES["auth"], "Company sign in", "lk-outline-signin", "log-in")
    with st.container(key="wl-mnav", horizontal=True, gap=None):
        for name, label, ico in NAV:
            state = "mnavon" if name == current else "mnavoff"
            nav_link(PAGES[name], label, f"lk-{state}-{name}", ico, size=14)


def footer() -> None:
    html_block('<footer class="mx-5 mt-10 flex flex-wrap justify-between gap-2 border-t py-4 text-[10px] text-muted-foreground lg:mx-8">'
               '<span>WELL LOG ANALYST / VOLVE</span><span>Illustrative interpretations · Equinor reference workflow</span></footer>')


def page_title(label: str, number: str, title: str, extra: str = "") -> str:
    return f'<p class="label-mono">{label} / {number}</p><h1 class="mt-1 text-2xl font-semibold">{title}</h1>{extra}'


# ── 1. Field overview (routes/index.tsx) ─────────────────────────────────────────────────────
def field_schematic(facts: list[dict]) -> str:
    def inside(x, y):
        hit, j = False, len(TARGET_OUTLINE) - 1
        for i, (ax, ay) in enumerate(TARGET_OUTLINE):
            bx, by = TARGET_OUTLINE[j]
            if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
                hit = not hit
            j = i
        return hit

    marks, n_in, outside = [], 0, []
    for f in facts:
        if f["name"] not in SCHEMATIC_XY:
            continue
        x, y = SCHEMATIC_XY[f["name"]]
        name, ok = display_name(f["name"]), inside(x, y)
        n_in += ok
        if not ok:
            outside.append(f)
        dot = ("fill-map-ink stroke-cover-foreground" if not ok else
               "fill-map-alert stroke-map-ink" if f["status"] == "review" else "fill-cover-foreground stroke-map-ink")
        pulse = (f'<circle cx="{x}" cy="{y}" r="2.6" class="well-pulse fill-none stroke-map-alert" stroke-width=".4"/>'
                 if f["status"] == "review" else "")
        tag = (f'<text x="{x - 4}" y="{y - 4}" class="map-label fill-cover-foreground font-mono" font-size="2.6">OUTSIDE</text>'
               if not ok else "")
        marks.append(f'<g class="map-well" role="link" tabindex="0" data-href="{url("wells", id=f["name"])}" '
                     f'aria-label="Open {esc(name)} from field schematic"><circle cx="{x}" cy="{y}" r="4" fill="transparent"/>{pulse}'
                     f'<circle cx="{x}" cy="{y}" r="1.25" class="{dot}" stroke-width=".4"/>'
                     f'<text x="{x + 2.6}" y="{y + 1}" class="map-label fill-cover-foreground font-mono" font-size="3.1">{esc(name)}</text>{tag}</g>')
    outline = " ".join(f"{x},{y}" for x, y in TARGET_OUTLINE)
    outside_text = " · ".join(f'{esc(display_name(f["name"]))} · {STATUS[f["status"]][0] if f["status"] in STATUS else ""}'
                              for f in outside)
    return (
        '<div class="wl-schematic"><div class="flex items-center justify-between"><h2 class="text-sm font-semibold">Field schematic</h2>'
        f'<button type="button" class="wl-map-toggle btn-ghost size-7" aria-label="Pause map animation" title="Pause map animation">'
        f'{icon("pause", 16, "i-pause")}{icon("play", 16, "i-play")}</button></div>'
        '<div class="field-schematic relative mt-3 aspect-square overflow-hidden">'
        + cover_image("field-seabed.jpg", "Illustrative seabed relief, not surveyed Volve bathymetry", "absolute inset-0 h-full w-full object-cover")
        + '<div class="seabed-shade absolute inset-0"></div>'
        '<svg viewBox="0 0 100 100" class="relative h-full w-full" aria-label="Illustrative Volve well locations">'
        '<path d="M10 20H90 M10 40H90 M10 60H90 M10 80H90 M20 10V90 M40 10V90 M60 10V90 M80 10V90" class="stroke-cover-foreground/15" stroke-width=".2"/>'
        f'<polygon points="{outline}" class="fill-map-alert/10 stroke-map-alert" stroke-width=".65" stroke-dasharray="2 1.2" stroke-linejoin="round"/>'
        '<text x="44" y="89" class="map-label fill-map-alert font-mono" font-size="2.8">HUGIN TARGET SCOPE</text>'
        '<path d="M20 30 Q36 28 45 35 T58 50 Q70 53 82 68 M28 40 Q42 44 58 50 M35 26 Q45 38 58 50 M52 72 Q59 57 58 50 M66 62 Q61 55 58 50 M74 40 Q67 47 58 50" '
        'class="stroke-cover-foreground/35" fill="none" stroke-width=".35" stroke-dasharray="1.5 1"/>'
        + "".join(marks) +
        '</svg><span class="absolute right-3 top-2 font-mono text-[10px] text-cover-foreground">N ↑</span>'
        '<span class="absolute bottom-2 left-3 font-mono text-[8px] text-cover-foreground/80">VOLVE / HUGIN</span></div>'
        '<div class="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-[10px] text-muted-foreground">'
        '<span class="flex items-center gap-1.5"><span class="w-4 border-t border-dashed border-warn"></span>Target outline</span>'
        f'<span>{n_in} inside · {len(outside)} outside</span></div>'
        + (f'<p class="mt-2 text-[10px] text-muted-foreground">Outside: {outside_text}</p>' if outside else "")
        + '<p class="mt-2 text-[9px] leading-4 text-muted-foreground">Illustrative Hugin scope · not a geographic boundary</p></div>')


def page_index() -> None:
    st.set_page_config(page_title="Volve Field Overview · Well Log Analyst")
    with st.spinner("Reading the Volve wells…"):
        facts = [well_facts(w, memory_stamp()) for w in wells()]
    flagged = [f for f in facts if f["status"] == "review"]

    with st.container(key="idx-top", horizontal=True, vertical_alignment="center", gap=None):
        html_block(page_title("Asset intelligence", "01", "Field overview"))
        nav_link(PAGES["agent"], "New analysis", "lk-outline-newanalysis", "arrow-up-right", side="after")

    kpis = [("Total wells", len(facts), "Volve inventory"),
            ("Hugin intervals", sum(f["status"] in ("ok", "review") for f in facts), "Formation identified"),
            ("Within tolerance", sum(f["status"] == "ok" for f in facts), "Matches reference"),
            ("Review required", len(flagged), "Interpretation differences")]
    kpi_html = "".join(
        f'<div class="kpi px-5 py-2 {"sm:border-l" if i else ""}"><p class="text-xs text-muted-foreground">{label}</p>'
        f'<div class="mt-2 font-mono text-3xl {"text-warn" if i == 3 else ""}">{value:02d}</div>'
        f'<p class="mt-2 text-[10px] text-muted-foreground">{sub}</p></div>' for i, (label, value, sub) in enumerate(kpis))

    rows = []
    for f in facts:
        name, link = display_name(f["name"]), url("wells", id=f["name"])
        dot = STATUS.get(f["status"], STATUS["none"])[2]
        values = "".join(f'<td class="px-3 font-mono text-muted-foreground">{"—" if v is None else f"{v:.3f}"}</td>'
                         for v in (f["ng"], f["phif"], f["sw"]))
        status_cell = badge(f["status"]) if f["status"] in STATUS else '<span class="text-[11px] text-muted-foreground">—</span>'
        rows.append(f'<tr class="border-b" data-name="{esc(name)}" data-status="{f["status"]}">'
                    f'<td class="py-4 pl-0 pr-3"><a href="{link}" class="flex items-center gap-2 font-mono font-medium">'
                    f'<span class="size-1.5 rounded-full {dot}"></span>{esc(name)}</a></td>{values}'
                    f'<td class="px-3">{status_cell}</td><td class="pr-1"><a href="{link}" class="btn-ghost size-7" '
                    f'aria-label="View {esc(name)}">{icon("arrow-up-right", 16)}</a></td></tr>')
    heads = "".join(f'<th class="px-3 py-3 font-normal">{h}</th>' for h in ["Well", "N/G", "PHIF", "SW", "QC status", ""])
    queue = "".join(
        f'<a href="{url("wells", id=f["name"])}" class="mt-4 flex items-center justify-between border-b pb-3"><div>'
        f'<p class="font-mono text-xs">{esc(display_name(f["name"]))}</p>'
        f'<p class="mt-1 text-[10px] text-warn">SW deviation +{f["diff"]["sw"]:.3f}</p></div>'
        f'{icon("arrow-right", 16, "text-muted-foreground")}</a>' for f in flagged)
    options = "".join(f'<option value="{k}">{v}</option>' for k, v in
                      [("all", "All statuses"), ("ok", STATUS["ok"][0]), ("review", STATUS["review"][0]), ("none", STATUS["none"][0])])

    html_block(
        '<section class="field-cover relative mt-5 min-h-[245px] overflow-hidden">'
        + cover_image("volve-platform.jpg", "Illustrative offshore platform in the Norwegian North Sea",
                      "absolute inset-0 h-full w-full object-cover object-right")
        + f'<div class="relative z-1 px-7 py-8 text-cover-foreground sm:px-9"><p class="flex items-center gap-2 text-xs">{icon("map-pin", 14)}North Sea · Norway</p>'
        '<h2 class="mt-5 text-5xl font-medium">Volve field</h2>'
        '<p class="mt-3 text-sm text-cover-foreground/80">Hugin formation / Petrophysical interpretation</p>'
        '<div class="mt-6 flex items-center gap-2 text-[11px] text-cover-foreground/75"><span class="size-1.5 rounded-full bg-cover-foreground"></span>'
        f'Equinor reference dataset<span class="mx-2">/</span>{len(facts)} wells</div></div>'
        '<span class="absolute bottom-3 right-4 z-1 text-[9px] text-cover-foreground/70">Illustrative platform image</span></section>'
        f'<section class="grid grid-cols-2 border-b py-6 sm:grid-cols-4">{kpi_html}</section>'
        '<div class="mt-7 grid gap-8 xl:grid-cols-[minmax(0,1fr)_285px]">'
        '<section class="wl-inventory min-w-0"><div class="flex flex-wrap items-center justify-between gap-3">'
        f'<h2 class="text-base font-semibold">Well inventory <span class="ml-2 text-xs font-normal text-muted-foreground"><span class="wl-inv-count">{len(facts)}</span> wells</span></h2>'
        f'<div class="flex items-center gap-2">{icon("search", 16, "text-muted-foreground")}'
        '<input aria-label="Search wells" placeholder="Search wells" class="wl-inv-search w-32 border-0 bg-transparent py-2 text-xs">'
        f'{icon("sliders-horizontal", 14, "text-muted-foreground")}'
        f'<select aria-label="Filter well status" class="wl-inv-filter max-w-32 bg-transparent py-2 text-xs">{options}</select></div></div>'
        '<div class="mt-3 overflow-x-auto"><table class="inventory w-full whitespace-nowrap text-left text-xs">'
        f'<thead class="border-y bg-muted/50 text-[10px] uppercase text-muted-foreground"><tr>{heads}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
        '<p class="wl-inv-empty py-8 text-center text-sm text-muted-foreground" style="display:none">No matching wells.</p></div>'
        '<p class="mt-3 text-[10px] text-muted-foreground">N/G net-to-gross · PHIF effective porosity · SW water saturation · From analyze_well</p></section>'
        f'<aside class="border-t pt-5 xl:border-l xl:border-t-0 xl:pl-6 xl:pt-0">{field_schematic(facts)}'
        f'<div class="mt-6 border-t pt-5"><p class="label-mono">Review queue</p><h3 class="mt-2 text-sm">{len(flagged)} wells need attention</h3>{queue}</div>'
        '</aside></div>')


# ── 2. Well detail (routes/wells.$id.tsx) ────────────────────────────────────────────────────
def curve_points(depth, values, lo, hi, vmin, vmax, log=False) -> list[str]:
    """SVG polyline point lists for one curve, broken where data is missing or the depths jump."""
    v = np.asarray(values, float)
    if log:
        v, vmin, vmax = np.log10(np.maximum(v, 0.1)), math.log10(vmin), math.log10(vmax)
    x = (v - vmin) / (vmax - vmin) * 100
    y = (np.asarray(depth, float) - lo) / (hi - lo) * 600
    step = float(np.median(np.diff(depth))) if len(depth) > 1 else 1.0
    jumps = np.r_[False, np.diff(depth) > 3 * step]
    lines, current = [], []
    for xi, yi, cut in zip(x, y, jumps):
        if cut or np.isnan(xi):
            if len(current) > 1:
                lines.append(" ".join(current))
            current = []
            if np.isnan(xi):
                continue
        current.append(f"{xi:.2f},{yi:.1f}")
    if len(current) > 1:
        lines.append(" ".join(current))
    return lines


def track(title: str, vmin, vmax, curves: list[tuple], lo, hi, log=False) -> str:
    grid = "".join(f'<line x1="{x}" x2="{x}" y1="0" y2="600" class="stroke-border" stroke-width=".5"/>' for x in (25, 50, 75))
    lines = ""
    for depth, values, cls, dashed in curves:
        for pts in curve_points(depth, values, lo, hi, vmin, vmax, log):
            dash = ' stroke-dasharray="4 3"' if dashed else ""
            lines += (f'<polyline fill="none" class="{cls}" stroke-width="1.2" vector-effect="non-scaling-stroke"{dash} '
                      f'points="{pts}"/>')
    return (f'<div class="track min-w-[110px] flex-1 overflow-hidden border-r"><div class="track-head border-b px-2 py-1.5">'
            f'<p class="label-mono">{title}</p><p class="font-mono text-[0.6rem] text-muted-foreground">{vmin:g} — {vmax:g}</p></div>'
            f'<svg viewBox="0 0 100 600" preserveAspectRatio="none" class="h-[600px] w-full">{grid}{lines}</svg></div>')


def not_found() -> None:
    with st.container(key="not-found", gap=None):
        html_block('<div class="px-4 text-center"><h1 class="font-mono text-6xl text-primary">404</h1>'
                   '<p class="mt-2 text-muted-foreground">No well at this depth.</p></div>')
        nav_link(PAGES["index"], "Back to field", "lk-primarylg-back")


def page_well() -> None:
    well = find_well(st.query_params.get("id", ""))
    if not well:
        st.set_page_config(page_title="Well not found")
        not_found()
        return
    name = display_name(well)
    st.set_page_config(page_title=f"{name} · Well Log Analyst")
    with st.spinner(f"Reading {name}…"):
        f = well_facts(well, memory_stamp())
        t = well_tracks(well, memory_stamp())

    with st.container(key="well-top", horizontal=True, vertical_alignment="bottom", gap=None):
        with st.container(key="well-title", gap=None, width="content"):
            nav_link(PAGES["index"], "← Field", "lk-back-field")
            sub = (f'<p class="mt-1 text-sm text-muted-foreground">Hugin {format_intervals(f["intervals"])} m MD</p>'
                   if f["intervals"] else "")
            html_block(f'<h1 class="mt-1 font-mono text-4xl">{esc(name)}</h1>{sub}')
        with st.container(key="well-actions", horizontal=True, vertical_alignment="center", gap=None, width="content"):
            if f["status"] in STATUS:
                html_block(badge(f["status"]), width="content")
            nav_link(PAGES["agent"], "Ask the agent", "lk-primary-ask", "arrow-up-right", side="after", query={"well": name})

    blocks = ""
    if f["ng"] is not None:                                     # analyze_well's numbers, same formats as the tool
        results = [("N/G", f"{f['ng']:.3f}"), ("PHIF net sand", f"{f['phif']:.3f}"), ("SW net sand", f"{f['sw']:.3f}"),
                   ("KLOGH arithmetic", f"{f['k_arith']:.0f} mD"), ("KLOGH geometric", f"{f['k_geo']:.0f} mD")]
        cells = "".join(f'<div class="border-r px-4 last:border-r-0"><p class="label-mono">{label}</p>'
                        f'<p class="mt-1 font-mono text-2xl">{value}</p></div>' for label, value in results)
        blocks += (f'<div class="delta-row mt-6 grid border-y py-5" style="grid-template-columns:repeat(5,minmax(0,1fr))">'
                   f'{cells}</div>')
    if f["diff"]:
        cells = ""
        for k in ("vsh", "phif", "sw"):
            d = f["diff"][k]
            if d is None:
                cells += f'<div class="border-r px-4 last:border-r-0"><p class="label-mono">Δ {k.upper()} vs Equinor</p><p class="mt-1 font-mono text-2xl">—</p></div>'
                continue
            tone = "warn" if d > REVIEW_LIMIT else "ok"
            cells += (f'<div class="border-r px-4 last:border-r-0"><p class="label-mono">Δ {k.upper()} vs Equinor</p>'
                      f'<p class="mt-1 font-mono text-2xl text-{tone}">{d:.3f}</p><div class="mt-2 h-1 rounded bg-muted">'
                      f'<div class="h-1 rounded bg-{tone}" style="width:{min(100, d * 500):.1f}%"></div></div></div>')
        blocks += f'<div class="delta-row mt-6 grid grid-cols-3 border-y py-5">{cells}</div>'
    if f["note"]:
        blocks += (f'<div class="mt-6 border-l-2 border-primary/60 bg-muted/50 px-3 py-2"><p class="font-mono text-xs text-primary">'
                   f'<span class="inline-flex items-center gap-2">{icon("activity", 12)}analyze_well</span></p>'
                   f'<p class="font-mono text-sm">{esc(f["note"])}</p></div>')

    lo, hi = t["lo"], t["hi"]
    legend = ('<span class="flex items-center gap-1"><span class="h-0.5 w-5 bg-foreground"></span> Agent</span>'
              '<span class="flex items-center gap-1"><span class="h-0.5 w-5 border-t border-dashed border-primary"></span> Equinor</span>'
              '<span class="flex items-center gap-1"><span class="h-3 w-5 bg-hugin"></span> Hugin</span>') if t["intervals"] else ""
    source = "From load_input · match_depths" if t["intervals"] else "From load_input"
    blocks += (f'<div class="mt-6 flex flex-wrap items-center gap-4 border-b pb-4 text-xs text-muted-foreground">{legend}'
               f'<span class="ml-auto label-mono">{source}</span></div>')

    d, raw = t["depth"], t["raw"]
    tracks = [("GR", 0, 150, [(d, raw.get("GR"), "stroke-curve-gr", False)], False),
              ("RHOB", 1.95, 2.95, [(d, raw.get("RHOB"), "stroke-curve-rho", False)], False),
              ("NPHI", 0, 0.6, [(d, raw.get("NPHI"), "stroke-curve-nphi", False)], False),
              ("RT", 0.2, 200, [(d, raw.get("RT"), "stroke-curve-rt", False)], True)]
    if t["intervals"]:
        h, it = t["hugin_depth"], t["interp"]
        for c, vmax in (("VSH", 1), ("PHIF", 0.35), ("SW", 1)):
            tracks.append((c, 0, vmax, [(h, it.get(c), "stroke-foreground", False),
                                        (h, it.get(f"EQ_{c}"), "stroke-primary", True)], False))
    track_html = "".join(track(title, a, b, [c for c in curves if c[1] is not None], lo, hi, log)
                         for title, a, b, curves, log in tracks)
    band = "".join(f'<div class="pointer-events-none absolute inset-x-0 z-0 bg-hugin" '
                   f'style="top:{46 + (top - lo) / (hi - lo) * 600:.1f}px;height:{(base - top) / (hi - lo) * 600:.1f}px"></div>'
                   for top, base in t["intervals"])
    ticks = "".join(f'<span class="absolute left-1" style="top:{q * 96}%">{round(lo + q * (hi - lo))}</span>'
                    for q in (0, 0.25, 0.5, 0.75, 1))
    blocks += ('<div class="relative mt-6 flex gap-2 overflow-x-auto bg-card">'
               '<div class="w-14 shrink-0 overflow-hidden border-r"><div class="track-head border-b px-2 py-1.5"><p class="label-mono">MD</p>'
               '<p class="font-mono text-[0.6rem] text-muted-foreground">m</p></div>'
               f'<div class="relative h-[600px] font-mono text-[0.6rem] text-muted-foreground">{ticks}</div></div>'
               f'<div class="relative flex min-w-[700px] flex-1 gap-2">{band}{track_html}</div></div>')
    html_block(blocks)


# ── 3. Analysis agent (routes/agent.tsx + chat.py) ───────────────────────────────────────────
def new_thread() -> None:
    s = st.session_state
    s.thread_id = f"well-session-{uuid.uuid4().hex[:8]}"   # one thread per browser session, as in chat.py
    s.messages, s.pending, s.error, s.saved = [], None, None, False


def agent_state():
    s = st.session_state
    if "thread_id" not in s:
        new_thread()
    return s


def run_agent(payload) -> None:
    """Invoke the agent the way chat.py does (version v2, same thread), keeping any pending approval."""
    s = agent_state()
    config = {"configurable": {"thread_id": s.thread_id}}
    try:
        if s.get("agent") is None:
            from agent import build_agent                      # built once per session
            s.agent = build_agent()
        result = s.agent.invoke(payload, config=config, version="v2")
    except Exception as e:                                       # same messages as chat.py
        text = str(e)
        if "413" in text or "rate_limit" in text:
            s.error = ("The model's limit was reached. Type 'new' for a fresh conversation, or wait a minute.\n"
                       f"Details: {text[:300]}")
        else:
            s.error = f"Error: {e}"
        return
    values = result.value if isinstance(result.value, dict) and "messages" in result.value else \
        s.agent.get_state(config).values
    s.messages = values.get("messages", [])
    s.error = None
    if result.interrupts:                                        # the agent paused before writing a file
        s.pending = {"requests": result.interrupts[0].value["action_requests"], "decisions": [], "editing": False}
    else:
        s.pending = None


def on_send() -> None:
    s = agent_state()
    text = (s.get("in-chat") or "").strip()
    if not text:
        return
    if text.lower() == "new":                                   # chat.py: 'new' starts a fresh conversation
        new_thread()
        return
    s.saved, s.queued = False, text


def suggest(name: str) -> None:
    st.session_state["in-chat"] = f"Analyze well {name}"


def decide(kind: str) -> None:
    """Approve, edit or reject the current file write, like ask_approval in chat.py."""
    s = agent_state()
    pending = s.pending
    req = pending["requests"][len(pending["decisions"])]
    args = dict(req["args"])
    key = "content" if "content" in args else "new_string"
    if kind == "edit":
        pending["editing"] = True
        return
    if kind == "reject":
        pending["decisions"].append({"type": "reject", "message": "The user rejected this file. Ask what to change."})
    else:
        text = s.get(f"draft-{s.thread_id}-{len(pending['decisions'])}", args.get(key) or "")
        if pending["editing"] and text != (args.get(key) or ""):
            args[key] = text
            pending["decisions"].append({"type": "edit", "edited_action": {"name": req["name"], "args": args}})
        else:
            pending["decisions"].append({"type": "approve"})
        if req["name"] == "write_file":
            s.saved = True
    pending["editing"] = False
    if len(pending["decisions"]) == len(pending["requests"]):
        s.resume = pending["decisions"]


def tool_step(call: dict, result) -> str:
    shown = {k: (str(v)[:80] + "..." if len(str(v)) > 80 else v) for k, v in call["args"].items() if k != "content"}
    out = ""
    if result is not None:
        text = result.text if hasattr(result, "text") else str(result.content)
        out = f'<p class="mt-1 whitespace-pre-wrap font-mono text-sm">{esc(text[:4000])}</p>'
    return (f'<div class="ml-4 border-l-2 border-primary/60 bg-muted/50 px-3 py-2">'
            f'<p class="font-mono text-xs text-primary"><span class="inline-flex items-center gap-2">{icon("activity", 12)}{esc(call["name"])}</span>'
            f' <span class="text-muted-foreground">{esc(shown)}</span></p>{out}</div>')


def render_messages(messages) -> None:
    results = {m.tool_call_id: m for m in messages if m.type == "tool"}
    for i, m in enumerate(messages):
        if m.type == "human":
            html_block(f'<div class="msg-user ml-auto max-w-[80%] rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground">'
                       f'{esc(m.text)}</div>')
        elif m.type == "ai":
            if m.text.strip():
                with st.container(key=f"msg-agent-{i}", gap=None):
                    st.markdown(m.text)
            steps = "".join(tool_step(c, results.get(c["id"])) for c in m.tool_calls)
            if steps:
                html_block(f'<div class="space-y-3">{steps}</div>')


def page_agent() -> None:
    st.set_page_config(page_title="Agent · Well Log Analyst")
    s = agent_state()
    asked = st.query_params.get("well")
    if asked and s.get("prefilled") != asked:                   # "Ask the agent" from a well page
        s["in-chat"], s.prefilled = f"Analyze well {asked}", asked

    html_block(f'<div class="mb-6 border-b pb-5">{page_title("Interpretation", "02", "Analysis agent")}</div>')
    with st.container(key="agent-grid", gap=None):
        with st.container(key="chat-card", gap=None):
            html_block('<div class="flex items-center justify-between border-b px-4 py-3">'
                       f'<p class="flex items-center gap-2 text-xs font-medium">{icon("activity", 16, "text-primary")}Petrophysical analysis</p>'
                       f'<span class="label-mono">{esc(s.thread_id)}</span></div>')
            with st.container(key="chat-scroll", height=400, gap=None, autoscroll=True):
                queued, resume = s.pop("queued", None), s.pop("resume", None)
                if not s.messages and not queued and not s.error:
                    with st.container(key="chat-empty", gap=None):
                        html_block(f'<div class="flex flex-col items-center text-center">{icon("bot", 40, "mb-5 text-primary")}'
                                   '<h2 class="text-xl font-medium">Volve interpretation workspace</h2>'
                                   '<p class="mt-2 text-xs text-muted-foreground">Hugin formation · Equinor reference</p></div>')
                        with st.container(key="chat-sugg", horizontal=True, horizontal_alignment="center", gap=None):
                            for name in ("F-15 D", "F-1 C"):
                                k = f"bt-outline-sugg-{name.replace(' ', '')}"
                                st.button(name, key=k, on_click=suggest, args=(name,))
                                widget_icon(k, "arrow-up", 16, "after", rotate=45)
                render_messages(s.messages)
                if queued:
                    html_block(f'<div class="msg-user ml-auto max-w-[80%] rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground">{esc(queued)}</div>')
                if s.error:
                    html_block(f'<div class="max-w-[85%] whitespace-pre-wrap rounded-md border-l-2 border-destructive bg-accent px-3 py-2 text-sm">{esc(s.error)}</div>')
                if queued or resume:
                    from langgraph.types import Command
                    with st.spinner("Working…"):
                        run_agent({"messages": [{"role": "user", "content": queued}]} if queued else
                                  Command(resume={"decisions": resume}))
                    st.rerun()
            with st.form("chat-form", clear_on_submit=True, border=False):
                with st.container(key="chat-row", horizontal=True, vertical_alignment="center", gap=None):
                    st.text_input("Message the agent", key="in-chat", placeholder="Ask about a well…", label_visibility="collapsed")
                    st.form_submit_button("Send message", key="bt-send", on_click=on_send)
                    widget_icon("bt-send", "arrow-up", 16)

        with st.container(key="approval", gap=None):
            html_block(f'<p class="flex items-center gap-2 text-sm font-semibold">{icon("file-check", 16, "text-primary")}Report approval</p>'
                       '<p class="label-mono mt-2">Human review</p>')
            pending = s.pending
            if pending and len(pending["decisions"]) < len(pending["requests"]):
                n = len(pending["decisions"])
                req = pending["requests"][n]
                args = req["args"]
                body = args.get("content") if "content" in args else args.get("new_string")
                html_block(f'<p class="mt-3 font-mono text-[11px] text-muted-foreground">{esc(req["name"])} · '
                           f'{esc(args.get("file_path") or args.get("path") or "")}</p>')
                st.text_area("Report draft", value=body or "", key=f"draft-{s.thread_id}-{n}", height=360,
                             label_visibility="collapsed", disabled=not pending["editing"])
                with st.container(key="approval-buttons", horizontal=True, gap=None):
                    st.button("Approve & save", key="bt-primary-approve", on_click=decide, args=("approve",))
                    widget_icon("bt-primary-approve", "check", 12)
                    st.button("Edit", key="bt-outline-edit", on_click=decide, args=("edit",), disabled=pending["editing"])
                    widget_icon("bt-outline-edit", "pencil", 12)
                    st.button("Reject", key="bt-reject", on_click=decide, args=("reject",))
                    widget_icon("bt-reject", "x", 12)
            elif s.saved:
                with st.container(key="saved", horizontal=True, vertical_alignment="center", gap=None):
                    html_block('<p class="text-sm text-ok">Report saved.</p>', width="content")
                    nav_link(PAGES["reports"], "Open reports", "lk-inline-reports")
            else:
                html_block('<p class="mt-3 text-sm text-muted-foreground">No pending report.</p>')


# ── 4. Reports (routes/reports.tsx), from phase1_training/reports/ ─────────────────────────────
def page_reports() -> None:
    st.set_page_config(page_title="Reports · Well Log Analyst")
    files = report_files()
    html_block(f'<header class="mb-6 border-b pb-5">{page_title("Evaluation", "03", "Approved reports")}</header>')
    names = [f.name for f in files]
    if st.session_state.get("report") not in names:
        st.session_state.report = names[0] if names else None

    def pick(name):
        st.session_state.report = name

    with st.container(key="reports-grid", gap=None):
        with st.container(key="reports-list", gap=None):
            html_block(f'<p class="label-mono mb-2">{len(files)} approved reports</p>')
            for i, f in enumerate(files):
                state = "on" if f.name == st.session_state.report else "off"
                k = f"bt-report{state}-{i}"
                day = datetime.fromtimestamp(f.stat().st_mtime).date().isoformat()
                st.button(display_name(f.stem.removesuffix("_report")), key=k, on_click=pick, args=(f.name,), width="stretch")
                widget_icon(k, "file-text", 16)
                st.session_state["_css"].append(f".st-key-{k} button p::after{{content:'{day}'}}")
        if st.session_state.report:
            f = REPORTS_DIR / st.session_state.report
            body = f.read_text(encoding="utf-8")
            day = datetime.fromtimestamp(f.stat().st_mtime).date().isoformat()
            with st.container(key="report-article", gap=None):
                with st.container(key="report-bar", horizontal=True, vertical_alignment="center", gap=None):
                    html_block(f'<p class="label-mono">{day}</p>')
                    st.download_button("Download .md", body, file_name=f.name, mime="text/markdown", key="bt-outline-download",
                                       on_click="ignore")
                    widget_icon("bt-outline-download", "download", 16)
                html_block(f'<div class="whitespace-pre-wrap font-mono text-xs leading-7">{esc(body)}</div>')


# ── 5. Curve dictionary (routes/dictionary.tsx), from config.INPUT_CURVES ─────────────────────
def page_dictionary() -> None:
    st.set_page_config(page_title="Curve dictionary · Well Log Analyst")
    added = st.session_state.setdefault("added_mnemonics", {})  # this session only, like the Lovable page

    def add(curve):
        name = (st.session_state.get(f"in-dict-{curve}") or "").strip().upper()
        names = INPUT_CURVES[curve] + added.get(curve, [])
        if name and name not in names:
            added.setdefault(curve, []).append(name)

    html_block('<div class="border-b pb-5">' + page_title("Reference", "04", "Curve dictionary",
               '<p class="mt-2 text-xs text-muted-foreground">Volve dataset · Log curve mnemonics</p>') + '</div>')
    with st.container(key="dict-list", gap=None):
        for curve, names in INPUT_CURVES.items():
            with st.container(key=f"dict-row-{curve}", gap=None):
                html_block(f'<div class="flex items-start gap-3">{icon("waves", 16, "mt-1 text-muted-foreground")}<div>'
                           f'<h2 class="font-mono text-xl text-primary">{curve}</h2><span class="label-mono">{CURVE_LABELS.get(curve, "")}</span></div></div>')
                with st.container(key=f"dict-right-{curve}", gap=None):
                    chips = "".join(f'<span class="border-b px-1 py-1 font-mono text-xs {"border-primary/60" if i == 0 else ""}">{esc(n)}</span>'
                                    for i, n in enumerate(names + added.get(curve, [])))
                    html_block(f'<div class="flex flex-wrap gap-2">{chips}</div>')
                    with st.form(f"dict-form-{curve}", clear_on_submit=True, border=False):
                        with st.container(key=f"dict-add-{curve}", horizontal=True, vertical_alignment="center", gap=None):
                            st.text_input(f"Add mnemonic for {curve}", key=f"in-dict-{curve}", placeholder="Add mnemonic",
                                          label_visibility="collapsed")
                            k = f"bt-add-{curve}"
                            st.form_submit_button(f"Add {curve} mnemonic", key=k, on_click=add, args=(curve,))
                            widget_icon(k, "plus", 16)


# ── 6. Company sign in (routes/auth.tsx): presentation only, nothing is sent or stored ─────────
def page_auth() -> None:
    st.set_page_config(page_title="Company Sign In · Well Log Analyst")
    html_block(
        '<div class="auth-bg">'
        + cover_image("volve-platform.jpg", "Illustrative North Sea offshore platform", "absolute inset-0 h-full w-full object-cover object-right")
        + '<div class="auth-shade absolute inset-0"></div></div>')
    nav_link(PAGES["index"], "Workspace preview", "lk-cover-back", "arrow-left")
    html_block(
            '<div class="auth-scene">'
            '<header class="auth-head relative z-1 flex items-center justify-between gap-4 px-6 py-7 text-cover-foreground sm:px-10">'
            f'<a href="{url("./")}" class="flex items-center gap-3">{icon("activity", 24, "text-heritage")}'
            '<span class="font-display text-2xl">Well Log Analyst</span></a></header>'
            '<main class="auth-main relative z-1 flex flex-1 items-center px-6 py-10 sm:px-10 lg:px-20">'
            '<section class="w-full max-w-[450px] bg-background px-6 py-9 sm:px-10">'
            f'<div class="flex items-center justify-between"><p class="label-mono text-heritage">Company access</p>{theme_toggle()}</div>'
            '<div class="my-6 h-px w-12 bg-heritage"></div><h1 class="font-display text-4xl">Welcome back.</h1>'
            '<p class="mt-3 text-sm text-muted-foreground">Volve field · Interpretation workspace</p>'
            '<div class="wl-auth-form mt-9 space-y-5">'
            '<div><label for="company-username" class="text-xs font-medium">Company username</label>'
            f'<div class="mt-2 flex items-center gap-3 border-b py-3 auth-field">{icon("building-2", 16, "shrink-0 text-muted-foreground")}'
            '<input id="company-username" name="username" autocomplete="username" required placeholder="Your company username" '
            'class="min-w-0 flex-1 bg-transparent text-sm"></div></div>'
            '<div><label for="company-password" class="text-xs font-medium">Password</label>'
            f'<div class="mt-2 flex items-center gap-3 border-b py-2 auth-field">{icon("lock-keyhole", 16, "shrink-0 text-muted-foreground")}'
            '<input id="company-password" name="password" type="password" autocomplete="current-password" required '
            'placeholder="Enter your password" class="min-w-0 flex-1 bg-transparent text-sm">'
            '<button type="button" class="wl-eye btn-ghost size-8" aria-label="Show password" title="Show password">'
            f'{icon("eye", 16, "i-eye")}{icon("eye-off", 16, "i-eye-off")}</button></div></div>'
            f'<button type="button" class="wl-signin btn-primary mt-3 h-11 w-full justify-between">Sign in {icon("arrow-right", 16)}</button>'
            '<p role="status" class="wl-auth-message border-l-2 border-warn pl-3 text-xs leading-6 text-muted-foreground" style="display:none"></p></div>'
            '<p class="mt-7 border-t pt-5 text-[11px] leading-5 text-muted-foreground">Preview only · Account access and profile storage pending integration.</p>'
            '</section><div class="ml-auto hidden max-w-[360px] self-end pb-6 pl-10 text-cover-foreground xl:block">'
            '<p class="text-xs text-heritage">NORTH SEA / NORWAY</p><p class="mt-4 font-display text-4xl leading-tight">A deeper view.<br>A clearer interpretation.</p>'
            '<p class="mt-5 text-xs text-cover-foreground/70">Volve · Hugin formation</p></div></main>'
            '<footer class="relative z-1 flex justify-between gap-4 px-6 py-5 text-[10px] text-cover-foreground/70 sm:px-10">'
            '<span>WELL LOG ANALYST / COMPANY WORKSPACE</span><span>Illustrative platform image</span></footer></div>')


# ── App ─────────────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Well Log Analyst", page_icon=str(FAVICON) if FAVICON.exists() else None,
                   layout="wide", initial_sidebar_state="expanded")
st.session_state["_css"] = []

PAGES = {
    "index": st.Page(page_index, title="Field overview", url_path="", default=True),
    "well": st.Page(page_well, title="Well detail", url_path="wells"),
    "agent": st.Page(page_agent, title="Analysis agent", url_path="agent"),
    "reports": st.Page(page_reports, title="Reports", url_path="reports"),
    "dictionary": st.Page(page_dictionary, title="Curve dictionary", url_path="dictionary"),
    "auth": st.Page(page_auth, title="Company Sign In", url_path="auth"),
}
page = st.navigation(list(PAGES.values()), position="hidden")
current = next(k for k, p in PAGES.items() if p.url_path == page.url_path)

st.markdown(f"<style>{CSS_FILE.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
with st.container(key="wl-js"):
    st.html(PAGE_SCRIPT, unsafe_allow_javascript=True)

if current == "auth":
    html_block('<span class="wl-auth"></span>')
    page.run()
else:
    sidebar(current)
    header(current)
    with st.container(key="wl-content", gap=None):
        page.run()
    footer()

st.markdown(f"<style>{''.join(st.session_state['_css'])}</style>", unsafe_allow_html=True)
