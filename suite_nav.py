# suite_nav.py — Menú lateral unificado para Go Mapper Suite
import os
import sys
import streamlit as st
from ui.styles import inject_global_styles

ROOT = os.path.dirname(__file__)


def _page_exists(script_relpath: str) -> bool:
    """
    Verifica si una página existe en la multi-page app de Streamlit.

    - Primero intenta con st.get_pages("app.py") (Streamlit 1.35+).
    - Si algo falla, hace fallback al sistema de archivos.
    """
    # 1) Intento con la API oficial
    try:
        pages = st.get_pages("app.py")
        for p in pages.values():
            if p.get("script_path") == script_relpath:
                return True
        return False
    except Exception:
        # 2) Fallback: mirar si el archivo existe
        script_fs = os.path.join(ROOT, script_relpath)
        return os.path.isfile(script_fs)


def _logout():
    """Cierra sesión en toda la suite."""
    st.session_state["logged_in"] = False
    st.session_state["suite_auth"] = False
    st.session_state["user_role"] = None
    st.session_state["user_name"] = None
    st.session_state["username"] = ""
    st.session_state["remember"] = False
    st.experimental_rerun()


def _active_script_name() -> str:
    main_file = getattr(sys.modules.get("__main__"), "__file__", "")
    return os.path.basename(str(main_file))


def render_suite_sidebar():
    """Dibuja el menú lateral con navegación + logout."""
    inject_global_styles()
    active_name = _active_script_name()
    with st.sidebar:
        st.markdown(
            """
            <div class="gm-sidebar-brand">
              <div class="gm-sidebar-brand-title">🗺️ Go Mapper Suite</div>
              <div class="gm-sidebar-brand-sub">CDR · Análisis · KMZ · Pericial</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Info de usuario
        user = st.session_state.get("username") or st.session_state.get("user_name")
        role = st.session_state.get("user_role")

        if user:
            if role == "owner":
                rol_txt = "Propietario"
            elif role == "user":
                rol_txt = "Usuario"
            else:
                rol_txt = "Sesión"
            st.markdown(
                f"<div class='gm-sidebar-user'><div><strong>{user}</strong><br><span>{rol_txt}</span></div><span>●</span></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown("<div class='gm-sidebar-user'><div><strong>Sesión</strong><br><span>Activa</span></div><span>●</span></div>", unsafe_allow_html=True)

        if st.button("Cerrar sesión", key="logout_sidebar"):
            _logout()

        st.markdown("---")
        st.markdown("<div class='gm-nav-group'>Inicio</div>", unsafe_allow_html=True)
        if active_name == "app.py":
            st.markdown("<div class='gm-active-page'>🏠 Inicio</div>", unsafe_allow_html=True)
        else:
            try:
                st.page_link("app.py", label="🏠 Inicio")
            except Exception:
                pass

        groups = [
            (
                "Preparación",
                [
                    ("pages/app_limpieza_excel.py", "🧹 Limpieza"),
                    ("pages/app armonizador a telcel.py", "🔁 Armonizador"),
                ],
            ),
            (
                "Análisis",
                [
                    ("pages/app_consulta_visual.py", "📊 Consulta visual"),
                    ("pages/app_linea_tiempo.py", "📅 Línea de tiempo"),
                    ("pages/app_link_analysis.py", "🔗 Análisis de vínculos"),
                    ("pages/app_oraculo_cdr.py", "🧠 ORÁCULO CDR"),
                    ("pages/app_grafo_inteligente.py", "🗺️ Sentinel Mapa Investigativo"),
                ],
            ),
            (
                "Geográfico",
                [
                    ("pages/app_mapper_azimuth.py", "🛰️ KMZ Azimut"),
                    ("pages/app_sentinel_mapper_kmz_pro.py", "🌎 KMZ Pro"),
                ],
            ),
            (
                "Reportes",
                [
                    ("pages/app_informe_cdr.py", "📑 Informe CDR"),
                    ("pages/app_lex_cdr.py", "📚 LEX CDR"),
                ],
            ),
            (
                "Sistema",
                [
                    ("pages/app_maestro_ubicaciones.py", "📍 Maestro de ubicaciones"),
                ],
            ),
        ]

        for group_name, links in groups:
            visible = [(script, label) for script, label in links if _page_exists(script)]
            if not visible:
                continue
            st.markdown(f"<div class='gm-nav-group'>{group_name}</div>", unsafe_allow_html=True)
            for script, label in visible:
                if os.path.basename(script) == active_name:
                    st.markdown(f"<div class='gm-active-page'>{label}</div>", unsafe_allow_html=True)
                    continue
                try:
                    st.page_link(script, label=label)
                except Exception:
                    pass
