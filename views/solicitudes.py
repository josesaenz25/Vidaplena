import seguridad as _seg
_seg.requiere("solicitudes")
from datetime import datetime

import streamlit as st

from core import (ESTATUS, ESTATUS_ACTIVOS, PRIORIDADES, SERVICIOS_SOL, insert_row, kpi_row, load,
                  page_header, solicitudes_full, tabla, update_row)

page_header("Solicitudes", "Bandeja de solicitudes de cuidado: creación, asignación y seguimiento", "📝")
s = solicitudes_full()
cu = load("cuidadores")
ad = load("adultos")
ad = ad[ad.id.isin(_seg.permitidos_adultos())]
es_coord = _seg.rol() == "coordinacion"

kpi_row([("Pendientes", int((s.estatus == "Pendiente").sum()), "Esperan asignación", "red"),
         ("Asignadas", int((s.estatus == "Asignada").sum()), "Cuidador definido", "amber"),
         ("En curso", int((s.estatus == "En curso").sum()), "Atención activa", "blue"),
         ("Completadas", int((s.estatus == "Completada").sum()), "Servicio finalizado", "green")])
st.write("")

if not len(ad):
    st.info("No tiene personas asignadas por ahora.")
    st.stop()
tabs = st.tabs(["Bandeja", "Nueva solicitud"] + (["Gestionar"] if es_coord else []))
tab1, tab2 = tabs[0], tabs[1]
tab3 = tabs[2] if es_coord else None

with tab1:
    f1, f2, f3 = st.columns(3)
    est = f1.multiselect("Estatus", ESTATUS, default=ESTATUS_ACTIVOS)
    pri = f2.multiselect("Prioridad", PRIORIDADES, default=PRIORIDADES)
    alc = f3.selectbox("Alcaldía", ["Todas"] + sorted(s.alcaldia.dropna().unique()))
    d = s[s.estatus.isin(est) & s.prioridad.isin(pri)]
    if alc != "Todas":
        d = d[d.alcaldia == alc]
    t = d.sort_values("fecha_solicitud", ascending=False)[
        ["id", "fecha_solicitud", "adulto", "alcaldia", "tipo_servicio", "prioridad", "estatus", "cuidador"]]
    t.columns = ["Folio", "Fecha", "Adulto mayor", "Alcaldía", "Servicio", "Prioridad", "Estatus", "Cuidador"]
    tabla(t)
    st.download_button("Descargar CSV", t.to_csv(index=False).encode("utf-8"), "solicitudes.csv", "text/csv")

with tab2:
    if _seg.rol() == "cuidador":
        st.info("Las nuevas solicitudes las crean la coordinación o la familia.")
        st.stop()
    with st.form("nueva_sol", clear_on_submit=True):
        nombres = dict(zip(ad.id, ad.nombre))
        n1, n2 = st.columns(2)
        aid = n1.selectbox("Adulto mayor", list(nombres), format_func=lambda i: nombres[i],
                           index=list(nombres).index(st.session_state.get("adulto_id", ad.id.iloc[0])))
        tipo = n2.selectbox("Servicio requerido", SERVICIOS_SOL)
        prio = n1.selectbox("Prioridad", PRIORIDADES, index=1)
        nota = n2.text_input("Notas")
        if st.form_submit_button("Crear solicitud", type="primary"):
            insert_row("solicitudes", adulto_id=int(aid), fecha_solicitud=datetime.now(), tipo_servicio=tipo,
                       prioridad=prio, estatus="Pendiente", notas=nota.strip()[:250])
            st.success("Solicitud creada en estatus Pendiente. La coordinación le asignará un cuidador.")
            st.rerun()

if tab3 is not None:
  with tab3:
      abiertas = s[s.estatus.isin(ESTATUS_ACTIVOS)].sort_values("fecha_solicitud", ascending=False)
      if abiertas.empty:
          st.info("No hay solicitudes abiertas.")
      else:
          lab = {int(r.id): f"#{r.id} · {r.adulto} · {r.tipo_servicio} · {r.estatus}" for r in abiertas.itertuples()}
          sid = st.selectbox("Solicitud", list(lab), format_func=lambda i: lab[i])
          r = s[s.id == sid].iloc[0]
          disp = cu[cu.disponible | (cu.id == r.cuidador_id)]
          nom = {int(i): n for i, n in zip(disp.id, disp.nombre)}
          opciones = [0] + list(nom)
          actual = int(r.cuidador_id) if r.cuidador_id == r.cuidador_id else 0
          g1, g2 = st.columns(2)
          nuevo_est = g1.selectbox("Estatus", ESTATUS, index=ESTATUS.index(r.estatus))
          nuevo_cu = g2.selectbox("Cuidador", opciones, index=opciones.index(actual),
                                  format_func=lambda i: "— Sin asignar —" if i == 0 else nom[i])
          if st.button("Guardar cambios", type="primary"):
              vals = dict(estatus=nuevo_est, cuidador_id=nuevo_cu or None)
              if nuevo_cu and r.fecha_asignacion != r.fecha_asignacion:   # NaT
                  vals["fecha_asignacion"] = datetime.now()
              if nuevo_est in ("Asignada", "En curso", "Completada") and not nuevo_cu:
                  st.error("Para ese estatus debes elegir un cuidador.")
              else:
                  update_row("solicitudes", sid, **vals)
                  st.success("Solicitud actualizada.")
                  st.rerun()
