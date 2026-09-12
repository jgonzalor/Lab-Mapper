"""Stable Suite route for Sentinel Mapa Investigativo."""
import streamlit as st

def main():
    # Streamlit 1.35 requires this before imports that register custom components.
    st.set_page_config(page_title='Sentinel Mapa Investigativo',page_icon='🗺️',layout='wide')
    from guardian import login_guard
    login_guard('Sentinel Mapa Investigativo')
    from suite_nav import render_suite_sidebar
    from ui.styles import apply_theme
    from ui.sentinel.app import render_app
    render_suite_sidebar()
    apply_theme()
    render_app()

if __name__=='__main__':main()
