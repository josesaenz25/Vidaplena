import seguridad as _seg
_seg.requiere("matching")
from datetime import datetime

import folium
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from core import (BLUE, COND_ESP, ESPECIALIDADES, PALETA, PRIORIDADES, SERVICIOS_SOL, TEAL,
                  adulto_activo, badge, estrellas, insert_row, load, mapa_base, page_header,
                  ranking_cuidadores, style_fig, with_alcaldia)

page_header("Matching Inteligente",
            "Recomendación del cuidador ideal según cercanía, especialidad, calificación y experiencia", "🤝")
a = adulto_activo()
cu = with_alcaldia(load("cuidadores"))

c1, c2 = st.columns([1.2, 1], gap="large")
with c1:
    st.markdown(f"<div class='vp-card'><h4>{a.nombre}</h4>{a.edad} años · {a.alcaldia}<br>"
                f"{badge(a.condicion, 'info')} {badge('Dependencia ' + a.nivel_dependencia, 'warn')}</div>",
                unsafe_allow_html=True)
    esp_def = COND_ESP.get(a.condicion, "Acompañamiento")
    esp = st.selectbox("Especialidad requerida", ESPECIALIDADES, index=ESPECIALIDADES.index(esp_def),
                       help="Se sugiere automáticamente según la condición del adulto mayor.")
with c2:
    with st.expander("⚙️ Ajustar importancia de los criterios", expanded=True):
        pesos = dict(
            dist=st.slider("Cercanía", 0, 100, 40), esp=st.slider("Especialidad", 0, 100, 30),
            cal=st.slider("Calificación", 0, 100, 20), exp=st.slider("Experiencia", 0, 100, 10))

rk = ranking_cuidadores(a, cu, esp, pesos)
if rk.empty:
    st.warning("No hay cuidadores disponibles.")
    st.stop()
top = rk.head(5)

st.markdown("#### Mejores 5 candidatos")
col_l, col_r = st.columns([1.3, 1], gap="large")
with col_l:
    for i, r in enumerate(top.itertuples(), 1):
        with st.container(border=True):
            h1, h2 = st.columns([3, 1])
            h1.markdown(f"**{i}. {r.nombre}**  \n{r.alcaldia} · {r.especialidad} · "
                        f"<span style='color:#F2A93B'>{estrellas(r.calificacion)}</span> {r.calificacion} · "
                        f"{r.experiencia_anios} años · a {r.distancia_km:.1f} km", unsafe_allow_html=True)
            h2.metric("Puntaje", f"{r.score:.0f}/100")
            st.progress(min(r.score / 100, 1.0))
            if st.button("Asignar este cuidador", key=f"asig_{r.id}", type="primary" if i == 1 else "secondary"):
                st.session_state["pend_asig"] = int(r.id)

    if "pend_asig" in st.session_state:
        cid = st.session_state["pend_asig"]
        nom = cu[cu.id == cid].iloc[0].nombre
        with st.form("confirmar"):
            st.markdown(f"**Confirmar asignación:** {nom} → {a.nombre}")
            f1, f2 = st.columns(2)
            tipo = f1.selectbox("Tipo de servicio", SERVICIOS_SOL)
            prio = f2.selectbox("Prioridad", PRIORIDADES, index=1)
            nota = st.text_input("Notas (opcional)")
            ok, cancel = st.columns(2)
            if ok.form_submit_button("Confirmar", type="primary"):
                ahora = datetime.now()
                insert_row("solicitudes", adulto_id=int(a.id), cuidador_id=cid, fecha_solicitud=ahora,
                           fecha_asignacion=ahora, tipo_servicio=tipo, prioridad=prio,
                           estatus="Asignada", notas=nota)
                del st.session_state["pend_asig"]
                st.toast("Asignación registrada. Revisa la página Solicitudes.", icon="✅")
                st.rerun()
            if cancel.form_submit_button("Cancelar"):
                del st.session_state["pend_asig"]
                st.rerun()

with col_r:
    nombres = [n.split()[0] + " " + n.split()[-1] for n in top.nombre]
    fig = go.Figure()
    for k, lab, colr in [("p_dist", "Cercanía", PALETA[0]), ("p_esp", "Especialidad", PALETA[1]),
                         ("p_cal", "Calificación", PALETA[3]), ("p_exp", "Experiencia", PALETA[4])]:
        fig.add_bar(y=nombres, x=top[k], name=lab, orientation="h", marker_color=colr)
    fig.update_layout(barmode="stack", title="Composición del puntaje", yaxis=dict(autorange="reversed"))
    st.plotly_chart(style_fig(fig, 320), use_container_width=True)

    m = mapa_base(a.lat, a.lon, 12)
    folium.Marker([a.lat, a.lon], tooltip=a.nombre, icon=folium.Icon(color="darkblue", icon="home")).add_to(m)
    for i, r in enumerate(top.itertuples(), 1):
        folium.Marker([r.lat, r.lon], tooltip=f"{i}. {r.nombre}", icon=folium.Icon(color="green" if i == 1 else "blue")).add_to(m)
        folium.PolyLine([[a.lat, a.lon], [r.lat, r.lon]], color=TEAL if i == 1 else BLUE, weight=2, opacity=.6).add_to(m)
    st_folium(m, height=300, use_container_width=True, returned_objects=[])
