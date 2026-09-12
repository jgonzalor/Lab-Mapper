"""A cellular site is not a handset location. Sector identity retained separately."""
import re
from .validators import number,text
from .entity_engine import ensure_entity
from .models import stable

def locate(con,row):
    lat,lon=number(row.get('lat')),number(row.get('lon'))
    issues=[]
    if lat is None or lon is None:return None,['COORDENADAS_AUSENTES_O_NO_NUMERICAS']
    if not -90<=lat<=90 or not -180<=lon<=180 or (lat==0 and lon==0):return None,['COORDENADAS_NO_VALIDAS']
    az=number(row.get('azimuth'))
    if az is not None and not 0<=az<360:issues.append('AZIMUTH_NO_VALIDO');az=None
    plus=text(row.get('plus')).upper().replace(' ','')
    if plus and not re.fullmatch(r'[23456789CFGHJMPQRVWX]{8}\+[23456789CFGHJMPQRVWX]{2,3}',plus):issues.append('PLUS_CODE_NO_COMPLETO_O_INVALIDO')
    try:
        from openlocationcode import openlocationcode as olc
        if plus and olc.isFull(plus):
            area=olc.decode(plus)
            if not (area.latitudeLo<=lat<=area.latitudeHi and area.longitudeLo<=lon<=area.longitudeHi):issues.append('PLUS_CODE_DISCREPA_COORDENADAS')
    except ImportError:
        if plus:issues.append('PLUS_CODE_VALIDACION_GEOMETRICA_NO_DISPONIBLE')
    site=f'{lat:.7f},{lon:.7f}'
    cell=text(row.get('cell'));lac=text(row.get('lac'));tac=text(row.get('tac'))
    key=stable(site,az,cell,lac,tac)
    address=text(row.get('address'))
    eid=ensure_entity(con,'ANTENA',key,(address or site)+(f' · {az:g}°' if az is not None else ''),{'site_key':site,'lat':lat,'lon':lon,'azimuth':az,'plus_code':plus,'cell_id':cell,'lac':lac,'tac':tac,'interpretation':'Sitio/sector registrado; no ubicación GPS del usuario'})
    con.execute('INSERT OR IGNORE INTO locations VALUES(?,?,?,?,?,?,?)',(eid,site,lat,lon,az,plus,address))
    return eid,issues
