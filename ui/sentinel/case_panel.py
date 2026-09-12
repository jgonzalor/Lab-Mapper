import streamlit as st
from core.sentinel.case_store import CaseStore
from core.sentinel.importer_cdr import import_files,inspect_workbook
from core.sentinel.models import ImportOptions
from core.sentinel.exporters import export_case,restore_case
from core.sentinel.correlation_engine import correlate

def rerun():st.rerun()
def choose_case(actor):
    with st.expander('Crear / abrir investigación',expanded='sentinel_case' not in st.session_state):
        choices=CaseStore.list_cases(actor)
        bypath={c['path']:c['name'] for c in choices}
        paths=list(bypath);current=st.session_state.get('sentinel_case')
        chosen=st.selectbox('Casos guardados',['']+paths,index=paths.index(current)+1 if current in paths else 0,format_func=lambda p:bypath.get(p,'Seleccionar investigación'),key='sentinel_case_choice')
        if st.button('Abrir caso',disabled=not chosen):
            st.session_state['sentinel_case']=chosen;st.session_state.pop('sentinel_selected',None);rerun()
        with st.form('sentinel_create_case'):
            name=st.text_input('Nombre de investigación');desc=st.text_area('Descripción');investigator=st.text_input('Investigador',value=actor)
            if st.form_submit_button('Crear caso',type='primary'):
                try:
                    with CaseStore.create(name,actor,desc,investigator) as s:st.session_state['sentinel_case']=str(s.path)
                    st.session_state.pop('sentinel_selected',None);rerun()
                except ValueError as e:st.error(str(e))
        restore=st.file_uploader('Recuperar paquete de caso (.zip)',type=['zip'],key='sentinel_restore')
        if st.button('Recuperar caso',disabled=restore is None):
            try:st.session_state['sentinel_case']=restore_case(restore.getvalue(),actor);st.session_state.pop('sentinel_selected',None);rerun()
            except Exception as e:st.error('No se recuperó el paquete: '+str(e))
    return st.session_state.get('sentinel_case')

def case_actions(s):
    with st.expander('Importar CDR / respaldo / datos del caso'):
        st.caption('Un caso admite varias líneas. Se procesa únicamente Datos_Limpios; se preserva cada Excel original.')
        uploads=st.file_uploader('Excel de Go Mapper Limpieza',type=['xlsx'],accept_multiple_files=True,key='sentinel_uploads')
        col1,col2=st.columns(2)
        import json
        policy=json.loads(s.meta('import_options') or '{}')
        with col1:seconds=st.number_input('Tolerancia de espejo (segundos)',0,30,int(policy.get('dedup_seconds',0)),disabled=bool(policy))
        with col2:dur=st.number_input('Tolerancia de duración (segundos)',0,5,int(policy.get('duration_tolerance',0)),disabled=bool(policy))
        st.caption('Hora sin zona: America/Mazatlan por convención, sin desplazamiento. A=origen; B=destino. Empates no se fusionan.')
        if st.button('Importar y analizar',type='primary',disabled=not uploads):
            try:
                with st.spinner('Validando, preservando evidencia y correlacionando…'):
                    result=import_files(s,[(u.name,u.getvalue()) for u in uploads],ImportOptions(dedup_seconds=seconds,duration_tolerance=dur))
                    result['correlation']=correlate(s)
                st.session_state['sentinel_notice']=result;rerun()
            except Exception as e:st.error('Importación no completada: '+str(e))
        if 'sentinel_notice' in st.session_state:st.success(str(st.session_state.pop('sentinel_notice')))
        if st.button('Preparar respaldo completo'):
            try:
                st.session_state['sentinel_backup']=(str(s.path),export_case(s),int(s.meta('revision')))
            except Exception as e:st.error(str(e))
        backup=st.session_state.get('sentinel_backup')
        if backup and backup[0]==str(s.path):
            if backup[2]!=int(s.meta('revision')):st.info('El caso cambió: prepara un nuevo respaldo para incluir los cambios recientes.')
            st.download_button('Descargar investigación (.zip)',backup[1],file_name='SENTINEL_CASO.zip',mime='application/zip')
        with st.form('sentinel_case_metadata'):
            name=st.text_input('Nombre del caso',value=s.meta('name'));desc=st.text_area('Observaciones del caso',value=s.meta('description'));investigator=st.text_input('Investigador responsable',value=s.meta('investigator'))
            if st.form_submit_button('Guardar datos del caso'):
                try:s.update_case(name,desc,investigator);rerun()
                except ValueError as e:st.error(str(e))
        st.caption('Las modificaciones se guardan en disco al confirmar cada acción. El ZIP incluye base de datos, originales y evidencias.')
        if st.button('Cerrar investigación'):
            for k in ('sentinel_case','sentinel_selected','sentinel_backup'):st.session_state.pop(k,None)
            rerun()
