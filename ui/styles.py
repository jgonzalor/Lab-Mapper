"""Shared visual system for Go Mapper Streamlit pages.

This module intentionally contains presentation helpers only. It does not
transform data, alter filters, or change export/KMZ logic.
"""
from __future__ import annotations

from html import escape
from typing import Iterable, Mapping

import streamlit as st



def apply_theme() -> None:
    """Inject the Go Mapper visual theme for the current Streamlit render."""
    st.markdown(
        """
<style>
:root {
  --gm-bg: #0b1120;
  --gm-bg-soft: #111827;
  --gm-surface: #ffffff;
  --gm-surface-muted: #f8fafc;
  --gm-border: #dbe4ef;
  --gm-border-strong: #b8c4d6;
  --gm-text: #0f172a;
  --gm-muted: #64748b;
  --gm-primary: #0f766e;
  --gm-primary-dark: #115e59;
  --gm-accent: #2563eb;
  --gm-warn: #b45309;
  --gm-danger: #b91c1c;
  --gm-shadow: 0 18px 45px rgba(15, 23, 42, 0.10);
  --gm-radius: 18px;
}

#MainMenu, header, footer {visibility: hidden;}
.stDeployButton, div[data-testid="stStatusWidget"] {display:none!important;}

.stApp {
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, .11), transparent 34rem),
    radial-gradient(circle at top right, rgba(15, 118, 110, .12), transparent 32rem),
    linear-gradient(180deg, #f8fafc 0%, #eef3f8 100%);
  color: var(--gm-text);
}

.block-container {
  max-width: 1520px !important;
  padding-top: 1.3rem !important;
  padding-bottom: 3rem !important;
}

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #07111f 0%, #0f172a 55%, #111827 100%);
  border-right: 1px solid rgba(148, 163, 184, .25);
}
[data-testid="stSidebar"] * {color: #e5edf7 !important;}
[data-testid="stSidebar"] .stButton > button {
  width: 100%;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, .32);
  background: rgba(15, 23, 42, .45);
}
[data-testid="stSidebar"] hr {border-color: rgba(148, 163, 184, .25);}

h1, h2, h3 {letter-spacing: -.025em;}
h1 {font-weight: 800 !important;}
h2, h3 {font-weight: 750 !important;}

.gm-hero {
  position: relative;
  overflow: hidden;
  padding: 2rem 2.2rem;
  border-radius: 26px;
  background:
    linear-gradient(135deg, rgba(15, 23, 42, .98), rgba(15, 118, 110, .88)),
    radial-gradient(circle at 88% 12%, rgba(59, 130, 246, .55), transparent 20rem);
  color: #f8fafc;
  box-shadow: var(--gm-shadow);
  border: 1px solid rgba(255, 255, 255, .12);
  margin-bottom: 1.2rem;
}
.gm-hero:after {
  content: "";
  position: absolute;
  right: -5rem;
  top: -5rem;
  width: 18rem;
  height: 18rem;
  border-radius: 999px;
  background: rgba(255,255,255,.08);
}
.gm-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: .45rem;
  padding: .28rem .7rem;
  border: 1px solid rgba(255,255,255,.22);
  border-radius: 999px;
  background: rgba(255,255,255,.08);
  color: #ccfbf1;
  font-size: .78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .08em;
}
.gm-hero h1 {margin: .8rem 0 .45rem; color: #fff; font-size: clamp(2rem, 4vw, 3.65rem);}
.gm-hero p {max-width: 880px; color: #dbeafe; font-size: 1.04rem; line-height: 1.65; margin: 0;}
.gm-hero-meta {display:flex; flex-wrap:wrap; gap:.65rem; margin-top:1.1rem;}
.gm-pill {
  display:inline-flex; align-items:center; gap:.4rem; padding:.45rem .75rem;
  border-radius: 999px; background: rgba(255,255,255,.10); color:#ecfeff;
  border: 1px solid rgba(255,255,255,.14); font-size:.86rem; font-weight:650;
}

.gm-panel, .gm-card, .gm-kpi-card, .gm-section {
  background: rgba(255, 255, 255, .92);
  border: 1px solid var(--gm-border);
  border-radius: var(--gm-radius);
  box-shadow: 0 10px 30px rgba(15, 23, 42, .065);
}
.gm-panel {padding: 1.1rem 1.2rem; margin: .75rem 0 1rem;}
.gm-card {padding: 1.15rem; min-height: 190px; transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;}
.gm-card:hover {transform: translateY(-2px); box-shadow: var(--gm-shadow); border-color: rgba(15, 118, 110, .35);}
.gm-card-title {font-size: 1.05rem; font-weight: 800; margin-bottom: .35rem; color: #0f172a;}
.gm-card-desc {font-size: .92rem; color: var(--gm-muted); line-height: 1.55; min-height: 4.1rem;}
.gm-card-tag {display:inline-flex; margin-bottom:.65rem; padding:.2rem .55rem; border-radius:999px; background:#e0f2fe; color:#075985; font-size:.75rem; font-weight:800;}

.gm-kpi-card {padding: 1rem; border-left: 4px solid var(--gm-primary);}
.gm-kpi-label {font-size:.78rem; text-transform:uppercase; letter-spacing:.075em; color:var(--gm-muted); font-weight:800;}
.gm-kpi-value {font-size:1.65rem; color:var(--gm-text); font-weight:850; margin-top:.25rem;}
.gm-kpi-help {font-size:.82rem; color:var(--gm-muted); margin-top:.2rem;}

.gm-section-title {margin:1.35rem 0 .5rem; display:flex; align-items:center; gap:.55rem;}
.gm-section-title h2, .gm-section-title h3 {margin:0;}
.gm-section-subtitle {color:var(--gm-muted); margin-top:-.2rem; margin-bottom:.8rem;}

.gm-sidebar-brand {
  border: 1px solid rgba(148, 163, 184, .24);
  background: linear-gradient(135deg, rgba(20, 184, 166, .16), rgba(37, 99, 235, .12));
  border-radius: 18px;
  padding: 1rem;
  margin-bottom: .9rem;
}
.gm-sidebar-brand-title {font-weight:850; font-size:1.05rem; color:#f8fafc!important;}
.gm-sidebar-brand-sub {font-size:.78rem; color:#cbd5e1!important; margin-top:.18rem;}
.gm-sidebar-user {
  border-radius: 14px;
  padding: .75rem .85rem;
  background: rgba(15, 23, 42, .48);
  border: 1px solid rgba(148, 163, 184, .2);
  margin-bottom: .75rem;
}
.gm-nav-group {font-size:.72rem; color:#94a3b8!important; text-transform:uppercase; letter-spacing:.1em; font-weight:850; margin:.95rem 0 .35rem;}

.stButton > button, .stDownloadButton > button, [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"] {
  border-radius: 12px !important;
  font-weight: 750 !important;
}
.stButton > button[kind="primary"], [data-testid="stBaseButton-primary"] {
  background: linear-gradient(135deg, var(--gm-primary), var(--gm-accent)) !important;
  border: 0 !important;
}

[data-testid="stMetric"] {
  background: rgba(255,255,255,.9);
  border: 1px solid var(--gm-border);
  border-radius: 16px;
  padding: .9rem 1rem;
  box-shadow: 0 8px 22px rgba(15,23,42,.055);
}
[data-testid="stDataFrame"] {border-radius: 16px; overflow: hidden; border: 1px solid var(--gm-border);}

.gm-muted {color: var(--gm-muted);}
.gm-divider {height:1px; background:linear-gradient(90deg, transparent, var(--gm-border), transparent); margin:1.2rem 0;}
</style>
""",
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = "", eyebrow: str = "GO MAPPER", badges: Iterable[str] | None = None) -> None:
    """Render a consistent premium header for a page."""
    badge_html = "".join(f'<span class="gm-pill">{escape(str(b))}</span>' for b in (badges or []))
    subtitle_html = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    st.markdown(
        f"""
<div class="gm-hero">
  <span class="gm-eyebrow">{escape(eyebrow)}</span>
  <h1>{escape(title)}</h1>
  {subtitle_html}
  <div class="gm-hero-meta">{badge_html}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def section_title(title: str, subtitle: str = "", icon: str = "") -> None:
    icon_html = f"<span>{escape(icon)}</span>" if icon else ""
    st.markdown(
        f"""
<div class="gm-section-title">{icon_html}<h3>{escape(title)}</h3></div>
{f'<div class="gm-section-subtitle">{escape(subtitle)}</div>' if subtitle else ''}
""",
        unsafe_allow_html=True,
    )


def module_card(title: str, description: str, tag: str = "Módulo") -> None:
    st.markdown(
        f"""
<div class="gm-card">
  <div class="gm-card-tag">{escape(tag)}</div>
  <div class="gm-card-title">{escape(title)}</div>
  <div class="gm-card-desc">{escape(description)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def kpi_row(items: Iterable[Mapping[str, object]], columns: int | None = None) -> None:
    data = list(items)
    if not data:
        return
    cols = st.columns(columns or len(data))
    for col, item in zip(cols, data):
        with col:
            st.markdown(
                f"""
<div class="gm-kpi-card">
  <div class="gm-kpi-label">{escape(str(item.get('label', '')))}</div>
  <div class="gm-kpi-value">{escape(str(item.get('value', '')))}</div>
  <div class="gm-kpi-help">{escape(str(item.get('help', '')))}</div>
</div>
""",
                unsafe_allow_html=True,
            )


def info_panel(title: str, body: str) -> None:
    st.markdown(
        f"""
<div class="gm-panel">
  <strong>{escape(title)}</strong><br>
  <span class="gm-muted">{escape(body)}</span>
</div>
""",
        unsafe_allow_html=True,
    )
