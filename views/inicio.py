import seguridad as _seg
_seg.requiere("inicio")
import streamlit as st

from core import BANNER, ESTATUS_ACTIVOS, NAVY, horas_respuesta, kpi_row, load

if BANNER.exists():
    st.image(str(BANNER), use_container_width=True)
else:
    st.markdown(
        f"<div class='vp-header'><div class='vp-title' style='font-size:2.2rem'>VidaPlena CDMX</div>"
        f"<div class='vp-sub'>Bienestar y cuidado para nuestros adultos mayores</div></div>",
        unsafe_allow_html=True)

st.markdown(f"<h1 style='margin:.4rem 0 0 0'>VidaPlena CDMX</h1>", unsafe_allow_html=True)
st.markdown("##### Sistema de gestión y monitoreo para adultos mayores.")
st.markdown(f"<div class='vp-card' style='margin-top:.6rem'><h3 style='margin:0'>👋 {_seg.saludo()}</h3>"
            f"<small>Rol: {_seg.rol()}</small></div>", unsafe_allow_html=True)

_perm = _seg.permitidos_adultos()
ad, cu, so = load("adultos"), load("cuidadores"), load("solicitudes")
if _seg.rol() != "coordinacion":      # mínimo privilegio: solo lo propio
    ad, so = ad[ad.id.isin(_perm)], so[so.adulto_id.isin(_perm)]
    cu = cu[cu.id.isin(so.cuidador_id.dropna())]
activas = so[so.estatus.isin(ESTATUS_ACTIVOS)]
kpi_row([
    ("Adultos registrados" if _seg.rol() == "coordinacion" else "Personas a mi cargo", f"{len(ad):,}", "Personas bajo seguimiento", "blue"),
    ("Cuidadores", f"{len(cu):,}", f"{int(cu.disponible.sum())} disponibles hoy", "teal"),
    ("Solicitudes", f"{len(so):,}", f"{len(activas)} activas", "amber"),
    ("Respuesta media", (f"{horas_respuesta(so).mean():.1f} h" if len(so) and horas_respuesta(so).notna().any() else "—"), "Solicitud → asignación", "green"),
])

st.write("")
st.markdown("#### Cómo funciona el sistema")
pasos = [("1", "Registro", "Perfil, condición y ubicación"), ("2", "Matching", "Cuidador ideal por puntaje"),
         ("3", "Asignación", "Solicitud gestionada"), ("4", "Seguimiento", "Agenda y salud diaria"),
         ("5", "Análisis", "Observatorio y dashboard")]
for col, (n, t, d) in zip(st.columns(5), pasos):
    col.markdown(f"<div class='vp-step'><b>{n}</b><span><strong>{t}</strong></span><span>{d}</span></div>",
                 unsafe_allow_html=True)

st.write("")
c1, c2 = st.columns([1, 1.5], gap="large")
with c1:
    st.markdown("#### Tecnologías")
    chips = "".join(f"<span class='chip'>{t}</span>" for t in
                    ["Python", "Streamlit", "PostgreSQL", "SQLAlchemy", "Plotly", "Folium", "Docker"])
    st.markdown(f"<div class='vp-card'>{chips}</div>", unsafe_allow_html=True)
with c2:
    st.markdown("#### Funcionalidades")
    with st.container(border=True):
        f1, f2 = st.columns(2)
        with f1:
            if "dashboard" in _seg.PAGINAS_POR_ROL[_seg.rol()]:
                st.page_link("views/dashboard.py", label="Dashboard Ejecutivo", icon="📊")
            if "observatorio" in _seg.PAGINAS_POR_ROL[_seg.rol()]:
                st.page_link("views/observatorio.py", label="Observatorio de Datos", icon="🔎")
            if "matching" in _seg.PAGINAS_POR_ROL[_seg.rol()]:
                st.page_link("views/matching.py", label="Matching Inteligente", icon="🤝")
        with f2:
            if "solicitudes" in _seg.PAGINAS_POR_ROL[_seg.rol()]:
                st.page_link("views/solicitudes.py", label="Solicitudes", icon="📝")
            if "mapa_interactivo" in _seg.PAGINAS_POR_ROL[_seg.rol()]:
                st.page_link("views/mapa_interactivo.py", label="Mapa Interactivo", icon="🗺️")
            if "salud" in _seg.PAGINAS_POR_ROL[_seg.rol()]:
                st.page_link("views/salud.py", label="Monitoreo de Salud", icon="❤️")

st.write("")
valores = [("❤️", "Mejores condiciones de vida"), ("👥", "Comunidades más solidarias"),
           ("📊", "Decisiones basadas en datos"), ("🤲", "Un cuidado más justo e incluyente")]
for col, (i, t) in zip(st.columns(4), valores):
    col.markdown(f"<div class='vp-card' style='text-align:center;color:{NAVY}'><div style='font-size:1.6rem'>{i}</div>"
                 f"<strong>{t}</strong></div>", unsafe_allow_html=True)
