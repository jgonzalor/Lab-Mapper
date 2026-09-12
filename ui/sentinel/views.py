import json
from datetime import datetime,time
from zoneinfo import ZoneInfo
import streamlit as st
from core.sentinel import queries
from core.sentinel.models import TZ
from core.sentinel.correlation_engine import correlate
from core.sentinel.exporters import csv_bytes
from .canvas import render_canvas
from .entity_panel import evidence_table

def canvas_selection(result,allowed):
    if result and result.get('id') in allowed and result.get('nonce')!=st.session_state.get('sentinel_canvas_nonce'):
        st.session_state['sentinel_canvas_nonce']=result['nonce'];st.session_state['sentinel_selected']=result['id'];st.rerun()

def map_view(s,target,selected):
    tiles=st.checkbox('Activar cartografía pública OpenStreetMap',value=False,key='sentinel_osm')
    limit=st.select_slider('Máximo de sitios visibles',[50,100,250,500],value=100)
    points=queries.geography(s,target,limit)
    # Researcher supplied locations use the same entity model and never trigger geocoding.
    for e in queries.entities(s,limit=1000):
        if e['origin']!='MANUAL':continue
        item=queries.entity(s,e['id']);attrs=item['effective_attrs']
        if isinstance(attrs.get('lat'),(float,int)) and isinstance(attrs.get('lon'),(float,int)):
            if target:continue
            points.append({'id':e['id'],'lat':attrs['lat'],'lon':attrs['lon'],'label':item['display_label'],'manual':True,'source':item.get('source')})
    points=points[:limit]
    result=render_canvas('map',str(s.path)+'_map',selected,points=points,tiles=tiles)
    canvas_selection(result,{p['id'] for p in points})
    st.caption('Resumen por coordenadas de sitio; varios sectores pueden compartir el mismo punto. El límite visible no modifica los datos guardados.')
    with st.expander('Ubicaciones del filtro'):st.dataframe(points,use_container_width=True,hide_index=True)

def graph_view(s,selected):
    c1,c2=st.columns(2)
    with c1:mode=st.selectbox('Vista de relaciones',['COMUNES','EXPANSION'],format_func=lambda m:'Objetivos, contactos comunes e IMEI compartidos' if m=='COMUNES' else 'Expandir elemento seleccionado')
    with c2:limit=st.select_slider('Límite de entidades',[40,80,120,200],value=80)
    kinds=['']+[r['kind'] for r in s.rows('SELECT DISTINCT kind FROM relations ORDER BY kind')]
    kind=st.selectbox('Tipo de vínculo',kinds,format_func=lambda k:k or 'Todos')
    nodes,edges=queries.graph(s,selected if mode=='EXPANSION' else None,limit,mode,kind)
    result=render_canvas('graph',str(s.path)+'_graph',selected,nodes=nodes,edges=edges)
    canvas_selection(result,{x['id'] for x in nodes}|{x['id'] for x in edges})
    st.caption('Comunicación, tráfico especial y observación de IMEI son categorías distintas. Selecciona una línea para inspeccionar su soporte.')
    with st.expander('Relaciones visibles'):
        labels={n['id']:n['display_label'] for n in nodes}
        table=[{'id':e['id'],'origen':labels.get(e['source']),'destino':labels.get(e['destination']),'tipo':e['kind'],'eventos':e['event_count'],'registros':e['record_count'],'confianza':e['effective_confidence']} for e in edges]
        st.dataframe(table,hide_index=True,use_container_width=True)
        st.download_button('Exportar relaciones visibles',csv_bytes(table),file_name='SENTINEL_RELACIONES.csv')

def chronology(s,target,selected):
    c1,c2=st.columns(2)
    with c1:begin=st.date_input('Desde',value=None)
    with c2:end=st.date_input('Hasta',value=None)
    focus=st.checkbox('Aplicar entidad seleccionada',value=False,disabled=not bool(queries.entity(s,selected) if selected else None))
    page=st.number_input('Página de eventos (100 por página)',1,value=1)
    tz=ZoneInfo(TZ)
    lo=datetime.combine(begin,time.min,tz).timestamp() if begin else None
    hi=datetime.combine(end,time.max,tz).timestamp() if end else None
    if lo and hi and lo>hi:st.error('Intervalo de fechas invertido');return
    rows=queries.timeline(s,target,lo,hi,offset=(page-1)*100,subject=selected if focus else None)
    st.dataframe(rows,use_container_width=True,hide_index=True)
    st.download_button('Exportar página de cronología',csv_bytes(rows),file_name='SENTINEL_CRONOLOGIA.csv')
    if rows:
        eid=st.selectbox('Ver evidencia de evento',[r['id'] for r in rows],format_func=lambda i:next(r['local_time']+' · '+r['kind']+' · '+str(r['source'])+' → '+str(r['destination']) for r in rows if r['id']==i))
        evidence_table(s,eid,'timeline')

