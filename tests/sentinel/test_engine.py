from io import BytesIO
import json,pytest,openpyxl
from core.sentinel.validators import phone,identifier,temporal,classify
from core.sentinel.case_store import CaseStore
from core.sentinel.importer_cdr import import_files
from core.sentinel.models import ImportOptions
from core.sentinel import queries
from core.sentinel.entity_engine import add_entity,add_relation
from core.sentinel.exporters import export_case,restore_case,add_evidence
from core.sentinel.correlation_engine import correlate

A='5550000001';B='5550000002';C='5550000003'
def book(target,rows):
    w=openpyxl.Workbook();s=w.active;s.title='Datos_Limpios'
    s.append(['Teléfono','Tipo','Número A','Número B','Datetime','Duración (seg)','IMEI','Latitud','Longitud','Azimuth'])
    for row in rows:s.append([target]+row)
    w.create_sheet('Duplicados').append(['NO IMPORTAR'])
    f=BytesIO();w.save(f);return f.getvalue()
def row(a=A,b=B,t='VOZ SALIENTE',dt='2026-01-01 12:00:00',dur=30,imei='35231739461624'):
    return [t,a,b,dt,dur,imei,25.0,-108.0,40]
@pytest.fixture
def case(tmp_path):
    s=CaseStore.create('Test','tester',root=tmp_path)
    yield s
    s.close()

def test_identifiers():
    assert phone('005550000001')=='005550000001'
    assert phone('525550000001')==A
    assert phone('5215550000001')==A
    assert phone('NAN')=='' and phone('internet.itelcel.com')==''
    assert identifier('0035231739461624')=='0035231739461624'
    assert classify('PREPAGO')=='NO_CLASIFICADO'
    assert identifier(1.234567890123456e16)==''

def test_time():
    local,ts,policy=temporal('2026-01-01 12:00:00')
    assert local.endswith('12:00:00-07:00')
    assert temporal('2026-01-01T19:00:00Z')[1]==ts
    assert temporal('04/05/2026 12:00')[0].startswith('2026-05-04')
    assert temporal('2020-10-25 01:30:00')[0] is None

def test_mirror_evidence_and_reopen(case):
    data=book(A,[row(),row(),row(t='PREPAGO')]);other=book(B,[row(t='VOZ ENTRANTE')])
    import_files(case,[(A+'.xlsx',data),(B+'.xlsx',other)])
    assert queries.metrics(case)['Objetivos']==2
    assert queries.metrics(case)['Eventos lógicos']==1
    assert queries.metrics(case)['No clasificados']==1
    event=case.rows('SELECT * FROM events')[0]
    assert len(queries.support(case,event['id']))==3
    assert import_files(case,[('copy.xlsx',data)])['imported']==0
    with CaseStore(case.path,'tester') as reopened:assert queries.metrics(reopened)['Eventos lógicos']==1
    with pytest.raises(PermissionError):CaseStore(case.path,'other')

def test_ambiguous_not_fused(case):
    import_files(case,[(A+'.xlsx',book(A,[row(dt='2026-01-01 12:00:00'),row(dt='2026-01-01 12:00:02')])),(B+'.xlsx',book(B,[row(t='VOZ ENTRANTE',dt='2026-01-01 12:00:01')]))],ImportOptions(dedup_seconds=2))
    assert queries.metrics(case)['Eventos lógicos']==3
    assert all('AMBIGUOS' in e['method'] for e in case.rows('SELECT * FROM events'))

def test_services_no_false_phone_contacts(case):
    import_files(case,[(A+'.xlsx',book(A,[row(a='UNOTV.COM',b=A,t='MENSAJE ENTRANTE'),row(b='internet.itelcel.com',t='DATOS')]))])
    assert queries.contacts(case)==[]
    assert queries.metrics(case)['Eventos lógicos']==2
    assert case.rows("SELECT * FROM entities WHERE kind='SERVICIO'")[0]['canonical']=='UNOTV.COM'

