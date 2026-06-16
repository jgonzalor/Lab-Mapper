# app.py — Portada + lanzador Go Mapper Suite (con guardian unificado)

import os
import streamlit as st
from suite_nav import render_suite_sidebar      # Menú lateral unificado
from guardian import login_guard                # Guardián central de acceso
from ui.styles import apply_theme, info_panel, kpi_row, module_card, page_header, section_title

# =========================
#   CONFIG UI BÁSICA
# =========================
st.set_page_config(
    page_title="Go Mapper Suite",
    page_icon="🗺️",
    layout="wide",
    menu_items={"Get Help": None, "Report a bug": None, "About": None},
)

# Tema visual profesional compartido
apply_theme()

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
    saludo = f"Sesión activa: {username}" if username else "Sesión activa"

    page_header(
        "Go Mapper Suite",
        "Plataforma operativa para limpieza, homologación, análisis pericial, mapas y productos KMZ/KML de CDR.",
        eyebrow="INTELIGENCIA · CDR · GEOANÁLISIS",
        badges=[saludo, "Laboratorio seguro", "Suite multipágina"],
    )

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
            "tag": "Preparación",
        },
        {
            "fname": "app_mapper_azimuth.py",
            "title": "🛰️ KMZ Azimut",
            "desc": "Genera KMZ con sectores de cobertura, azimuth, brújula/overlay y animaciones por día.",
            "button": "Abrir KMZ Azimut",
            "tag": "Geográfico",
        },
        {
            "fname": "app_sentinel_mapper_kmz_pro.py",
            "title": "🌎 Sentinel Mapper KMZ Pro",
            "desc": "Genera KMZ avanzado con antenas, eventos, cobertura, azimuth, brújula, rutas cronológicas y popups profesionales.",
            "button": "Abrir KMZ Pro",
            "tag": "Geográfico Pro",
        },
        {
            "fname": "app_linea_tiempo.py",
            "title": "📅 Línea de tiempo",
            "desc": "Construye cronologías por eventos con vistas ligera y detallada, listas para imprimir o exportar.",
            "button": "Abrir Línea de tiempo",
            "tag": "Análisis",
        },
        {
            "fname": "app_link_analysis.py",
            "title": "🔗 Análisis de vínculos",
            "desc": "Grafo de relaciones entre números, con métricas de red y exportables para dictamen.",
            "button": "Abrir Análisis de vínculos",
            "tag": "Redes",
        },
        {
            "fname": "app armonizador a telcel.py",
            "title": "🔁 Armonizador",
            "desc": "Normaliza CDRs de diversas compañías al esquema Telcel de 11 columnas para trabajar todo unificado.",
            "button": "Abrir Armonizador",
            "tag": "Homologación",
        },
        {
            "fname": "app_consulta_visual.py",
            "title": "📊 Consulta visual",
            "desc": "Explora y filtra CDR ya procesados con tablas, vistas gráficas y descargas rápidas para análisis.",
            "button": "Abrir Consulta visual",
            "tag": "Exploración",
        },
        {
            "fname": "app_maestro_ubicaciones.py",
            "title": "📍 Maestro de ubicaciones",
            "desc": "Administra el catálogo maestro de antenas y direcciones (PlusRepo / maestro_ubicaciones.sqlite).",
            "button": "Abrir Maestro de ubicaciones",
            "tag": "Catálogo",
        },

        # ====== NUEVOS MÓDULOS ======
        {
            "fname": "app_oraculo_cdr.py",
            "title": "🧠 ORÁCULO CDR",
            "desc": "Consulta inteligente sobre CDR limpia: pregunta → intent → evidencia (filas soporte) + exportables.",
            "button": "Abrir ORÁCULO CDR",
            "tag": "Consulta IA",
        },
        {
            "fname": "app_grafo_inteligente.py",
            "title": "🕸️ Grafo Inteligente",
            "desc": "Control de gráficos: cargar/editar nodos y aristas, export JSON/Excel y render visual (si hay pyvis).",
            "button": "Abrir Grafo Inteligente",
            "tag": "Grafo",
        },
        {
            "fname": "app_lex_cdr.py",
            "title": "📚 LEX CDR",
            "desc": "Manual/FAQ legal CDR: soporte metodológico + fundamento legal + redacción sugerida lista para dictamen.",
            "button": "Abrir LEX CDR",
            "tag": "Legal",
        },
    ]

    existing_modules = [m for m in modules if page_by_fname.get(m["fname"])]
    missing_modules = [m for m in modules if not page_by_fname.get(m["fname"])]

    kpi_row(
        [
            {"label": "Módulos activos", "value": len(existing_modules), "help": "Páginas disponibles en la suite"},
            {"label": "Flujo recomendado", "value": "Limpieza → Consulta → KMZ", "help": "Ruta operativa base"},
            {"label": "Modo", "value": "Laboratorio", "help": "Cambios seguros por etapas"},
        ],
        columns=3,
    )

    section_title("Centro de operaciones", "Accesos rápidos a los módulos principales de la suite.", "▦")

    cols = st.columns(3)
    for i, mod in enumerate(modules):
        col = cols[i % 3]
        with col:
            rel = page_by_fname.get(mod["fname"])
            module_card(mod["title"], mod["desc"], mod.get("tag", "Módulo"))
            if rel:
                st.page_link(rel, label=f"➡️ {mod['button']}")
            else:
                st.warning("Módulo no encontrado en /pages.", icon="⚠️")

    if missing_modules:
        info_panel(
            "Módulos pendientes",
            "Algunos accesos están declarados en la suite pero todavía no tienen archivo de página disponible. Se muestran como advertencia para no ocultar el estado del laboratorio.",
        )

    section_title("Sugerencias operativas", "Buenas prácticas para procesar lotes grandes sin saturar geocoding ni la sesión.", "◌")
    info_panel(
        "Rendimiento recomendado",
        "Ejecuta Limpieza primero con caché/PlusRepo cuando aplique; si faltan direcciones, realiza una segunda pasada limitada y divide lotes grandes en tandas controladas.",
    )


# =========================
#   FLUJO PRINCIPAL
# =========================

# 1) Guardián central (misma interfaz que en el resto de la suite)
login_guard("Portada / Lanzador de módulos")

# 2) Si pasó el guardián, ya está logueado → sidebar + dashboard
render_suite_sidebar()
launcher()
