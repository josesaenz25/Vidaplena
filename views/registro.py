import seguridad as _seg
_seg.requiere("registro")
import random
import re
from datetime import datetime

import streamlit as st

from core import (CONDICIONES, ESPECIALIDADES, PRIORIDADES, SERVICIOS_SOL, enlaces_rapidos, insert_row,
                  kpi_row, load, page_header, tabla, with_alcaldia)

page_header("Registro", "Alta de adultos mayores, cuidadores y nuevas solicitudes de cuidado", "➕")

al = load("alcaldias")
adultos, cuid = load("adultos"), load("cuidadores")
kpi_row([("Adultos registrados", f"{len(adultos):,}", "Personas en seguimiento", "blue"),
         ("Cuidadores registrados", f"{len(cuid):,}", f"{int(cuid.disponible.sum())} disponibles", "teal")])
st.write("")


def _tel_ok(t: str) -> bool:
    return len(re.sub(r"\D", "", t)) in (10, 12, 13)


def _ubicar(alc: str):
    z = al[al.nombre == alc].iloc[0]       # sin dirección exacta: se ubica en la alcaldía (zona aproximada)
    return (int(z.id), float(z.lat) + random.uniform(-.02, .02), float(z.lon) + random.uniform(-.02, .02))


def _duplicado(df, nombre, aid) -> bool:
    return bool(((df.nombre.str.lower().str.strip() == nombre.lower().strip()) & (df.alcaldia_id == aid)).any())


t1, t2, t3 = st.tabs(["Adulto mayor", "Cuidador", "Nueva solicitud"])

with t1:
    st.caption("Los datos de salud son datos personales sensibles: registra solo con consentimiento expreso por escrito "
               "de la persona o su representante. El teléfono se guarda cifrado.")
    with st.form("alta_adulto", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Nombre completo *")
        edad = c2.number_input("Edad *", 60, 110, 70)
        sexo = c1.selectbox("Sexo", ["F", "M"], format_func=lambda x: "Mujer" if x == "F" else "Hombre")
        alc = c2.selectbox("Alcaldía *", al.nombre.sort_values().tolist())
        tel = c1.text_input("Teléfono (10 dígitos)")
        cond = c2.selectbox("Condición de salud principal", CONDICIONES)
        nivel = c1.selectbox("Nivel de dependencia", ["Baja", "Media", "Alta"])
        cons = st.checkbox("Cuento con el consentimiento expreso por escrito de la persona (o su representante) *")
        if st.form_submit_button("Registrar adulto mayor", type="primary"):
            aid, la, lo = _ubicar(alc)
            if len(nombre.strip()) < 5:
                st.warning("Escribe el nombre completo.")
            elif tel.strip() and not _tel_ok(tel):
                st.warning("El teléfono debe tener 10 dígitos.")
            elif not cons:
                st.warning("Es necesario confirmar el consentimiento.")
            elif _duplicado(adultos, nombre, aid):
                st.warning("Ya existe una persona con ese nombre en esa alcaldía.")
            else:
                nuevo = insert_row("adultos", nombre=nombre.strip(), edad=int(edad), sexo=sexo, alcaldia_id=aid,
                                   telefono=_seg.cifrar(tel.strip()[:30]), condicion=cond,
                                   nivel_dependencia=nivel, lat=la, lon=lo)
                st.session_state["_nuevo_adulto"] = (int(nuevo), nombre.strip())
                st.rerun()
    if "_nuevo_adulto" in st.session_state:
        nid, nn = st.session_state["_nuevo_adulto"]
        st.success(f"✅ {nn} fue registrado (ID {nid}). Ya aparece en mapas, observatorio y solicitudes.")

with t2:
    with st.form("alta_cuidador", clear_on_submit=True):
        n1, n2 = st.columns(2)
        nombre_c = n1.text_input("Nombre completo *")
        tel_c = n2.text_input("Teléfono (10 dígitos)")
        alc_c = n1.selectbox("Alcaldía *", al.nombre.sort_values().tolist(), key="alc_c")
        esp = n2.selectbox("Especialidad", ESPECIALIDADES)
        exp = n1.number_input("Años de experiencia", 0, 50, 3)
        tar = n2.number_input("Tarifa por hora (MXN)", 50, 500, 120, 10)
        if st.form_submit_button("Registrar cuidador", type="primary"):
            aid, la, lo = _ubicar(alc_c)
            if len(nombre_c.strip()) < 5:
                st.warning("Escribe el nombre completo.")
            elif tel_c.strip() and not _tel_ok(tel_c):
                st.warning("El teléfono debe tener 10 dígitos.")
            elif _duplicado(cuid, nombre_c, aid):
                st.warning("Ya existe un cuidador con ese nombre en esa alcaldía.")
            else:
                insert_row("cuidadores", nombre=nombre_c.strip(), alcaldia_id=aid, especialidad=esp,
                           experiencia_anios=int(exp), calificacion=4.0, tarifa_hora=float(tar), disponible=True,
                           telefono=_seg.cifrar(tel_c.strip()[:30]), lat=la, lon=lo)
                st.success("Cuidador registrado y disponible para el matching.")
                st.rerun()

with t3:
    ad_ = with_alcaldia(adultos).sort_values("nombre")
    if ad_.empty:
        st.info("Primero registra un adulto mayor.")
    else:
        etiqueta = {int(r.id): f"{r.nombre} · {r.alcaldia}" for r in ad_.itertuples()}
        with st.form("alta_solicitud", clear_on_submit=True):
            s1, s2 = st.columns(2)
            ids = list(etiqueta)
            pre = st.session_state.get("_nuevo_adulto", (None,))[0]
            persona = s1.selectbox("Adulto mayor", ids, index=ids.index(pre) if pre in ids else 0,
                                   format_func=lambda i: etiqueta[i])
            serv = s2.selectbox("Servicio requerido", SERVICIOS_SOL)
            prio = s1.selectbox("Prioridad", PRIORIDADES, index=1)
            notas = s2.text_input("Notas")
            if st.form_submit_button("Crear solicitud", type="primary"):
                insert_row("solicitudes", adulto_id=int(persona), cuidador_id=None, fecha_solicitud=datetime.now(),
                           fecha_asignacion=None, tipo_servicio=serv, prioridad=prio, estatus="Pendiente",
                           notas=notas.strip()[:200])
                st.success("Solicitud creada en estado Pendiente. Asígnala desde Matching Inteligente o Solicitudes.")

st.markdown("#### Últimos adultos registrados")
rec = with_alcaldia(adultos).sort_values("id", ascending=False).head(8)[["id", "nombre", "edad", "alcaldia", "condicion", "nivel_dependencia"]]
rec.columns = ["ID", "Nombre", "Edad", "Alcaldía", "Condición", "Dependencia"]
tabla(rec)
enlaces_rapidos([("matching", "views/matching.py", "Matching Inteligente", "🤝"),
                 ("solicitudes", "views/solicitudes.py", "Solicitudes", "📝"),
                 ("cuidadores", "views/cuidadores.py", "Cuidadores", "👥"),
                 ("mapa_interactivo", "views/mapa_interactivo.py", "Mapa Interactivo", "🗺️")])
