import os

import streamlit as st

import core
from core import BANNER, inject_css, load
import portada
import privacidad
import seguridad as seg

st.set_page_config(page_title="VidaPlena CDMX", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")
inject_css()

@st.cache_resource(show_spinner="Preparando la base de datos (solo la primera vez, ~1 min)…")
def preparar_base():
    """En la nube no hay terminal: con AUTO_SEED=1 se crean tablas y datos sintéticos si faltan (idempotente)."""
    if os.getenv("AUTO_SEED") != "1":
        return "omitido"
    import seed
    from sqlalchemy import create_engine
    eng = create_engine(core.db_url(), pool_pre_ping=True, connect_args={"connect_timeout": 10} if core.db_url().startswith("postgresql") else {})
    try:
        if seed.base_lista(eng):          # caso normal: ya hay datos → no se toca nada
            return "lista"
    finally:
        eng.dispose()
    seed.main(reset=False)                # primera vez: crea tablas y datos
    return "ok"


# ---- Base de datos disponible y esquema al día ----
try:
    preparar_base()
except core.ConfigError as e:
    st.error(str(e))
    st.stop()
except Exception as e:
    st.error("No se pudo preparar la base de datos.")
    st.exception(e)
    st.stop()
try:
    adultos = load("adultos")
    load("usuarios")
except core.ConfigError as e:
    st.error(str(e))
    st.stop()
except Exception as e:
    st.error("No se pudo leer la base de datos o falta el esquema de seguridad. Enciende PostgreSQL y ejecuta:")
    st.code("docker compose up -d\npython seed.py          # crea tablas nuevas, cifra teléfonos y crea usuarios", language="bash")
    st.exception(e)
    st.stop()


def pantalla_login():
    st.markdown("""<style>
    .stApp{background:linear-gradient(135deg,#F4F7FB 0%,#E2EBF9 100%)}
    [data-testid="stForm"]{background:#fff;border:1px solid #E6E9EF;border-radius:20px;padding:1.7rem 1.6rem;
        box-shadow:0 8px 30px rgba(31,79,163,.12)}
    [data-testid="stHeader"]{background:transparent}
    [data-testid="stForm"] div[data-baseweb="input"], [data-testid="stForm"] div[data-baseweb="base-input"]
        {background:#EEF3FB !important;border-radius:10px}
    [data-testid="stForm"] div[data-baseweb="input"]{border:1px solid #D4E0F4}
    </style>""", unsafe_allow_html=True)
    izq, der = st.columns([1.15, 1], gap="large", vertical_alignment="center")
    with izq:
        st.markdown(portada.panel_html(), unsafe_allow_html=True)
    with der:
        with st.form("login"):
            usr = st.text_input("Usuario")
            pwd = st.text_input("Contraseña", type="password")
            ok = st.form_submit_button("Entrar", type="primary", use_container_width=True)
        if ok:
            u, msg = seg.autenticar(usr, pwd)
            if u:
                st.rerun()
            st.error(msg)
        with st.expander("Aviso de privacidad"):
            privacidad.aviso_simplificado()


OCULTAR_MENU = """<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"]
{display:none !important;}
</style>"""


def solo_pagina(funcion, titulo, ruta):
    """Muestra una pantalla sin menú lateral (login / consentimiento)."""
    pg_ = st.navigation([st.Page(funcion, title=titulo, url_path=ruta, default=True)], position="hidden")
    st.markdown(OCULTAR_MENU, unsafe_allow_html=True)
    pg_.run()
    st.stop()


if not seg.sesion_vigente():
    if st.session_state.pop("_expirada", False):
        st.warning("Tu sesión expiró por inactividad.")
    solo_pagina(pantalla_login, "Iniciar sesión", "login")

u = seg.usuario()

# ---- Compuerta de consentimiento (aviso de privacidad vigente) ----
if not seg.consentimiento_vigente(u["id"]):
    solo_pagina(lambda: privacidad.pantalla_consentimiento(u), "Aviso de privacidad", "consentimiento")

# ---- Navegación por rol ----
P = lambda f, t, i, **k: st.Page(f"views/{f}.py", title=t, icon=f":material/{i}:", url_path=f, **k)
ver = seg.PAGINAS_POR_ROL[u["rol"]]
grupos = {
    "Principal": [P("inicio", "Inicio", "home", default=True)],
    "Atención": [P("programa", "Programa Cuidados", "event_available"), P("salud", "Salud", "monitor_heart"),
                 P("solicitudes", "Solicitudes", "assignment")],
    "Red de apoyo": [P("cuidadores", "Cuidadores", "groups"), P("matching", "Matching Inteligente", "hub"),
                     P("mapa_cdmx", "Mapa CDMX", "location_on")],
    "Análisis": [P("observatorio", "Observatorio", "insights"), P("mapa_interactivo", "Mapa Interactivo", "map"),
                 P("dashboard", "Dashboard Ejecutivo", "dashboard")],
    "Privacidad y seguridad": [P("aviso", "Aviso de privacidad", "policy"),
                               P("mis_derechos", "Mis derechos", "verified_user"),
                               P("gestion_arco", "Gestión ARCO", "mail"),
                               P("auditoria", "Auditoría", "fact_check"),
                               P("estado_sistema", "Estado del sistema", "monitor_heart")],
}
paginas = {g: [p for p in ps if p.url_path in ver or p.url_path == ""] for g, ps in grupos.items()}
paginas = {g: ps for g, ps in paginas.items() if ps}
pg = st.navigation(paginas)

# ---- Barra lateral: usuario, adulto activo (solo los permitidos) y salir ----
permitidos = seg.permitidos_adultos()
with st.sidebar:
    st.divider()
    st.markdown(f"**{u['nombre']}**  \n<small>Rol: {u['rol']}</small>", unsafe_allow_html=True)
    if permitidos:
        nombres = {int(i): n for i, n in zip(adultos.id, adultos.nombre) if int(i) in permitidos}
        st.markdown("**Adulto mayor activo**")
        if st.session_state.get("adulto_id") not in nombres:
            st.session_state["adulto_id"] = next(iter(nombres))
        st.selectbox("Adulto mayor activo", list(nombres), format_func=lambda i: nombres[i],
                     key="adulto_id", label_visibility="collapsed")
    else:
        st.caption("Sin personas asignadas por ahora.")
    if st.button("Cerrar sesión", use_container_width=True):
        seg.cerrar_sesion()
        st.rerun()
    st.caption(f"Sesión se cierra tras {seg.TIMEOUT_MIN} min sin actividad.")

if st.session_state.get("_aviso_auditoria"):
    st.sidebar.warning(st.session_state.pop("_aviso_auditoria"))

pg.run()
