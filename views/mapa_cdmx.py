import seguridad as _seg
_seg.requiere("mapa_cdmx")
import folium
import streamlit as st
from streamlit_folium import st_folium

from core import (BLUE, TIPO_COLOR, TIPO_ICONO, TIPOS_SERVICIO, adulto_activo, haversine,
                  kpi_row, load, mapa_base, page_header, tabla, with_alcaldia)

page_header("Servicios cercanos — Mapa CDMX",
            "Centros de salud, farmacias, programas sociales y centros de día cerca del adulto mayor", "📍")
a = adulto_activo()
serv = with_alcaldia(load("servicios"))
serv["distancia_km"] = haversine(a.lat, a.lon, serv.lat.values, serv.lon.values).round(1)

f1, f2, f3 = st.columns([2, 1, 2])
tipos = f1.multiselect("Tipo de servicio", TIPOS_SERVICIO, default=TIPOS_SERVICIO)
radio = f2.slider("Radio (km)", 1, 25, 8)
q = f3.text_input("Buscar por nombre o alcaldía", placeholder="Ej. Coyoacán")

sel = serv[serv.tipo.isin(tipos) & (serv.distancia_km <= radio)]
if q:
    m = sel.nombre.str.contains(q, case=False) | sel.alcaldia.str.contains(q, case=False)
    sel = sel[m]
sel = sel.sort_values("distancia_km")

kpi_row([("Servicios en el radio", len(sel), f"Alrededor de {a.nombre.split()[0]}", "blue"),
         ("Más cercano", f"{sel.distancia_km.min():.1f} km" if len(sel) else "—",
          sel.iloc[0].nombre if len(sel) else "Amplía el radio", "teal")])
st.write("")

zoom = 14 if radio <= 3 else 13 if radio <= 7 else 12 if radio <= 14 else 11
m = mapa_base(a.lat, a.lon, zoom)
folium.Marker([a.lat, a.lon], tooltip=f"{a.nombre} (domicilio)",
              icon=folium.Icon(color="darkblue", icon="home")).add_to(m)
folium.Circle([a.lat, a.lon], radius=radio * 1000, color=BLUE, fill=True, fill_opacity=0.04).add_to(m)
for r in sel.itertuples():
    folium.Marker([r.lat, r.lon], tooltip=f"{r.nombre} · {r.distancia_km} km",
                  popup=f"<b>{r.nombre}</b><br>{r.tipo}<br>{r.direccion}<br>Tel. {r.telefono}",
                  icon=folium.Icon(color=TIPO_COLOR[r.tipo], icon=TIPO_ICONO[r.tipo])).add_to(m)
st_folium(m, height=520, use_container_width=True, returned_objects=[])

t = sel[["nombre", "tipo", "alcaldia", "direccion", "telefono", "distancia_km"]]
t.columns = ["Servicio", "Tipo", "Alcaldía", "Dirección", "Teléfono", "Distancia (km)"]
tabla(t)
