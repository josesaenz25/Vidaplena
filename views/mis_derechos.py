import json

import pandas as pd
import streamlit as st
from sqlalchemy import select

import seguridad as seg
from core import get_engine, load, metadata, page_header, tabla

seg.requiere("mis_derechos")
u = seg.usuario()
page_header("Mis derechos y privacidad", "Consentimiento, derechos ARCO, descarga de tus datos y contraseña", "🛡️")

t1, t2, t3, t4 = st.tabs(["Consentimiento", "Derechos ARCO", "Mis datos", "Contraseña"])

with t1:
    c = seg.consentimiento_vigente(u["id"])
    if c:
        st.success(f"Consentimiento vigente · aviso {c['version']} · aceptado el {pd.Timestamp(c['fecha']):%d/%m/%Y %H:%M}")
        st.write("Uso de datos anonimizados para estadísticas: **" + ("Sí" if c["finalidad_secundaria"] else "No") + "**")
        st.caption("Si revocas el consentimiento, se cerrará tu sesión y no podrás usar el sistema hasta aceptarlo de nuevo. "
                   "Para suprimir tus datos presenta una solicitud de Cancelación.")
        if st.button("Revocar mi consentimiento"):
            seg.revocar_consentimiento(u["id"])
            seg.cerrar_sesion(motivo="LOGOUT")
            st.rerun()
    else:
        st.warning("No hay consentimiento vigente.")

with t2:
    with st.form("arco", clear_on_submit=True):
        tipo = st.selectbox("Derecho que deseas ejercer", seg.TIPOS_ARCO)
        desc = st.text_area("Describe tu solicitud", max_chars=500,
                            help="No incluyas contraseñas ni datos de otras personas.")
        if st.form_submit_button("Enviar solicitud", type="primary"):
            if len(desc.strip()) < 10:
                st.warning("Describe brevemente tu solicitud (mínimo 10 caracteres).")
            else:
                folio = seg.crear_arco(u["id"], tipo, desc.strip())
                st.success(f"Solicitud registrada con folio **{folio}**.")
    a = load("solicitudes_arco")
    a = a[a.usuario_id == u["id"]].sort_values("fecha", ascending=False)
    if len(a):
        v = a[["folio", "tipo", "estatus", "fecha", "fecha_limite", "respuesta"]].copy()
        v.columns = ["Folio", "Derecho", "Estatus", "Fecha", "Fecha límite", "Respuesta"]
        tabla(v)

with t3:
    st.write("Descarga una copia de los datos que el sistema guarda de tu cuenta"
             + (" y de la persona a la que das seguimiento." if u.get("adulto_id") else "."))
    datos = seg.exportar_mis_datos(u["id"])
    st.download_button("Descargar mis datos (JSON)", json.dumps(datos, ensure_ascii=False, indent=2).encode("utf-8"),
                       "mis_datos_vidaplena.json", "application/json")

with t4:
    with st.form("pw", clear_on_submit=True):
        actual = st.text_input("Contraseña actual", type="password")
        nueva = st.text_input("Contraseña nueva", type="password", help="Mínimo 10 caracteres, con mayúsculas, minúsculas y números.")
        if st.form_submit_button("Cambiar contraseña"):
            err = seg.cambiar_password(u["id"], actual, nueva)
            st.error(err) if err else st.success("Contraseña actualizada.")
