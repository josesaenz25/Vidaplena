from datetime import date

import streamlit as st

import seguridad as seg
from core import kpi_row, load, page_header, tabla

seg.requiere("gestion_arco")
page_header("Gestión de solicitudes ARCO", "Atención de derechos de las personas titulares", "📬")
a = load("solicitudes_arco")
us = load("usuarios")[["id", "nombre", "rol"]].rename(columns={"id": "usuario_id", "nombre": "titular"})
a = a.merge(us, on="usuario_id", how="left")
abiertas = a[a.estatus.isin(["Recibida", "En revisión"])]
vencidas = abiertas[abiertas.fecha_limite.dt.date < date.today()] if len(abiertas) else abiertas
kpi_row([("Recibidas", len(a), "Total", "blue"), ("Abiertas", len(abiertas), "Por atender", "amber"),
         ("Vencidas", len(vencidas), "Pasaron su fecha límite", "red"),
         ("Atendidas", int((a.estatus == "Atendida").sum()), "Resueltas", "green")])
st.write("")
if a.empty:
    st.info("Aún no hay solicitudes ARCO.")
    st.stop()
v = a.sort_values("fecha", ascending=False)[["id", "folio", "titular", "tipo", "estatus", "fecha", "fecha_limite", "descripcion"]]
tabla(v.drop(columns="id"))
st.markdown("#### Responder")
opciones = {int(r.id): f"{r.folio} · {r.titular} · {r.tipo} · {r.estatus}" for r in a.itertuples()}
sid = st.selectbox("Solicitud", list(opciones), format_func=lambda i: opciones[i])
est = st.selectbox("Estatus", ["Recibida", "En revisión", "Atendida", "Rechazada"])
resp = st.text_area("Respuesta al titular", max_chars=500)
if st.button("Guardar respuesta", type="primary"):
    if est in ("Atendida", "Rechazada") and len(resp.strip()) < 5:
        st.error("Escribe la respuesta (si se rechaza, indica el motivo).")
    else:
        seg.resolver_arco(sid, est, resp.strip())
        st.success("Actualizado y registrado en la bitácora.")
        st.rerun()
