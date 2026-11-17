import seguridad as _seg
_seg.requiere("observatorio")
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

import poblacion
from core import (BLUE, ESTATUS_ACTIVOS, TEAL, TODA, enlaces_rapidos, foco_alcaldia, horas_respuesta,
                  kpi_row, load, page_header, style_fig, tabla, with_alcaldia)

page_header("Observatorio de Datos", "Estadísticas e indicadores para identificar necesidades y mejorar los programas", "🔎")
ad = with_alcaldia(load("adultos"))
cu = with_alcaldia(load("cuidadores"))
so = load("solicitudes")

todas = sorted(ad.alcaldia.unique())
_foco = foco_alcaldia()
sel = st.multiselect("Filtrar por alcaldía", todas, default=[_foco] if _foco in todas else todas)
if len(sel) == 1:
    st.session_state["alc_foco"] = sel[0]
elif len(sel) == len(todas):
    st.session_state["alc_foco"] = TODA
ad = ad[ad.alcaldia.isin(sel)]
cu = cu[cu.alcaldia.isin(sel)]
so = so[so.adulto_id.isin(ad.id)]
if ad.empty:
    st.warning("Selecciona al menos una alcaldía.")
    st.stop()

kpi_row([("Adultos registrados", f"{len(ad):,}", f"Edad promedio {ad.edad.mean():.0f} años", "blue"),
         ("Cuidadores disponibles", int(cu.disponible.sum()), f"de {len(cu)} registrados", "teal"),
         ("Solicitudes activas", int(so.estatus.isin(ESTATUS_ACTIVOS).sum()), f"{len(so)} en total", "amber"),
         ("Tiempo de respuesta", f"{horas_respuesta(so).mean():.1f} h", "Promedio solicitud → asignación", "green")])
st.write("")

c1, c2 = st.columns([1.3, 1])
g = ad.groupby("alcaldia").size().reset_index(name="Adultos").sort_values("Adultos")
c1.plotly_chart(style_fig(px.bar(g, x="Adultos", y="alcaldia", orientation="h",
                                 title="Adultos mayores por alcaldía", color_discrete_sequence=[BLUE]).update_yaxes(title=""), 420),
                use_container_width=True)
c2.plotly_chart(style_fig(px.pie(ad, names="condicion", hole=.55, title="Condición de salud principal"), 420),
                use_container_width=True)

c3, c4 = st.columns(2)
c3.plotly_chart(style_fig(px.histogram(ad, x="edad", nbins=14, title="Distribución por edad",
                                       color_discrete_sequence=[TEAL]).update_layout(bargap=.05)), use_container_width=True)
dep = ad.groupby(["nivel_dependencia"]).size().reset_index(name="n")
c4.plotly_chart(style_fig(px.bar(dep, x="nivel_dependencia", y="n", title="Nivel de dependencia",
                                 category_orders={"nivel_dependencia": ["Baja", "Media", "Alta"]},
                                 color_discrete_sequence=[BLUE]).update_layout(xaxis_title="", yaxis_title="Adultos")),
                use_container_width=True)

# Brecha demanda / oferta
oferta = cu[cu.disponible].groupby("alcaldia").size().rename("disp")
brecha = ad.groupby("alcaldia").size().rename("adultos").to_frame().join(oferta).fillna(0)
brecha["Adultos por cuidador disponible"] = brecha.adultos / brecha.disp.replace(0, np.nan)
brecha["Adultos por cuidador disponible"] = brecha["Adultos por cuidador disponible"].fillna(brecha.adultos).astype(float)
brecha = brecha.reset_index().sort_values("Adultos por cuidador disponible", ascending=False)
c5, c6 = st.columns(2)
c5.plotly_chart(style_fig(px.bar(brecha, x="alcaldia", y="Adultos por cuidador disponible",
                                 title="Brecha entre demanda y oferta de cuidado",
                                 color_discrete_sequence=[BLUE]).update_layout(xaxis_title="")), use_container_width=True)