def test_manual_backup(case,tmp_path):
    import_files(case,[(A+'.xlsx',book(A,[row()]))])
    original=case.rows('SELECT cells FROM raw_records')
    person=add_entity(case,'PERSONA','Prueba',{'alias':'Ejemplo'},'Informe')
    phone_id=case.rows('SELECT id FROM entities WHERE target=1')[0]['id']
    rid=add_relation(case,person,phone_id,'UTILIZA','PROBABLE','Documentado','Oficio')
    case.annotate(rid,confidence='DESCARTADO',source='Revisión',note='No sostenido')
    add_evidence(case,person,'nota.txt',b'evidencia','Nota','Inspección')
    data=export_case(case);path=restore_case(data,'tester',tmp_path)
    with CaseStore(path,'tester') as s:
        assert queries.entity(s,person)['display_label']=='Prueba'
        assert not any(r['id']==rid for r in queries.relations(s))
        assert s.rows('SELECT cells FROM raw_records')==original
        assert s.rows('SELECT * FROM evidence')

def test_coincidences_exclude_same_call(case):
    import_files(case,[(A+'.xlsx',book(A,[row()])),(B+'.xlsx',book(B,[row(t='VOZ ENTRANTE')]))])
    assert correlate(case)['pairs']==0
    import_files(case,[(C+'.xlsx',book(C,[row(a=C,b='internet',t='DATOS',dt='2026-01-01 12:02:00')]))])
    assert correlate(case)['pairs']==2
    f=case.rows('SELECT * FROM findings')[0]
    assert len(queries.support(case,f['id']))==2

def test_reject_bad_structure_atomic(case):
    with pytest.raises(ValueError):import_files(case,[(A+'.xlsx',book(A,[row()])),('unknown.xlsx',book('',[row()]))])
    assert queries.metrics(case)['Registros']==0

def test_direction_and_transfer(case):
    import_files(case,[(A+'.xlsx',book(A,[row(a=B,b=C,t='VOZ TRANSFER'),row(a=A,b=B,t='VOZ ENTRANTE')]))])
    assert queries.metrics(case)['Por revisar']==2
    assert queries.metrics(case)['Eventos lógicos']==0

def test_null_duration_does_not_fuse(case):
    import_files(case,[(A+'.xlsx',book(A,[row(dur=None)])),(B+'.xlsx',book(B,[row(t='VOZ ENTRANTE',dur=None)]))])
    assert queries.metrics(case)['Eventos lógicos']==2

def test_same_target_separate_calls_not_time_bucketed(case):
    import_files(case,[(A+'.xlsx',book(A,[row(dt='2026-01-01 12:00:01'),row(dt='2026-01-01 12:00:02')]))])
    assert queries.metrics(case)['Eventos lógicos']==2

def test_bad_coordinates_preserve_event_without_map(case):
    r=row();r[-3]=95
    import_files(case,[(A+'.xlsx',book(A,[r]))])
    assert queries.metrics(case)['Eventos lógicos']==1
    assert queries.geography(case)==[]

def test_revision_never_changes_original(case):
    import_files(case,[(A+'.xlsx',book(A,[row()]))]);before=case.rows('SELECT * FROM raw_records')
    eid=case.rows('SELECT id FROM entities WHERE target=1')[0]['id']
    case.annotate(eid,label='Nueva etiqueta',source='Oficio',note='Verificación')
    assert case.rows('SELECT * FROM raw_records')==before
    assert queries.entity(case,eid)['display_label']=='Nueva etiqueta'
    assert case.rows("SELECT * FROM audit_log WHERE action='REVISION'")

def test_corrupted_bundle_rejected(case,tmp_path):
    import zipfile
    import_files(case,[(A+'.xlsx',book(A,[row()]))]);data=export_case(case)
    b=BytesIO()
    with zipfile.ZipFile(BytesIO(data)) as z,zipfile.ZipFile(b,'w') as out:
        for name in z.namelist():out.writestr(name,b'corrupted' if name=='case.db' else z.read(name))
    with pytest.raises(ValueError):restore_case(b.getvalue(),'tester',tmp_path)

def test_export_formula_escape():
    from core.sentinel.exporters import csv_bytes
    assert b"'=SUM" in csv_bytes([{'note':'=SUM(1,2)'}])

def test_date_only_not_assumed_midnight():
    assert temporal('2026-01-01')[0] is None

def test_discard_entity_excludes_graph(case):
    import_files(case,[(A+'.xlsx',book(A,[row()]))])
    eid=case.rows('SELECT id FROM entities WHERE target=1')[0]['id']
    case.annotate(eid,confidence='DESCARTADO',source='Revisión')
    nodes,edges=queries.graph(case,mode='EXPANSION')
    assert eid not in {n['id'] for n in nodes}
    assert not any(eid in (e['source'],e['destination']) for e in edges)
