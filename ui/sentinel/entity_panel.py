import json
from html import escape
import streamlit as st
from core.sentinel import queries
from core.sentinel.models import ENTITY_TYPES,CONFIDENCE,RELATION_TYPES
from core.sentinel.entity_engine import add_entity,add_relation
from core.sentinel.exporters import add_evidence,csv_bytes
from core.sentinel.validators import number

FIELDS={
'PERSONA':('nombre','alias','identificadores','rol'),
'TELEFONO':('numero','operador','titular_conocido','usuario_conocido','estado'),
'DISPOSITIVO':('imei','marca','modelo'), 'SIM':('imsi',),
'PERFIL_DIGITAL':('plataforma','usuario','url','correo'),
'VEHICULO':('marca','modelo','placas','color','propietario_documentado'),
'DOMICILIO':('direccion','tipo'), 'EMPRESA':('nombre','giro','direccion'),
'ANTENA':('cell_id','lac','tac','plus_code','azimuth'),
'EVIDENCIA':('descripcion','origen'), 'EVENTO':('tipo','fecha_hora','descripcion'),
'UBICACION':('nombre','tipo','direccion'),'OTRO':('descripcion',)}

def choose_subject(s,rows,label,key):
    labels={r['id']:r.get('edited_label') or r.get('label') or r.get('kind') or r['id'] for r in rows}
    return st.selectbox(label,['']+list(labels),format_func=lambda i:labels.get(i,'Seleccionar'),key=key)

def add_manual(s):
    with st.expander('＋ Agregar elemento / vincular'):
        kind=st.selectbox('Tipo de elemento',ENTITY_TYPES,key='sentinel_new_kind')
        custom_kind=st.text_input('Nombre de nueva categoría',value='OTRO') if kind=='OTRO' else kind
        with st.form('sentinel_add_entity'):
            label=st.text_input('Nombre o identificador visible')
            attrs={field:st.text_input(field.replace('_',' ').capitalize()) for field in FIELDS.get(kind,('descripcion',))}
            note=st.text_area('Observaciones del elemento');attrs['observaciones']=note
            c1,c2=st.columns(2)
            with c1:lat=st.text_input('Latitud documentada (opcional)')
            with c2:lon=st.text_input('Longitud documentada (opcional)')
            source=st.text_input('Fuente documental / oficio / informe')
            confidence=st.selectbox('Confianza inicial',CONFIDENCE,index=3)
            photo=st.file_uploader('Fotografía o evidencia opcional',type=['jpg','jpeg','png','pdf','txt'],key='sentinel_new_photo')
            if st.form_submit_button('Guardar elemento'):
                try:
                    if lat or lon:
                        la,lo=number(lat),number(lon)
                        if la is None or lo is None or not -90<=la<=90 or not -180<=lo<=180:raise ValueError('Coordenadas no válidas')
                        attrs.update(lat=la,lon=lo)
                    eid=add_entity(s,custom_kind.strip().upper(),label,attrs,source,confidence)
                    if photo:add_evidence(s,eid,photo.name,photo.getvalue(),'Adjunto del elemento',source)
                    st.session_state['sentinel_selected']=eid;st.rerun()
                except Exception as e:st.error(str(e))
        st.markdown('**Vincular elementos**')
        search=st.text_input('Buscar extremos de relación',key='sentinel_link_search')
        available=queries.entities(s,search,limit=1000)
        st.caption('Hasta 1,000 resultados; usa la búsqueda para encontrar otros elementos.')
        with st.form('sentinel_add_relation'):
            a=choose_subject(s,available,'Origen','sentinel_manual_a');b=choose_subject(s,available,'Destino','sentinel_manual_b')
            kind=st.selectbox('Relación',RELATION_TYPES);confidence=st.selectbox('Confianza del vínculo',CONFIDENCE,index=3)
            source=st.text_input('Fuente del vínculo');note=st.text_area('Explicación / evidencia disponible')
            start=st.text_input('Fecha inicial (opcional, AAAA-MM-DD)');end=st.text_input('Fecha final (opcional, AAAA-MM-DD)')
            if st.form_submit_button('Crear relación'):
                try:
                    from datetime import date
                    for v in (start,end):
                        if v:date.fromisoformat(v)
                    if not a or not b:raise ValueError('Selecciona los dos extremos')
                    st.session_state['sentinel_selected']=add_relation(s,a,b,kind,confidence,note,source,start or None,end or None);st.rerun()
                except Exception as e:st.error(str(e))

def evidence_table(s,subject,key='support'):
    page=st.number_input('Página de evidencia',1,value=1,key='sentinel_evp_'+key)
    rows=queries.support(s,subject,limit=50,offset=(page-1)*50)
    if rows:
        display=[{k:v for k,v in r.items() if k not in ('cells','quality','id')} for r in rows]
        st.dataframe(display,use_container_width=True,hide_index=True)
        st.download_button('Exportar esta página de soporte',csv_bytes(rows),file_name='SENTINEL_EVIDENCIA.csv',key='sentinel_evx_'+key)
        row=st.selectbox('Inspeccionar fila original',rows,format_func=lambda r:f"{r['archivo_origen']} · fila {r['fila_origen']}",key='sentinel_raw_'+key)
        st.json(json.loads(row['cells']));st.caption(row['quality'])
    else:st.caption('Sin filas CDR para esta selección. Consulta los documentos o la fuente manual.')

