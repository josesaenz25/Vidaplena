import seguridad as _seg
_seg.requiere("mapa_interactivo")
import folium
import streamlit as st
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium

from core import (ESTATUS_ACTIVOS, TIPO_COLOR, TIPO_ICONO, kpi_row, load, mapa_base, page_header,
                  solicitudes_full, with_alcaldia)

page_header("Mapa Interactivo", "Adultos mayores, cuidadores, servicios y demanda activa sobre la CDMX", "🗺️")
ad = with_alcaldia(load("adultos"))
cu = with_alcaldia(load("cuidadores"))
sv = with_alcaldia(load("servicios"))
so = solicitudes_full()

alc = st.selectbox("Alcaldía", ["Toda la CDMX"] + sorted(ad.alcaldia.unique()))
t1, t2, t3, t4 = st.columns(4)
v_ad = t1.toggle("Adultos mayores", True)
v_cu = t2.toggle("Cuidadores", True)
v_sv = t3.toggle("Servicios", False)
v_hm = t4.toggle("Mapa de calor de demanda", True)

if alc != "Toda la CDMX":
    ad, cu, sv = ad[ad.alcaldia == alc], cu[cu.alcaldia == alc], sv[sv.alcaldia == alc]
    so = so[so.alcaldia == alc]
act = so[so.estatus.isin(ESTATUS_ACTIVOS)]
kpi_row([("Adultos", len(ad), "En el área", "blue"), ("Cuidadores", len(cu), f"{int(cu.disponible.sum())} disponibles", "teal"),
         ("Servicios", len(sv), "Salud y apoyo", "green"), ("Demanda activa", len(act), "Solicitudes abiertas", "amber")])
st.write("")

centro = (ad.lat.mean(), ad.lon.mean()) if len(ad) else (19.40, -99.14)
m = mapa_base(*centro, 11 if alc == "Toda la CDMX" else 13)
if v_hm and len(act):
    HeatMap(act[["a_lat", "a_lon"]].dropna().values.tolist(), radius=28, blur=22, name="Demanda").add_to(m)
if v_ad:
    g = MarkerCluster(name="Adultos mayores").add_to(m)
    for r in ad.itertuples():
        folium.Marker([r.lat, r.lon], tooltip=r.nombre, popup=f"<b>{r.nombre}</b><br>{r.edad} años · {r.condicion}",
                      icon=folium.Icon(color="blue", icon="user")).add_to(g)
if v_cu:
    g = folium.FeatureGroup(name="Cuidadores").add_to(m)
    for r in cu.itertuples():
        folium.CircleMarker([r.lat, r.lon], radius=7, color="#2E9E6B" if r.disponible else "#999999", fill=True,
                            fill_opacity=.9, tooltip=f"{r.nombre} · {r.especialidad}").add_to(g)
if v_sv:
    g = folium.FeatureGroup(name="Servicios").add_to(m)
    for r in sv.itertuples():
        folium.Marker([r.lat, r.lon], tooltip=f"{r.nombre} ({r.tipo})",
                      icon=folium.Icon(color=TIPO_COLOR[r.tipo], icon=TIPO_ICONO[r.tipo])).add_to(g)
folium.LayerControl().add_to(m)
st_folium(m, height=600, use_container_width=True, returned_objects=[])
st.caption("Cuidadores en verde = disponibles; en gris = ocupados. El mapa de calor muestra dónde está la demanda activa.")
