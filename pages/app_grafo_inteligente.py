# pages/app_grafo_inteligente.py
# 🕸️ Grafo Inteligente (MAPPER) — v2 (estable)
#
# - Carga grafo JSON (nodos/aristas) o Excel con NODOS/ARISTAS
# - Permite editar en tabla y exportar
# - Render visual opcional si existe pyvis

from __future__ import annotations

import json
from io import BytesIO
from datetime import datetime

import pandas as pd
import streamlit as st
from suite_nav import render_suite_sidebar
from ui.styles import apply_theme, kpi_row
from ui.components import render_card, render_page_header, render_section, render_step_header

APP_TITLE = "🕸️ Grafo Inteligente de Relaciones (MAPPER) — v2"

def df_to_excel_bytes(nodos: pd.DataFrame, aristas: pd.DataFrame) -> bytes:
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        nodos.to_excel(writer, index=False, sheet_name="NODOS")
        aristas.to_excel(writer, index=False, sheet_name="ARISTAS")
    return out.getvalue()

def try_render_pyvis(nodos: pd.DataFrame, aristas: pd.DataFrame):
    try:
        from pyvis.network import Network
        import streamlit.components.v1 as components
        net = Network(height="620px", width="100%", directed=True)
        for _, n in nodos.iterrows():
            net.add_node(str(n.get("id")), label=str(n.get("label", n.get("id"))))
        for _, e in aristas.iterrows():
            net.add_edge(str(e.get("source")), str(e.get("target")), value=int(e.get("peso_eventos", 1)))
        html = net.generate_html()
        components.html(html, height=640, scrolling=True)
        return True
    except Exception:
        return False

def main():
    st.set_page_config(page_title="Grafo Inteligente (MAPPER)", layout="wide")
    render_suite_sidebar()
    apply_theme()
    render_page_header(
        "Grafo Inteligente",
        "Carga, edita y exporta nodos/aristas con una vista visual opcional para análisis de relaciones.",
        status="GRAFO OPERATIVO",
        tags=["JSON", "Excel", "PyVis opcional"],
    )

    with render_card():
        render_step_header("01", "Filtros / carga", "Carga el grafo base y exporta el estado actual cuando exista en sesión.")
        col1, col2 = st.columns(2)
        with col1:
            up = st.file_uploader("Cargar JSON o Excel (NODOS/ARISTAS)", type=["json","xlsx"])
            load = st.button("Cargar", type="primary")
        with col2:
            if "nodos" in st.session_state and "aristas" in st.session_state:
                nodos = st.session_state["nodos"]
                aristas = st.session_state["aristas"]
                st.download_button("⬇️ Exportar Excel", data=df_to_excel_bytes(nodos, aristas),
                                   file_name=f"GRAFO_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)
                payload = {"nodos": nodos.to_dict(orient="records"), "aristas": aristas.to_dict(orient="records")}
                st.download_button("⬇️ Exportar JSON", data=json.dumps(payload, ensure_ascii=False, indent=2),
                                   file_name=f"GRAFO_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                   mime="application/json",
                                   use_container_width=True)
            else:
                st.caption("Sin grafo cargado todavía.")

    if load and up:
        if up.name.endswith(".json"):
            data = json.loads(up.getvalue().decode("utf-8"))
            nodos = pd.DataFrame(data.get("nodos", []))
            aristas = pd.DataFrame(data.get("aristas", []))
        else:
            xls = pd.ExcelFile(up)
            nodos = pd.read_excel(xls, "NODOS") if "NODOS" in xls.sheet_names else pd.DataFrame()
            aristas = pd.read_excel(xls, "ARISTAS") if "ARISTAS" in xls.sheet_names else pd.DataFrame()

        if len(nodos)==0:
            nodos = pd.DataFrame(columns=["id","label","tipo"])
        if len(aristas)==0:
            aristas = pd.DataFrame(columns=["source","target","tipo","peso_eventos"])

        st.session_state["nodos"] = nodos
        st.session_state["aristas"] = aristas
        st.success("Grafo cargado.")

    if "nodos" not in st.session_state:
        st.info("Carga un grafo para comenzar.")
        return

    nodos = st.session_state["nodos"]
    aristas = st.session_state["aristas"]

    render_section("Métricas rápidas", "Resumen del grafo cargado antes de editar o renderizar.", "02")
    kpi_row([
        {"label": "Nodos", "value": f"{len(nodos):,}", "help": "Entidades disponibles"},
        {"label": "Aristas", "value": f"{len(aristas):,}", "help": "Relaciones disponibles"},
    ], columns=2)

    render_section("Tablas de soporte", "Edición tabular de nodos y aristas; funciona como evidencia auxiliar del grafo.", "03")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**NODOS**")
        st.session_state["nodos"] = st.data_editor(nodos, num_rows="dynamic", use_container_width=True, height=320)
    with c2:
        st.write("**ARISTAS**")
        st.session_state["aristas"] = st.data_editor(aristas, num_rows="dynamic", use_container_width=True, height=320)

    render_section("Grafo interactivo", "Visual principal de relaciones basado en los nodos y aristas actuales.", "04")
    rendered = try_render_pyvis(st.session_state["nodos"], st.session_state["aristas"])
    if not rendered:
        st.info("No se pudo renderizar (pyvis no instalado). Puedes instalarlo o quedarte con la vista tabular.")

if __name__ == "__main__":
    main()
