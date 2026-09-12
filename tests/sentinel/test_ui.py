"""Streamlit AppTest exercises view reruns, selection and access without browser secrets."""
from pathlib import Path
from streamlit.testing.v1 import AppTest
from core.sentinel.case_store import CaseStore
from core.sentinel.entity_engine import add_entity,add_relation

PAGE=Path(__file__).resolve().parents[2]/'pages'/'app_grafo_inteligente.py'

def test_guard_stops_unauthenticated():
    a=AppTest.from_file(str(PAGE)).run()
    assert not a.exception
    assert any(i.label=='Contraseña' for i in a.text_input)
    assert not any(i.label=='Nombre de investigación' for i in a.text_input)

def test_views_and_manual_selection(tmp_path,monkeypatch):
    monkeypatch.setenv('SENTINEL_CASES_DIR',str(tmp_path))
    with CaseStore.create('UI test','ui',root=tmp_path) as s:
        entity=add_entity(s,'PERSONA','Persona sintética',{'alias':'Prueba'},'Test')
        path=str(s.path)
    a=AppTest.from_file(str(PAGE),default_timeout=15)
    a.session_state['logged_in']=True;a.session_state['suite_auth']=True;a.session_state['username']='ui';a.session_state['sentinel_case']=path
    a.run();assert not a.exception
    a.session_state['sentinel_selected']=entity
    for v in ('Mapa','Relaciones','Cronología','Evidencias','Análisis'):
        a.radio(key='sentinel_view').set_value(v).run();assert not a.exception
    assert any(x.value=='Persona sintética' for x in a.subheader)