def detail_panel(s,selected):
    st.markdown('**Ficha de investigación**')
    if not selected:
        st.info('Selecciona un punto del mapa o un nodo del grafo para explorar su ficha.')
        st.caption('Aquí verás sus atributos, confianza y registros de origen. También puedes buscar un elemento en el panel izquierdo.')
        return
    item=queries.entity(s,selected)
    if item:
        st.subheader(item['display_label']);st.caption(item['kind']+' · '+item['origin'])
        attrs=item['effective_attrs']
        st.markdown('<span class="sentinel-badge">'+escape(item.get('confidence') or 'CONFIRMADO')+'</span>',unsafe_allow_html=True)
        for k,v in attrs.items():
            if v not in ('',None):
                st.markdown('<div class="sentinel-field"><small>'+escape(k.replace('_',' '))+'</small>'+escape(str(v))+'</div>',unsafe_allow_html=True)
        if item.get('note'):st.write(item['note'])
        if item['kind']=='ANTENA':
            sectors=s.rows('SELECT entity_id,azimuth,plus_code,address FROM locations WHERE site_key=(SELECT site_key FROM locations WHERE entity_id=?)',(selected,))
            st.caption('Sectores registrados en este sitio');st.dataframe(sectors,hide_index=True,use_container_width=True)
        current_confidence=item.get('confidence') or 'CONFIRMADO'
    else:
        matches=s.rows('SELECT * FROM relations WHERE id=?',(selected,)) or s.rows('SELECT * FROM findings WHERE id=?',(selected,))
        if not matches:st.info('La selección ya no existe tras recalcular; selecciona de nuevo.');return
        item=matches[0];st.subheader(item['kind'])
        for endpoint in ('source','destination'):
            v=queries.entity(s,item[endpoint]);st.markdown('**'+('Origen' if endpoint=='source' else 'Destino')+'**');st.write(v['display_label'] if v else item[endpoint])
        if 'event_count' in item:
            st.metric('Eventos soporte',item['event_count'])
            st.caption(str(item.get('record_count',0))+' registros CDR asociados')
        with st.expander('Atributos del vínculo / hallazgo'):
            st.write({k:v for k,v in item.items() if k not in ('source','destination','id')})
        ann=s.rows('SELECT * FROM annotations WHERE subject_id=?',(selected,))
        if ann:st.write({'Interpretación del investigador':ann[0]['note'],'Confianza revisada':ann[0]['confidence'],'Fuente':ann[0]['source']})
        attrs={};current_confidence=(ann[0]['confidence'] if ann else None) or item['confidence']
    with st.expander('Editar interpretación / descartar'):
        with st.form('sentinel_edit_'+selected):
            label=st.text_input('Etiqueta',value=item.get('display_label','')) if item.get('display_label') else None
            edited={k:st.text_input(k.replace('_',' ').capitalize(),value=str(attrs.get(k,'')),key='sentinel_edit_attr_'+k+selected) for k in FIELDS.get(item.get('kind'),())}
            latitude=st.text_input('Latitud documentada',value=str(attrs.get('lat',''))) if item.get('display_label') else ''
            longitude=st.text_input('Longitud documentada',value=str(attrs.get('lon',''))) if item.get('display_label') else ''
            note=st.text_area('Notas',value=item.get('note') or '')
            confidence=st.selectbox('Confianza / estado',CONFIDENCE,index=CONFIDENCE.index(current_confidence))
            source=st.text_input('Fuente de la revisión',value=item.get('source') or '')
            if st.form_submit_button('Guardar revisión'):
                try:
                    if latitude or longitude:
                        lat,lon=number(latitude),number(longitude)
                        if lat is None or lon is None or not -90<=lat<=90 or not -180<=lon<=180:raise ValueError('Coordenadas inválidas')
                        edited.update(lat=lat,lon=lon)
                    s.annotate(selected,label,{**attrs,**edited},confidence,note,source);st.rerun()
                except ValueError as e:st.error(str(e))
        st.caption('DESCARTADO retira el vínculo de la vista activa. Los originales y la bitácora permanecen disponibles.')
    with st.expander('Adjuntar evidencia'):
        with st.form('sentinel_attach_'+selected):
            up=st.file_uploader('Archivo',key='sentinel_evi_file_'+selected)
            desc=st.text_area('Descripción de evidencia');source=st.text_input('Fuente de evidencia')
            if st.form_submit_button('Guardar evidencia',disabled=up is None):
                try:add_evidence(s,selected,up.name,up.getvalue(),desc,source);st.rerun()
                except Exception as e:st.error(str(e))
    docs=s.rows('SELECT * FROM evidence WHERE subject_id=?',(selected,))
    for doc in docs:
        path=(s.path/doc['path']).resolve()
        if not path.is_relative_to(s.path):continue
        st.caption(doc['name']+' · SHA-256 '+doc['sha256'])
        st.download_button('Descargar '+doc['name'],path.read_bytes(),file_name=doc['name'],key='sentinel_doc_'+doc['id'])
        if doc['name'].lower().endswith(('.jpg','.jpeg','.png')):
            try:st.image(path.read_bytes(),use_column_width=True)
            except Exception:st.caption('No se pudo previsualizar la imagen; archivo preservado.')
    with st.expander('Filas CDR que sostienen este elemento'):
        evidence_table(s,selected,key='detail_'+selected)
