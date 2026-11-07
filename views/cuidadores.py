import seguridad as _seg
_seg.requiere("cuidadores")
from datetime import datetime
import random

import streamlit as st

from core import (ESPECIALIDADES, adulto_activo, badge, estrellas, insert_row,
                  kpi_row, load, page_header, with_alcaldia)

ESP_SERVICIO = {"Geriatría": "Apoyo en actividades diarias", "Enfermería": "Enfermería a domicilio",
                "Fisioterapia": "Fisioterapia", "Cuidado de demencia": "Cuidado de demencia",
                "Acompañamiento": "Acompañamiento"}

page_header("Cuidadores disponibles", "Catálogo de la red de cuidadores y solicitud directa", "🧑‍⚕️")
a = adulto_activo()
cu = with_alcaldia(load("cuidadores"))

tab1, tab2 = st.tabs(["Catálogo", "Registrar cuidador"])

with tab1:
    f1, f2, f3, f4 = st.columns([1.3, 1.3, 1, 1])
    alc = f1.selectbox("Alcaldía", ["Todas"] + sorted(cu.alcaldia.unique()))
    esp = f2.selectbox("Especialidad", ["Todas"] + ESPECIALIDADES)
    cal = f3.slider("Calificación mínima", 3.0, 5.0, 3.5, 0.1)
    solo = f4.toggle("Solo disponibles", value=True)
    q = st.text_input("Buscar cuidador", placeholder="Nombre…")

    d = cu[cu.calificacion >= cal]
    if alc != "Todas": d = d[d.alcaldia == alc]
    if esp != "Todas": d = d[d.especialidad == esp]
    if solo: d = d[d.disponible]
    if q: d = d[d.nombre.str.contains(q, case=False)]
    d = d.sort_values("calificacion", ascending=False)

    kpi_row([("Cuidadores encontrados", len(d), "Con los filtros actuales", "blue"),
             ("Calificación promedio", f"{d.calificacion.mean():.1f}" if len(d) else "—", "De 5.0", "amber"),
             ("Tarifa promedio", f"${d.tarifa_hora.mean():.0f}/h" if len(d) else "—", "MXN", "teal")])
    st.write("")

    por_pag = 9
    paginas = max(1, -(-len(d) // por_pag))
    pag = st.number_input("Página", 1, paginas, 1) if paginas > 1 else 1
    vista = d.iloc[(pag - 1) * por_pag: pag * por_pag]
    for fila in range(0, len(vista), 3):
        cols = st.columns(3)
        for col, r in zip(cols, vista.iloc[fila: fila + 3].itertuples()):
            with col, st.container(border=True):
                st.markdown(f"**{r.nombre}**")
                st.markdown(f"{r.alcaldia} · {r.especialidad}<br>"
                            f"<span style='color:#F2A93B'>{estrellas(r.calificacion)}</span> {r.calificacion} · "
                            f"{r.experiencia_anios} años · ${r.tarifa_hora:.0f}/h<br>"
                            f"{badge('Disponible' if r.disponible else 'Ocupado', 'ok' if r.disponible else 'warn')}",
                            unsafe_allow_html=True)
                if st.button(f"Solicitar para {a.nombre.split()[0]}", key=f"sol_{r.id}", disabled=not r.disponible):
                    ahora = datetime.now()
                    insert_row("solicitudes", adulto_id=int(a.id), cuidador_id=int(r.id),
                               fecha_solicitud=ahora, fecha_asignacion=ahora,
                               tipo_servicio=ESP_SERVICIO.get(r.especialidad, "Acompañamiento"),
                               prioridad="Media", estatus="Asignada", notas="Solicitud directa desde el catálogo")
                    st.toast(f"Solicitud creada: {r.nombre} → {a.nombre}", icon="✅")

with tab2:
    al = load("alcaldias")
    with st.form("nuevo_cuidador", clear_on_submit=True):
        n1, n2 = st.columns(2)
        nombre = n1.text_input("Nombre completo")
        tel = n2.text_input("Teléfono")
        alc_n = n1.selectbox("Alcaldía", al.nombre.tolist())
        esp_n = n2.selectbox("Especialidad", ESPECIALIDADES)
        exp = n1.number_input("Años de experiencia", 0, 50, 3)
        tar = n2.number_input("Tarifa por hora (MXN)", 50, 500, 120, 10)
        if st.form_submit_button("Registrar cuidador", type="primary"):
            if nombre.strip():
                z = al[al.nombre == alc_n].iloc[0]
                insert_row("cuidadores", nombre=nombre.strip(), alcaldia_id=int(z.id), especialidad=esp_n,
                           experiencia_anios=int(exp), calificacion=4.0, tarifa_hora=float(tar), disponible=True,
                           telefono=_seg.cifrar(tel.strip()[:30]), lat=float(z.lat) + random.uniform(-.02, .02),
                           lon=float(z.lon) + random.uniform(-.02, .02))
                st.success("Cuidador registrado y disponible para el matching.")
                st.rerun()
            else:
                st.warning("Escribe el nombre.")
