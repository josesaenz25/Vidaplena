import seguridad as _seg
_seg.requiere("dashboard")
import io
import zipfile
from datetime import datetime, timedelta

import plotly.express as px
import streamlit as st

from core import (BLUE, ESTATUS_ACTIVOS, TEAL, horas_respuesta, kpi_row, load, metadata, page_header,
                  solicitudes_full, style_fig, ultima_lectura)

page_header("Dashboard Ejecutivo", "Indicadores clave del programa para la toma de decisiones", "📊")
s = solicitudes_full()
ad, cu, act = load("adultos"), load("cuidadores"), load("actividades")
ahora = datetime.now()

ult30 = s[s.fecha_solicitud >= ahora - timedelta(days=30)]
prev30 = s[(s.fecha_solicitud < ahora - timedelta(days=30)) & (s.fecha_solicitud >= ahora - timedelta(days=60))]
delta = len(ult30) - len(prev30)
atendidos = s[s.estatus.isin(["Asignada", "En curso", "Completada"])].adulto_id.nunique()
ul = ultima_lectura()
alertas = int(((ul.sistolica >= 140) | (ul.diastolica >= 90) | (ul.glucosa > 140) | (ul.glucosa < 70)).sum())
cumpl = act[act.fecha.dt.date >= (ahora - timedelta(days=7)).date()].completada.mean()
resp = horas_respuesta(s)

kpi_row([("Cobertura", f"{atendidos / len(ad):.0%}", f"{atendidos} de {len(ad)} adultos con servicio", "blue"),
         ("Solicitudes 30 días", len(ult30), f"{'▲' if delta >= 0 else '▼'} {abs(delta)} vs. 30 días previos", "amber"),
         ("Tiempo de respuesta", f"{resp.mean():.1f} h", f"Mediana {resp.median():.1f} h", "teal"),
         ("Cumplimiento de agenda", f"{cumpl:.0%}", "Últimos 7 días", "green"),
         ("Alertas de salud", alertas, "Última lectura fuera de rango", "red"),
         ("Calificación de cuidadores", f"{cu.calificacion.mean():.1f}/5", f"{int(cu.disponible.sum())} disponibles", "blue")])
st.write("")

c1, c2 = st.columns([1.6, 1])
sem = s.set_index("fecha_solicitud").resample("W").size().reset_index(name="Solicitudes")
c1.plotly_chart(style_fig(px.area(sem, x="fecha_solicitud", y="Solicitudes", title="Solicitudes por semana",
                                  color_discrete_sequence=[BLUE]).update_layout(xaxis_title="")), use_container_width=True)
est = s.groupby("estatus").size().reset_index(name="n")
c2.plotly_chart(style_fig(px.pie(est, names="estatus", values="n", hole=.55, title="Solicitudes por estatus")),
                use_container_width=True)

c3, c4 = st.columns(2)
top = s.groupby("alcaldia").size().reset_index(name="Solicitudes").sort_values("Solicitudes").tail(8)
c3.plotly_chart(style_fig(px.bar(top, x="Solicitudes", y="alcaldia", orientation="h", title="Alcaldías con mayor demanda",
                                 color_discrete_sequence=[TEAL]).update_layout(yaxis_title="")), use_container_width=True)
cond = s.groupby("tipo_servicio").size().reset_index(name="n").sort_values("n")
c4.plotly_chart(style_fig(px.bar(cond, x="n", y="tipo_servicio", orientation="h", title="Servicios más solicitados",
                                 color_discrete_sequence=[BLUE]).update_layout(xaxis_title="Solicitudes", yaxis_title="")),
                use_container_width=True)

pend = int((s.estatus == "Pendiente").sum())
alta = int(((s.prioridad == "Alta") & s.estatus.isin(ESTATUS_ACTIVOS)).sum())
st.markdown("#### Resumen ejecutivo")
st.info(f"• Se atiende al **{atendidos / len(ad):.0%}** de los adultos mayores registrados.\n\n"
        f"• Hay **{pend}** solicitudes pendientes y **{alta}** activas con prioridad alta.\n\n"
        f"• **{alertas}** adultos mayores tienen su última lectura de salud fuera de rango y requieren seguimiento.\n\n"
        f"• La demanda de los últimos 30 días {'subió' if delta >= 0 else 'bajó'} {abs(delta)} solicitudes frente al periodo previo.")

buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as z:
    for n in metadata.tables:
        z.writestr(f"{n}.csv", load(n).to_csv(index=False))
st.download_button("⬇️ Exportar datos para Power BI (ZIP de CSV)", buf.getvalue(), "vidaplena_datos.zip", "application/zip")