tipo = so.groupby("tipo_servicio").size().reset_index(name="n").sort_values("n")
c6.plotly_chart(style_fig(px.bar(tipo, x="n", y="tipo_servicio", orientation="h", title="Solicitudes por tipo de servicio",
                                 color_discrete_sequence=[TEAL]).update_layout(xaxis_title="Solicitudes", yaxis_title="")),
                use_container_width=True)

mes = so.set_index("fecha_solicitud").resample("MS").size().reset_index(name="Solicitudes")
st.plotly_chart(style_fig(px.line(mes, x="fecha_solicitud", y="Solicitudes", markers=True,
                                  title="Tendencia mensual de solicitudes").update_layout(xaxis_title="")),
                use_container_width=True)

st.markdown("#### Contexto demográfico: población de 60+ en la CDMX")
ref = poblacion.con_cobertura(with_alcaldia(load("adultos")).groupby("alcaldia").size())
ref_sel = ref[ref.alcaldia.isin(sel)]
k1, k2, k3 = st.columns(3)
k1.metric("60+ estimados (alcaldías elegidas)", f"{int(ref_sel.pob60_est.sum()):,}")
k2.metric("Registrados en VidaPlena", f"{int(ref_sel.registrados.sum()):,}")
k3.metric("Muestra piloto por 10,000 personas 60+", f"{ref_sel.registrados.sum() / ref_sel.pob60_est.sum() * 10000:.1f}")
d1, d2 = st.columns(2)
d1.plotly_chart(style_fig(px.bar(ref_sel.sort_values("pob60_est"), x="pob60_est", y="alcaldia", orientation="h",
                                 title="Población 60+ estimada por alcaldía", color_discrete_sequence=[BLUE])
                          .update_layout(xaxis_title="Personas (aprox.)", yaxis_title="")), use_container_width=True)
d2.plotly_chart(style_fig(px.bar(ref_sel.sort_values("pct65_2020"), x="pct65_2020", y="alcaldia", orientation="h",
                                 title="Proporción de 65+ (Censo 2020, INEGI)", color_discrete_sequence=[TEAL])
                          .update_layout(xaxis_title="% de la población", yaxis_title="")), use_container_width=True)
t = ref_sel.sort_values("pob60_est", ascending=False)[
    ["alcaldia", "pob60_est", "rank_numero", "pob_total_2020", "pct65_2020", "rank_proporcion", "registrados", "por_10mil"]]
t.columns = ["Alcaldía", "60+ estimados", "Lugar por número", "Población total 2020", "% 65+ (2020)",
             "Lugar por proporción", "Registrados en VidaPlena", "Registrados por 10,000 60+"]
tabla(t)
st.caption(f"Fuente: {poblacion.FUENTE} Población total y % de 65+: INEGI, Panorama sociodemográfico de Ciudad de México 2020. "
           f"Total CDMX (60+ estimado): {poblacion.TOTAL_60:,}.")
enlaces_rapidos([("mapa_interactivo", "views/mapa_interactivo.py", "Ver en el mapa", "🗺️"),
                 ("cuidadores", "views/cuidadores.py", "Cuidadores", "👥"),
                 ("solicitudes", "views/solicitudes.py", "Solicitudes", "📝"),
                 ("dashboard", "views/dashboard.py", "Dashboard Ejecutivo", "📊")])

top = g.iloc[-1]
peor = brecha.iloc[0]
st.markdown("#### Hallazgos")
st.info(f"• **{top.alcaldia}** concentra la mayor población registrada ({int(top.Adultos)} adultos mayores).\n\n"
        f"• **{peor.alcaldia}** presenta la mayor brecha: {peor['Adultos por cuidador disponible']:.1f} adultos por cuidador disponible.\n\n"
        f"• {(ad.nivel_dependencia == 'Alta').mean():.0%} de los adultos mayores tiene dependencia alta y requiere atención prioritaria.")
