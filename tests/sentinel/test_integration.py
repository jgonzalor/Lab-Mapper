"""Opt-in real dataset integration. Never commit carrier Excel files or identifiers."""
import os,json
from pathlib import Path
import pytest
from core.sentinel.case_store import CaseStore
from core.sentinel.importer_cdr import import_files
from core.sentinel.correlation_engine import correlate
from core.sentinel.exporters import export_case,restore_case
from core.sentinel import queries

@pytest.mark.skipif(not os.environ.get('SENTINEL_TEST_DATA'),reason='Set SENTINEL_TEST_DATA to the four original Excel directory')
def test_four_real_excels(tmp_path):
    files=sorted(Path(os.environ['SENTINEL_TEST_DATA']).glob('*LIMPIEZA ESTADISTICO SUITE.xlsx'))
    assert len(files)==4
    with CaseStore.create('Integration','test',root=tmp_path) as s:
        import_files(s,[(p.name,p.read_bytes()) for p in files])
        m=queries.metrics(s)
        assert m=={'Objetivos':4,'Registros':14171,'Eventos lógicos':12894,'No clasificados':106,'Por revisar':1}
        contacts=queries.contacts(s)
        assert sum(r['objectives']==4 for r in contacts)==2
        assert sum(r['objectives']==3 for r in contacts)==4
        devices=queries.shared_devices(s);assert len(devices)==3
        assert all(r['objectives']==2 for r in devices)
        assert all(len(r['imei'])==14 for r in devices)
        targets=s.rows('SELECT id FROM entities WHERE target=1');ids={r['id'] for r in targets}
        assert any(r['source'] in ids and r['destination'] in ids for r in queries.relations(s,limit=1000))
        assert len([p for p in queries.geography(s,limit=1000) if p['objectives']>1])==10
        assert s.rows('SELECT COUNT(*) n FROM observations WHERE status=\'VALIDO\'')[0]['n']==s.rows('SELECT COUNT(*) n FROM event_support')[0]['n']
        assert s.rows("SELECT COUNT(*) n FROM events WHERE method LIKE 'ESPEJO_UNICO%'")[0]['n']==5
        result=correlate(s);assert result['pairs']>0 and result['relevant']>0 and result['status']=='COMPLETO'
        assert s.con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not s.con.execute('PRAGMA foreign_key_check').fetchall()
        bundle=export_case(s);restored=restore_case(bundle,'test',tmp_path)
        with CaseStore(restored,'test') as r:
            assert queries.metrics(r)==m
            assert queries.contacts(r)==contacts
            assert r.con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        for entity in contacts[:2]+devices:
            assert queries.support(s,entity['id'])
        assert import_files(s,[(p.name,p.read_bytes()) for p in files])['imported']==0
        assert queries.metrics(s)==m
