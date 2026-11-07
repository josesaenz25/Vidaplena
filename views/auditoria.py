import streamlit as st

import seguridad as seg
from core import kpi_row, load, page_header, tabla

seg.requiere("auditoria")
page_header("Bitácora de auditoría", "Quién hizo qué y cuándo, con verificación de integridad", "🧾")
ok, n, bad = seg.verificar_cadena()
if ok:
    st.success(f"Cadena de integridad **verificada**: {n} registros, ninguno alterado.")
else:
    st.error(f"**Alteración detectada** a partir del registro #{bad}. La bitácora fue modificada fuera del sistema.")
b = load("bitacora").sort_values("id", ascending=False)
f1, f2, f3 = st.columns(3)
acc = f1.multiselect("Acción", sorted(b.accion.unique()))
usr = f2.multiselect("Usuario", sorted(b.usuario.dropna().unique()))
ent = f3.multiselect("Entidad", sorted(b.entidad.dropna().unique()))
d = b
if acc: d = d[d.accion.isin(acc)]
if usr: d = d[d.usuario.isin(usr)]
if ent: d = d[d.entidad.isin(ent)]
kpi_row([("Registros", len(b), "En la bitácora", "blue"),
         ("Accesos fallidos", int((b.accion == "LOGIN_FALLIDO").sum()), "Intentos rechazados", "red"),
         ("Accesos denegados", int((b.accion == "ACCESO_DENEGADO").sum()), "Sin permiso de rol", "amber"),
         ("Modificaciones", int(b.accion.isin(["CREAR", "MODIFICAR", "CREAR_LOTE"]).sum()), "Altas y cambios", "teal")])
st.write("")
t = d[["id", "fecha", "usuario", "rol", "accion", "entidad", "entidad_id", "detalle"]].head(300)
tabla(t)
st.download_button("Descargar bitácora (CSV)", d.drop(columns=["hash_prev"]).to_csv(index=False).encode("utf-8"),
                   "bitacora.csv", "text/csv")
