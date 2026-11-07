import seguridad as _seg
_seg.requiere("salud")
from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

from core import (BLUE, RED, TEAL, adulto_activo, badge, clasif_glucosa, clasif_presion,
                  insert_row, kpi, load, page_header, style_fig, tabla, ultima_lectura,
                  with_alcaldia)

page_header("Monitoreo de Salud", "Registro de signos vitales, medicamentos y bienestar", "❤️")
a = adulto_activo()
vit = load("signos_vitales")
mis = vit[vit.adulto_id == a.id].sort_values("fecha")
st.markdown(f"**{a.nombre}** · {a.edad} años · {a.condicion}")

if len(mis):
    u = mis.iloc[-1]
    tp, cp = clasif_presion(u.sistolica, u.diastolica)
    tg, cg = clasif_glucosa(u.glucosa)
    tone = {"ok": "green", "warn": "amber", "bad": "red"}
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("Presión arterial", f"{u.sistolica}/{u.diastolica}", f"mmHg · {badge(tp, cp)}", tone[cp])
    with c2: kpi("Glucosa", f"{u.glucosa}", f"mg/dL · {badge(tg, cg)}", tone[cg])
    with c3: kpi("Estado de ánimo", u.estado_animo, f"Registro: {u.fecha:%d/%m %H:%M}", "teal")
    with c4: kpi("Actividad", f"{u.actividad_min} min", "Última lectura", "blue")
    if "bad" in (cp, cg):
        st.warning("Lectura fuera de rango. Se recomienda contactar a su médico o cuidador. "
                   "Valores de referencia; no sustituyen una valoración médica.")
else:
    st.info("Aún no hay lecturas para este adulto mayor.")

st.write("")
left, right = st.columns([1, 2], gap="large")
with left:
    st.markdown("#### Registrar nuevo dato")
    with st.form("nuevo_signo", clear_on_submit=True):
        s1, s2 = st.columns(2)
        sis = s1.number_input("Sistólica", 60, 250, 120)
        dia = s2.number_input("Diastólica", 40, 150, 80)
        glu = st.number_input("Glucosa (mg/dL)", 30, 500, 95)
        animo = st.select_slider("Estado de ánimo", ["Bajo", "Regular", "Bien"], value="Bien")
        act_min = st.number_input("Actividad física (min)", 0, 300, 20)
        if st.form_submit_button("Registrar nuevo dato", type="primary"):
            insert_row("signos_vitales", adulto_id=int(a.id), fecha=datetime.now(), sistolica=int(sis),
                       diastolica=int(dia), glucosa=int(glu), estado_animo=animo, actividad_min=int(act_min))
            st.rerun()
with right:
    if len(mis) > 1:
        f1 = go.Figure()
        f1.add_scatter(x=mis.fecha, y=mis.sistolica, name="Sistólica", line=dict(color=BLUE, width=3))
        f1.add_scatter(x=mis.fecha, y=mis.diastolica, name="Diastólica", line=dict(color=TEAL, width=3))
        f1.add_hline(y=140, line_dash="dot", line_color=RED, annotation_text="Límite 140")
        f1.update_layout(title="Presión arterial")
        st.plotly_chart(style_fig(f1, 250), use_container_width=True)
        f2 = go.Figure()
        f2.add_scatter(x=mis.fecha, y=mis.glucosa, name="Glucosa", line=dict(color=BLUE, width=3))
        f2.add_hrect(y0=70, y1=140, fillcolor=TEAL, opacity=0.12, line_width=0)
        f2.update_layout(title="Glucosa (franja verde = rango esperado)")
        st.plotly_chart(style_fig(f2, 250), use_container_width=True)

with st.expander("Historial de registros"):
    h = mis.sort_values("fecha", ascending=False).head(20)[
        ["fecha", "sistolica", "diastolica", "glucosa", "estado_animo", "actividad_min"]]
    h.columns = ["Fecha", "Sistólica", "Diastólica", "Glucosa", "Ánimo", "Actividad (min)"]
    tabla(h)

if _seg.rol() != "coordinacion":
    st.stop()
st.markdown("#### Alertas del sistema — adultos con última lectura fuera de rango")
ul = ultima_lectura()
bad = ul[(ul.sistolica >= 140) | (ul.diastolica >= 90) | (ul.glucosa > 140) | (ul.glucosa < 70)]
ad = with_alcaldia(load("adultos"))[["id", "nombre", "alcaldia", "condicion", "telefono"]]
al = bad.merge(ad, left_on="adulto_id", right_on="id").sort_values("fecha", ascending=False)
if al.empty:
    st.success("Sin alertas activas.")
else:
    al["telefono"] = al["telefono"].map(lambda x: _seg.telefono(x, completo=True))
    t = al[["nombre", "alcaldia", "condicion", "sistolica", "diastolica", "glucosa", "telefono"]]
    t.columns = ["Adulto mayor", "Alcaldía", "Condición", "Sistólica", "Diastólica", "Glucosa", "Teléfono"]
    tabla(t.head(15))
