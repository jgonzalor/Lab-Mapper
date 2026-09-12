"""Presentation orchestrator; only selected view executes on a Streamlit 1.35 rerun."""
from pathlib import Path
import streamlit as st
from core.sentinel.case_store import CaseStore
from core.sentinel import queries
from ui.components import render_page_header,render_kpi_row
from .case_panel import choose_case,case_actions
from .entity_panel import detail_panel,add_manual
from .views import map_view,graph_view,chronology,analysis,evidence_view

def render_app():
    st.markdown('<style>'+Path(__file__).with_name('styles.css').read_text()+'</style>',unsafe_allow_html=True)
    actor=st.session_state.get('username') or st.session_state.get('user_name')
    if not actor:st.error('Se requiere usuario autenticado para acceder a casos.');st.stop()
    render_page_header('Sentinel Mapa Investigativo','Una investigación · varias líneas · vínculos con evidencia navegable',status='GO MAPPER · SENTINEL V1 · INTERFAZ ACTUALIZADA',tags=['Local','America/Mazatlan','Trazabilidad'])
    path=choose_case(actor)
    if not path:st.info('Crea una investigación o abre un caso guardado.');return
    try:s=CaseStore(path,actor)
    except Exception as e:st.error(str(e));return
    try:
        st.subheader(s.meta('name'));case_actions(s)
        m=queries.metrics(s);render_kpi_row([{'label':k,'value':v} for k,v in m.items()])
        view=st.radio('Vista investigativa',['Mapa','Relaciones','Cronología','Evidencias','Análisis'],horizontal=True,label_visibility='collapsed',key='sentinel_view')
        descriptions={
            'Mapa':'Explora sitios celulares y ubicaciones documentadas. Selecciona un punto para consultar su evidencia.',
            'Relaciones':'Explora comunicaciones y dispositivos compartidos. Selecciona un nodo o vínculo para conocer su origen.',
            'Cronología':'Consulta los eventos por fecha y línea, junto con los registros que los sostienen.',
            'Evidencias':'Revisa archivos originales, calidad de importación e historial de cambios.',
            'Análisis':'Consulta contactos comunes, IMEI compartidos y coincidencias con sus criterios de cálculo.'}
        st.caption(descriptions[view])
        wide=st.checkbox('Vista amplia · mostrar la ficha debajo',value=False,key='sentinel_wide')
        if wide:
            left,center=st.columns([1,5]);right=None
        else:
            left,center,right=st.columns([1.05,4.2,1.65])
        with left:
            st.markdown('**Explorar investigación**')
            targets=['']+[r['canonical'] for r in s.rows('SELECT canonical FROM entities WHERE target=1 ORDER BY canonical')]
            target=st.selectbox('Línea / ubicaciones',targets,format_func=lambda x:x or 'Todas las líneas',key='sentinel_target')
            search=st.text_input('Buscar entidad',key='sentinel_search')
            kinds=['']+[r['kind'] for r in s.rows('SELECT DISTINCT kind FROM entities ORDER BY kind')]
            kind=st.selectbox('Categoría',kinds,format_func=lambda x:x.replace('_',' ').capitalize() if x else 'Todas',key='sentinel_kind')
            found=queries.entities(s,search,kind,limit=150)
            labels={r['id']:(r.get('edited_label') or r['label']) for r in found}
            chosen=st.selectbox('Entidades (hasta 150)', ['']+list(labels),format_func=lambda x:labels.get(x,'Seleccionar entidad'),key='sentinel_entity_search')
            if st.button('Abrir ficha',disabled=not chosen):st.session_state['sentinel_selected']=chosen;st.rerun()
            if st.button('Restablecer filtros',use_container_width=True):
                for key in ('sentinel_target','sentinel_search','sentinel_kind','sentinel_entity_search'):
                    st.session_state.pop(key,None)
                st.session_state.pop('sentinel_selected',None);st.rerun()
            if st.button('Limpiar selección'):st.session_state.pop('sentinel_selected',None);st.rerun()
            st.caption(f"{len(found)} entidades en esta búsqueda · selecciona una para abrir su ficha.")
        selected=st.session_state.get('sentinel_selected')
        with center:
            if view=='Mapa':map_view(s,target,selected)
            elif view=='Relaciones':graph_view(s,selected)
            elif view=='Cronología':chronology(s,target,selected)
            elif view=='Evidencias':evidence_view(s,selected)
            else:analysis(s)
        if right is not None:
            with right:detail_panel(s,selected)
        else:
            with st.container(border=True):
                detail_panel(s,selected)
        add_manual(s)
        if view in ('Mapa','Relaciones'):
            with st.expander('Eventos recientes de la línea seleccionada',expanded=False):
                st.dataframe(queries.timeline(s,target,limit=25),use_container_width=True,hide_index=True)
        st.caption('Cada cambio confirmado queda guardado. CONFIRMADO se refiere a la observación documental; no demuestra titularidad, usuario ni ubicación exacta de una persona.')
    finally:s.close()
