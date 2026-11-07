import plotly.graph_objects as go
import streamlit as st

import seguridad as seg
from core import BLUE, kpi_row, page_header, style_fig

seg.requiere("estado_sistema")
page_header("Estado del sistema", "Disponibilidad, integridad y seguridad en tiempo real", "🩺")
e = seg.estado_sistema()
kpi_row([("Base de datos", "En línea" if e["bd_ok"] else "Caída", f"{e.get('latencia_ms', '—')} ms de respuesta",
          "green" if e["bd_ok"] else "red"),
         ("Integridad de bitácora", "Íntegra" if e["cadena_ok"] else "ALTERADA", f"{e['cadena_n']} registros verificados",
          "green" if e["cadena_ok"] else "red"),
         ("Cifrado de campos", "Activo" if e["cifrado_ok"] else "Sin llave", "Teléfonos de adultos y cuidadores",
          "green" if e["cifrado_ok"] else "red"),
         ("Sesión", f"{seg.TIMEOUT_MIN} min", "Cierre por inactividad", "blue")])
st.write("")
if e.get("filas"):
    f = e["filas"]
    fig = go.Figure(go.Bar(x=list(f.keys()), y=list(f.values()), marker_color=BLUE, text=list(f.values()), textposition="outside"))
    fig.update_layout(title="Registros por tabla")
    st.plotly_chart(style_fig(fig, 300), use_container_width=True)
st.markdown("#### Resumen de controles CID")
st.table({"Principio": ["Confidencialidad", "Integridad", "Disponibilidad"],
          "Controles activos": ["Login, roles, mínimo privilegio, cifrado de teléfonos, consentimiento",
                                "CHECK en BD, validación de formularios, bitácora encadenada con SHA-256",
                                "Reintentos, pool con pre-ping, reinicio automático, backup.py"]})
