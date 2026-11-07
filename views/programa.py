import seguridad as _seg
_seg.requiere("programa")
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from core import (BLUE, PLANTILLA_AGENDA, TEAL, adulto_activo, badge, insert_many,
                  insert_row, load, page_header, solicitudes_full, style_fig, update_row)

page_header("Programa de Cuidados", "Agenda personalizada de actividades, medicamentos y recordatorios", "🗓️")
a = adulto_activo()
act = load("actividades")
act = act[act.adulto_id == a.id]

col_a, col_b = st.columns([1.6, 1], gap="large")

with col_a:
    fecha = st.date_input("Fecha de la agenda", value=date.today(), key="prog_fecha")
    dia = act[act.fecha.dt.date == fecha].sort_values("hora")

    if dia.empty:
        st.info("No hay actividades programadas para esta fecha.")
        if st.button("Generar agenda recomendada", type="primary"):
            insert_many("actividades", [dict(adulto_id=int(a.id), fecha=fecha, hora=h, actividad=t,
                                             tipo=tp, completada=False) for h, t, tp in PLANTILLA_AGENDA])
            st.rerun()
    else:
        hechas = int(dia.completada.sum())
        st.progress(hechas / len(dia), text=f"{hechas} de {len(dia)} actividades completadas")

        def _toggle(act_id):
            update_row("actividades", act_id, completada=bool(st.session_state[f"act_{act_id}"]))

        with st.container(border=True):
            for r in dia.itertuples():
                st.checkbox(f"**{r.hora}** · {r.actividad}  —  _{r.tipo}_", value=bool(r.completada),
                            key=f"act_{r.id}", on_change=_toggle, args=(int(r.id),))

    with st.expander("➕ Agregar actividad o recordatorio"):
        with st.form("nueva_act", clear_on_submit=True):
            f1, f2 = st.columns([1, 2])
            hora = f1.time_input("Hora", value=datetime.strptime("09:00", "%H:%M").time())
            texto = f2.text_input("Actividad", placeholder="Ej. Cita con geriatra")
            tipo = st.selectbox("Tipo", ["Medicamento", "Actividad física", "Bienestar",
                                         "Alimentación", "Social", "Cita médica"])
            if st.form_submit_button("Guardar actividad", type="primary"):
                if texto.strip():
                    insert_row("actividades", adulto_id=int(a.id), fecha=fecha,
                               hora=hora.strftime("%H:%M"), actividad=texto.strip(),
                               tipo=tipo, completada=False)
                    st.rerun()
                else:
                    st.warning("Escribe el nombre de la actividad.")

with col_b:
    st.markdown(f"""<div class='vp-card'><h4>{a.nombre}</h4>
        {a.edad} años · {a.alcaldia}<br>
        {badge(a.condicion, 'info')} {badge('Dependencia ' + a.nivel_dependencia, 'warn' if a.nivel_dependencia != 'Baja' else 'ok')}
        <br><small>Tel. {_seg.telefono(a.telefono, completo=True)}</small></div>""", unsafe_allow_html=True)

    sol = solicitudes_full()
    mias = sol[(sol.adulto_id == a.id) & sol.cuidador.notna() &
               sol.estatus.isin(["Asignada", "En curso"])].sort_values("fecha_solicitud")
    st.write("")
    if len(mias):
        s = mias.iloc[-1]
        st.markdown(f"<div class='vp-card'><h4>Cuidador asignado</h4>{s.cuidador}<br>"
                    f"{badge(s.estatus, 'ok')} <small>{s.tipo_servicio}</small></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='vp-card'><h4>Cuidador asignado</h4>Sin cuidador activo. "
                    "La coordinación puede asignarle uno (Matching Inteligente).</div>", unsafe_allow_html=True)
        if "matching" in _seg.PAGINAS_POR_ROL[_seg.rol()]:
            st.page_link("views/matching.py", label="Buscar cuidador", icon="🤝")

st.write("")
sem = act[act.fecha >= pd.Timestamp(date.today()) - pd.Timedelta(days=6)]
if len(sem):
    g = sem.groupby(sem.fecha.dt.date).completada.mean().mul(100).round(0).reset_index()
    g.columns = ["Fecha", "Cumplimiento (%)"]
    fig = px.bar(g, x="Fecha", y="Cumplimiento (%)", title="Cumplimiento de la agenda — últimos 7 días",
                 color_discrete_sequence=[TEAL])
    fig.update_yaxes(range=[0, 100])
    st.plotly_chart(style_fig(fig, 280), use_container_width=True)
