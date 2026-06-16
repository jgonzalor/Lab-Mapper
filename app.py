# app.py — Portada + lanzador Go Mapper Suite (con guardian unificado)

import os
import streamlit as st
from suite_nav import render_suite_sidebar      # Menú lateral unificado
from guardian import login_guard                # Guardián central de acceso

# =========================
#   CONFIG UI BÁSICA
# =========================
st.set_page_config(
    page_title="Go Mapper Suite",
    page_icon="🗺️",
    layout="wide",
    menu_items={"Get Help": None, "Report a bug": None, "About": None},
)

# Oculta UI sobrante de Streamlit
st.markdown(
    """
<style>
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
#   UTILIDADES DE PÁGINAS
# =========================
ROOT = os.path.dirname(__file__)
PAGES_DIR = os.path.join(ROOT, "pages")


def discover_pages():
    """Escanea /pages y devuelve lista [(label, relpath)] de archivos .py existentes."""
    items = []
    if not os.path.isdir(PAGES_DIR):
        return items
    for fname in sorted(os.listdir(PAGES_DIR)):
        if not fname.endswith(".py"):
            continue
        abs_path = os.path.join(PAGES_DIR, fname)
        if not os.path.isfile(abs_path):
            continue
        relpath = f"pages/{fname}"  # lo que espera st.page_link
        label = fname.replace("_", " ").replace(".py", "")
        items.append((label, relpath))
    return items


# =========================
#   LANZADOR (DASHBOARD)
# =========================
def launcher():
    """Portada tipo dashboard con TODOS los módulos principales."""
    username = (
        st.session_state.get("username")
        or st.session_state.get("user_name")
        or ""
    )
    if username:
        saludo = (
            f"Acceso concedido. Bienvenido, {username}. "
            f"Go Mapper Suite. Gonzalo Romero"
        )
    else:
        saludo = "Acceso concedido a Go Mapper Suite."
    st.success(saludo)

    # Título principal
    st.markdown("# Go Mapper Suite")
    st.caption("Portada & lanzador de módulos")

    # Descubrimos todas las páginas disponibles en /pages
    pages = discover_pages()
    page_by_fname = {os.path.basename(rel): rel for (_label, rel) in pages}

    # Módulos principales (tarjetas)
    modules = [
        {
            "fname": "app_limpieza_excel.py",
            "title": "🧹 Limpieza",
            "desc": "Convierte CDR crudos en un Excel limpio con geocodificación, estadísticos y log completo.",
            "button": "Abrir Limpieza",
        },
        {
            "fname": "app_mapper_azimuth.py",
            "title": "🛰️ KMZ Azimut",
            "desc": "Genera KMZ con sectores de cobertura, azimuth, brújula/overlay y animaciones por día.",
            "button": "Abrir KMZ Azimut",
        },
        {
            "fname": "app_sentinel_mapper_kmz_pro.py",
            "title": "🌎 Sentinel Mapper KMZ Pro",
            "desc": "Genera KMZ avanzado con antenas, eventos, cobertura, azimuth, brújula, rutas cronológicas y popups profesionales.",
            "button": "Abrir KMZ Pro",
        },
        {
            "fname": "app_linea_tiempo.py",
            "title": "📅 Línea de tiempo",
            "desc": "Construye cronologías por eventos con vistas ligera y detallada, listas para imprimir o exportar.",
            "button": "Abrir Línea de tiempo",
        },
        {
            "fname": "app_link_analysis.py",
            "title": "🔗 Análisis de vínculos",
            "desc": "Grafo de relaciones entre números, con métricas de red y exportables para dictamen.",
            "button": "Abrir Análisis de vínculos",
        },
        {
            "fname": "app armonizador a telcel.py",
            "title": "🔁 Armonizador",
            "desc": "Normaliza CDRs de diversas compañías al esquema Telcel de 11 columnas para trabajar todo unificado.",
            "button": "Abrir Armonizador",
        },
        {
            "fname": "app_consulta_visual.py",
            "title": "📊 Consulta visual",
            "desc": "Explora y filtra CDR ya procesados con tablas, vistas gráficas y descargas rápidas para análisis.",
            "button": "Abrir Consulta visual",
        },
        {
            "fname": "app_maestro_ubicaciones.py",
            "title": "📍 Maestro de ubicaciones",
            "desc": "Administra el catálogo maestro de antenas y direcciones (PlusRepo / maestro_ubicaciones.sqlite).",
            "button": "Abrir Maestro de ubicaciones",
        },

        # ====== NUEVOS MÓDULOS ======
        {
            "fname": "app_oraculo_cdr.py",
            "title": "🧠 ORÁCULO CDR",
            "desc": "Consulta inteligente sobre CDR limpia: pregunta → intent → evidencia (filas soporte) + exportables.",
            "button": "Abrir ORÁCULO CDR",
        },
        {
            "fname": "app_grafo_inteligente.py",
            "title": "🕸️ Grafo Inteligente",
            "desc": "Control de gráficos: cargar/editar nodos y aristas, export JSON/Excel y render visual (si hay pyvis).",
            "button": "Abrir Grafo Inteligente",
        },
        {
            "fname": "app_lex_cdr.py",
            "title": "📚 LEX CDR",
            "desc": "Manual/FAQ legal CDR: soporte metodológico + fundamento legal + redacción sugerida lista para dictamen.",
            "button": "Abrir LEX CDR",
        },
    ]

    # Tarjetas en 4 columnas (se acomodan en varias filas)
    cols = st.columns(4)
    for i, mod in enumerate(modules):
        col = cols[i % 4]
        with col:
            st.markdown(f"### {mod['title']}")
            st.write(mod["desc"])
            rel = page_by_fname.get(mod["fname"])
            if rel:
                st.page_link(rel, label=f"➡️ {mod['button']}")
            else:
                st.warning("Módulo no encontrado en /pages.", icon="⚠️")

    # Sugerencias de uso
    st.markdown("---")
    st.markdown("#### Sugerencias de uso para rendimiento")
    st.markdown(
        """
        - Ejecuta **Limpieza** primero en modo **Solo caché/PlusRepo**.
        - Si faltan direcciones, corre una segunda pasada en **Completo** con un límite (200–300).
        - Divide lotes grandes en tandas más pequeñas para evitar errores 503.
        """
    )


# =========================
#   FLUJO PRINCIPAL
# =========================

# 1) Guardián central (misma interfaz que en el resto de la suite)
login_guard("Portada / Lanzador de módulos")

# 2) Si pasó el guardián, ya está logueado → sidebar + dashboard
render_suite_sidebar()
launcher()
