from pathlib import Path
import streamlit.components.v1 as components
_canvas=components.declare_component('sentinel_investigation_canvas',path=str(Path(__file__).parent/'frontend'))

def render_canvas(mode,key,selected=None,nodes=None,edges=None,points=None,tiles=False):
    # Send only the bounded read model required to draw, not raw CDR.
    slim=[{k:n.get(k) for k in ('id','kind','target','display_label')} for n in (nodes or [])]
    return _canvas(mode=mode,nodes=slim,edges=edges or [],points=points or [],tiles=tiles,selected=selected,key=key,default=None)