def analysis(s):
    metrics=queries.metrics(s);contacts=queries.contacts(s)
    st.markdown('**Contactos externos con tráfico documentado**')
    st.caption('Solo teléfonos, objetivos distintos y eventos soporte. Incluye tráfico especial diferenciado en cada vínculo; no confirma identidad personal.')
    threshold=st.slider('Mínimo de objetivos relacionados',1,max(1,metrics['Objetivos']),min(2,max(1,metrics['Objetivos']))) if metrics['Objetivos']>1 else 1
    visible=[{**r,'cobertura':str(r['objectives'])+'/'+str(metrics['Objetivos'])} for r in contacts if r['objectives']>=threshold]
    st.dataframe(visible,use_container_width=True,hide_index=True)
    if visible:
        contact=st.selectbox('Inspeccionar contacto',[r['id'] for r in visible],format_func=lambda i:next(r['canonical'] for r in visible if r['id']==i))
        if st.button('Abrir ficha de contacto'):st.session_state['sentinel_selected']=contact;st.rerun()
    st.markdown('**IMEI observados en varias líneas**');st.dataframe(queries.shared_devices(s),use_container_width=True,hide_index=True)
    st.markdown('**Relaciones objetivo–objetivo**')
    ids={r['id'] for r in s.rows('SELECT id FROM entities WHERE target=1')}
    direct=[r for r in queries.relations(s,limit=1000) if r['source'] in ids and r['destination'] in ids]
    labels={r['id']:r['label'] for r in s.rows('SELECT id,label FROM entities WHERE target=1')}
    st.dataframe([{**r,'source':labels[r['source']],'destination':labels[r['destination']]} for r in direct],use_container_width=True,hide_index=True)
    st.markdown('**Sitios celulares compartidos**');st.dataframe([p for p in queries.geography(s,limit=1000) if p['objectives']>1],use_container_width=True,hide_index=True)
    with st.form('sentinel_correlation'):
        opts=json.loads(s.meta('correlation_options') or '{}')
        window=st.number_input('Ventana temporal (segundos)',0,3600,opts.get('window_seconds',300))
        minimum=st.number_input('Eventos distintos por línea para relevancia operativa',2,100,opts.get('min_distinct_events',2))
        if st.form_submit_button('Recalcular coincidencias'):
            with st.spinner('Correlacionando eventos distintos…'):correlate(s,window,minimum)
            st.rerun()
    st.caption('Coincidencia celular ≠ presencia conjunta. Dos registros de una misma llamada lógica no constituyen coincidencia independiente. Estado: '+str(s.meta('correlation_status')))
    kind=st.selectbox('Hallazgos',['COINCIDENCIA_RELEVANTE','COINCIDENCIA_TEMPORAL'])
    page=st.number_input('Página de hallazgos',1,value=1)
    findings=s.rows('SELECT f.*,a.confidence reviewed_confidence,a.note FROM findings f LEFT JOIN annotations a ON a.subject_id=f.id WHERE f.kind=? ORDER BY f.id LIMIT 100 OFFSET ?',(kind,(page-1)*100))
    st.dataframe(findings,hide_index=True,use_container_width=True)
    if findings:
        fid=st.selectbox('Hallazgo para evidencia',[r['id'] for r in findings])
        if st.button('Abrir ficha de hallazgo'):st.session_state['sentinel_selected']=fid;st.rerun()
    st.download_button('Exportar contactos filtrados',csv_bytes(visible),file_name='SENTINEL_CONTACTOS.csv')

def evidence_view(s,selected):
    st.markdown('**Archivos de origen y calidad de importación**')
    st.dataframe(s.rows('SELECT name,target,sha256,imported_at,options,sheets FROM imports'),use_container_width=True,hide_index=True)
    status=st.selectbox('Estado de observaciones',['NO_CLASIFICADO','REVISAR','VALIDO'])
    page=st.number_input('Página de registros de calidad',1,value=1)
    rows=s.rows('''SELECT o.id,i.name archivo,r.row_number fila,o.kind,o.reason,o.quality FROM observations o JOIN raw_records r ON r.id=o.id JOIN imports i ON i.id=r.import_id WHERE o.status=? ORDER BY i.name,r.row_number LIMIT 100 OFFSET ?''',(status,(page-1)*100))
    st.dataframe(rows,hide_index=True,use_container_width=True)
    if rows:
        rid=st.selectbox('Registro original para inspección',[r['id'] for r in rows])
        evidence_table(s,rid,'quality')
    st.markdown('**Bitácora de cambios**');st.dataframe(s.rows('SELECT * FROM audit_log ORDER BY seq DESC LIMIT 100'),use_container_width=True,hide_index=True)
    st.markdown('**Interpretaciones conservadas, incluidas descartadas**')
    annotations=s.rows('SELECT * FROM annotations ORDER BY updated_at DESC LIMIT 100');st.dataframe(annotations,hide_index=True,use_container_width=True)
    if annotations:
        item=st.selectbox('Recuperar ficha de interpretación',[a['subject_id'] for a in annotations])
        if st.button('Revisar interpretación'):st.session_state['sentinel_selected']=item;st.rerun()
