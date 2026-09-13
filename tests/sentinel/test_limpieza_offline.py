"""Exercise the actual cleaning function with all address/network routes booby-trapped."""
from pathlib import Path
from io import BytesIO
import ast,pandas as pd,pytest
from core.limpieza_offline import offline_address

class Progress:
    def progress(self,*a,**k):pass
class UI:
    def progress(self,*a,**k):return Progress()
    def __getattr__(self,name):return lambda *a,**k:None

def load_cleaning_functions():
    path=Path(__file__).resolve().parents[2]/'pages'/'app_limpieza_excel.py'
    tree=ast.parse(path.read_text())
    body=[]
    for node in tree.body:
        if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='page_header':break
        if isinstance(node,(ast.Import,ast.ImportFrom,ast.FunctionDef,ast.Assign,ast.AnnAssign)):body.append(node)
        elif isinstance(node,ast.Try) and any(isinstance(n,(ast.Import,ast.ImportFrom)) for n in node.body):body.append(node)
    ns={};exec(compile(ast.Module(body=body,type_ignores=[]),str(path),'exec'),ns);ns['st']=UI();return ns

def test_offline_address_preserves_supplied():
    assert offline_address({'Direccion_final':'Dirección documentada'})=='Dirección documentada'
    assert offline_address({'PLUS_CODE_NOMBRE':'Dirección previa'})=='Dirección previa'
    assert 'OFFLINE' in offline_address({'PLUS_CODE_NOMBRE':float('nan')})

@pytest.mark.parametrize('offline,enabled',[(True,True),(False,False)])
def test_actual_pipeline_makes_zero_network_calls(tmp_path,monkeypatch,offline,enabled):
    ns=load_cleaning_functions();ns['GEOCODE_ENABLED']=enabled
    ns['PLUS_REPO_DIR']=str(tmp_path);ns['PLUS_REPO_DB']=str(tmp_path/'repo.sqlite');ns['CACHE_DB_PATH']=str(tmp_path/'geo.sqlite')
    def forbidden(*a,**k):raise AssertionError('Offline or disabled mode attempted address lookup')
    for key in ('reverse_address','pluscode_label','_reverse_http_base','_reverse_http_addr','_reverse_opencage','_get_geopy_reverse_for_host'):ns[key]=forbidden
    if offline:
        for key in ('init_plus_repo','pr_get_nombre','pr_get_near_name','pr_save_plus'):ns[key]=forbidden
    monkeypatch.setattr(ns['requests'],'get',forbidden)
    df=pd.DataFrame([[5550000001,'VOZ SALIENTE',5550000001,5550000002,'01/01/2026','12:34:56',30,35231739461624,25.,-108.,40]],columns=['Teléfono','Tipo','Número A','Número B','Fecha','Hora','Duración (seg)','IMEI','Latitud','Longitud','Azimuth'])
    ns['leer_archivo']=lambda f:df.copy()
    data,name=ns['limpiar_excel'](None,offline=offline)
    x=pd.ExcelFile(BytesIO(data));out=pd.read_excel(x,'Datos_Limpios')
    assert len(out)==1 and out['Número A'].iloc[0]==5550000001
    assert str(out.Datetime.iloc[0])=='2026-01-01 12:34:56'
    assert out.PLUS_CODE.iloc[0]
    assert set(x.sheet_names)=={'Datos_Limpios','LOG_Limpieza','ESTADISTICAS'}
    if offline:
        assert 'OFFLINE' in out.Direccion_final.iloc[0]
        assert 'OFFLINE' in pd.read_excel(x,'LOG_Limpieza')['Modo geocodificación'].iloc[0]

def test_geopy_factory_valid_rate_limiter():
    ns=load_cleaning_functions()
    # Constructing the client makes no reverse-geocoding request. Old delay values asserted here.
    limiter=ns['_get_geopy_reverse_for_host']('nominatim.openstreetmap.org')
    assert limiter.error_wait_seconds>=limiter.min_delay_seconds
