import streamlit as st

import privacidad
import seguridad as seg
from core import page_header

seg.requiere("aviso")
page_header("Aviso de privacidad", "Cómo se protegen y usan los datos de pacientes y cuidadores", "🔐")
privacidad.aviso_integral()
