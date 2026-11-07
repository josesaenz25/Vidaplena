"""Texto del Aviso de Privacidad Integral y pantalla de consentimiento.

AVISO: es una PLANTILLA para un proyecto académico con datos sintéticos. Antes de operar con personas reales
debe revisarlo un profesional del derecho y completarse (responsable, domicilio, contacto, transferencias).
"""
import streamlit as st

import seguridad as seg

RESPONSABLE = "VidaPlena CDMX"
DOMICILIO = "UNRC Santo Tomás"
CONTACTO = "privacidad@vidaplena.com.mx"

DATOS = {
    "Identificación y contacto": "nombre, edad, sexo, teléfono, alcaldía y ubicación aproximada del domicilio.",
    "Datos personales sensibles (salud)": "condición de salud, nivel de dependencia, presión arterial, glucosa, "
                                           "estado de ánimo, actividad física y agenda de medicamentos.",
    "Datos de cuidadores": "nombre, teléfono, especialidad, experiencia, calificación, tarifa y disponibilidad.",
    "Datos de uso de la cuenta": "usuario, rol, fechas de acceso y bitácora de acciones realizadas.",
}
FINALIDADES_PRIMARIAS = [
    "Registrar a la persona adulta mayor y administrar su programa de cuidados.",
    "Recibir, asignar y dar seguimiento a solicitudes de cuidado (matching con cuidadores).",
    "Monitorear signos vitales y generar alertas para su familia o cuidador.",
    "Garantizar la seguridad del sistema, la integridad de la información y atender derechos ARCO.",
]
FINALIDADES_SECUNDARIAS = [
    "Elaborar estadísticas y análisis agregados y anonimizados para el Observatorio de Datos y mejora del servicio.",
]
DERECHOS = ["Acceso", "Rectificación", "Cancelación", "Oposición"]
MEDIDAS = [
    "Confidencialidad: acceso con usuario y contraseña, permisos por rol, mínimo privilegio y cifrado de teléfonos.",
    "Integridad: validaciones, restricciones en la base de datos y bitácora con encadenamiento criptográfico.",
    "Disponibilidad: reintentos de conexión, monitoreo del estado del sistema y respaldos periódicos.",
]


def aviso_simplificado():
    st.markdown(f"""
**Aviso de privacidad simplificado** · versión `{seg.VERSION_AVISO}`

**{RESPONSABLE}** es responsable del tratamiento de tus datos personales, **incluidos datos sensibles de salud**,
para: registrar y dar seguimiento al programa de cuidados, gestionar solicitudes de cuidado y monitorear signos vitales.

Para estas finalidades **necesitamos tu consentimiento expreso**. Puedes oponerte a la finalidad adicional
(estadísticas anonimizadas) sin que se afecte el servicio. Tienes derechos de **acceso, rectificación, cancelación
y oposición (ARCO)**, y puedes revocar tu consentimiento desde *Mis derechos y privacidad*.
""")


def aviso_integral():
    st.markdown(f"## Aviso de Privacidad Integral\n*Versión {seg.VERSION_AVISO} · Plantilla sujeta a revisión legal*")
    st.markdown(f"### 1. Identidad y domicilio del responsable\n**{RESPONSABLE}**, con domicilio en {DOMICILIO}. "
                f"Contacto para temas de privacidad: **{CONTACTO}**.")
    st.markdown("### 2. Datos personales que se tratan")
    for k, v in DATOS.items():
        st.markdown(f"- **{k}:** {v}")
    st.warning("Los datos de salud son **datos personales sensibles**: su tratamiento requiere tu consentimiento "
               "expreso y por escrito (firma autógrafa, electrónica o mecanismo de autenticación; aquí, tu "
               "sesión autenticada y la casilla de aceptación quedan registradas).")
    st.markdown("### 3. Finalidades")
    st.markdown("**Necesarias para el servicio:**")
    for f in FINALIDADES_PRIMARIAS:
        st.markdown(f"- {f}")
    st.markdown("**Adicionales (puedes negarte sin perder el servicio):**")
    for f in FINALIDADES_SECUNDARIAS:
        st.markdown(f"- {f}")
    st.markdown("### 4. Transferencias y remisiones\n"
                "Tus datos solo son vistos por el personal de coordinación, el cuidador asignado y los familiares que "
                "tengan acceso a tu perfil. **No se venden ni se ceden a terceros.** Cualquier transferencia que "
                "requiera consentimiento se informará y solicitará antes de realizarse. "
                "*[Completar si existen proveedores de nube o instituciones de salud receptoras]*")
    st.markdown("### 5. Derechos ARCO y revocación")
    st.markdown("Puedes **Acceder** a tus datos, **Rectificarlos**, solicitar su **Cancelación** y **Oponerte** a su "
                "uso, así como **revocar el consentimiento**. Presenta tu solicitud en la sección "
                f"*Mis derechos y privacidad* o escribe a {CONTACTO}. Recibirás un folio y una fecha límite de respuesta "
                f"(plazo configurado: {seg.ARCO_DIAS_HABILES} días hábiles, a verificar con la ley vigente). "
                "Si consideras que tu derecho no fue atendido, puedes acudir ante la autoridad en la materia "
                "(Secretaría Anticorrupción y Buen Gobierno).")
    st.markdown("### 6. Medidas de seguridad")
    for m in MEDIDAS:
        st.markdown(f"- {m}")
    st.markdown("### 7. Cambios al aviso\nCualquier cambio o nueva finalidad se notificará en el sistema y se "
                "solicitará un **nuevo consentimiento** antes de aplicarse (se te pedirá aceptar la nueva versión).")


def pantalla_consentimiento(u: dict):
    """Compuerta: el usuario no accede a datos mientras no acepte la versión vigente del aviso."""
    st.markdown("## Antes de continuar: tu privacidad")
    aviso_simplificado()
    with st.expander("Leer el Aviso de Privacidad Integral"):
        aviso_integral()
    with st.form("consent"):
        c1 = st.checkbox("He leído el aviso de privacidad y **consiento expresamente** el tratamiento de mis datos "
                         "personales sensibles (salud) para las finalidades necesarias del servicio. *(Obligatorio)*")
        c2 = st.checkbox("Acepto el uso de mis datos **anonimizados** para estadísticas y mejora del servicio. *(Opcional)*")
        c3 = st.checkbox("Me comprometo a mantener la **confidencialidad** de la información de salud a la que "
                         "tenga acceso. *(Obligatorio para familiares y cuidadores)*")
        ok = st.form_submit_button("Aceptar y continuar", type="primary")
    if ok:
        if not (c1 and c3):
            st.error("Para usar el sistema debes dar tu consentimiento y el compromiso de confidencialidad. "
                     "Si no lo aceptas, puedes cerrar sesión; no se tratarán tus datos.")
        else:
            seg.registrar_consentimiento(u["id"], True, c2, c3)
            st.rerun()
    if st.button("No acepto — cerrar sesión"):
        seg.cerrar_sesion()
        st.rerun()
