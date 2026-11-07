"""Núcleo compartido de VidaPlena CDMX: base de datos, reglas de negocio y estilos."""
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import folium
import numpy as np
import pandas as pd
import streamlit as st
from sqlalchemy import (Boolean, CheckConstraint, Column, Date, DateTime, Float,
                        ForeignKey, Index, Integer, MetaData, String, Table,
                        create_engine, insert, select, update)
from sqlalchemy.exc import OperationalError

BASE_DIR = Path(__file__).parent
BANNER = BASE_DIR / "assets" / "logo.png"


class ConfigError(RuntimeError):
    """Falta configuración obligatoria (credenciales de base de datos)."""


def _cargar_env():
    """Lee .env (si existe) sin sobrescribir variables ya definidas. Las credenciales no viven en el código."""
    f = BASE_DIR / ".env"
    if f.exists():
        for linea in f.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_cargar_env()


def db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    if os.getenv("DB_PASSWORD"):
        return "postgresql+psycopg2://{u}:{p}@{h}:{pt}/{n}".format(
            u=os.getenv("DB_USER", "admin"), p=quote_plus(os.environ["DB_PASSWORD"]),
            h=os.getenv("DB_HOST", "127.0.0.1"), pt=os.getenv("DB_PORT", "5433"), n=os.getenv("DB_NAME", "vidaplena"))
    raise ConfigError("No hay credenciales de base de datos. Copia .env.example a .env y completa DB_PASSWORD.")


# ------------------------------------------------------------------
# Paleta institucional
# ------------------------------------------------------------------
NAVY, BLUE, TEAL, SKY = "#0B2E6B", "#1F4FA3", "#2BA6A0", "#8FC1E3"
AMBER, RED, GREEN, VIOLET = "#F2A93B", "#D64545", "#2E9E6B", "#7A6FD0"
PALETA = [BLUE, TEAL, SKY, AMBER, VIOLET, RED, GREEN, NAVY]
TONOS = {"blue": BLUE, "teal": TEAL, "amber": AMBER, "red": RED, "green": GREEN}

# ------------------------------------------------------------------
# Catálogos
# ------------------------------------------------------------------
CONDICIONES = ["Hipertensión", "Diabetes", "Movilidad reducida",
               "Demencia / Alzheimer", "Sin condición crónica"]
ESPECIALIDADES = ["Geriatría", "Enfermería", "Fisioterapia",
                  "Cuidado de demencia", "Acompañamiento"]
COND_ESP = {"Hipertensión": "Enfermería", "Diabetes": "Enfermería",
            "Movilidad reducida": "Fisioterapia",
            "Demencia / Alzheimer": "Cuidado de demencia",
            "Sin condición crónica": "Acompañamiento"}
SERVICIOS_SOL = ["Acompañamiento", "Enfermería a domicilio", "Fisioterapia",
                 "Cuidado de demencia", "Apoyo en actividades diarias"]
PRIORIDADES = ["Baja", "Media", "Alta"]
ESTATUS = ["Pendiente", "Asignada", "En curso", "Completada", "Cancelada"]
ESTATUS_ACTIVOS = ["Pendiente", "Asignada", "En curso"]
TIPOS_SERVICIO = ["Centro de salud", "Farmacia", "Programa social", "Centro de día"]
TIPO_COLOR = {"Centro de salud": "red", "Farmacia": "green",
              "Programa social": "orange", "Centro de día": "purple"}
TIPO_ICONO = {"Centro de salud": "plus-sign", "Farmacia": "tint",
              "Programa social": "star", "Centro de día": "heart"}
PLANTILLA_AGENDA = [("08:00", "Tomar medicamentos", "Medicamento"),
                    ("10:00", "Caminata ligera", "Actividad física"),
                    ("12:00", "Hidratación", "Bienestar"),
                    ("14:00", "Comida saludable", "Alimentación"),
                    ("18:00", "Llamada con familiar", "Social")]

# ------------------------------------------------------------------
# Esquema de base de datos (PostgreSQL o SQLite)
# ------------------------------------------------------------------
metadata = MetaData()
Table("alcaldias", metadata,
      Column("id", Integer, primary_key=True),
      Column("nombre", String(60), nullable=False),
      Column("lat", Float), Column("lon", Float))
Table("adultos", metadata,
      Column("id", Integer, primary_key=True),
      Column("nombre", String(120), nullable=False),
      Column("edad", Integer), Column("sexo", String(1)),
      Column("alcaldia_id", Integer, ForeignKey("alcaldias.id")),
      Column("telefono", String(255)), Column("condicion", String(40)),
      Column("nivel_dependencia", String(10)),
      Column("lat", Float), Column("lon", Float),
      CheckConstraint("edad BETWEEN 60 AND 110", name="ck_adultos_edad"))
Table("cuidadores", metadata,
      Column("id", Integer, primary_key=True),
      Column("nombre", String(120), nullable=False),
      Column("alcaldia_id", Integer, ForeignKey("alcaldias.id")),
      Column("especialidad", String(40)),
      Column("experiencia_anios", Integer),
      Column("calificacion", Float),
      Column("tarifa_hora", Float),
      Column("disponible", Boolean, default=True),
      Column("telefono", String(255)),
      Column("lat", Float), Column("lon", Float),
      CheckConstraint("calificacion BETWEEN 1 AND 5", name="ck_cuidadores_calif"))
Table("servicios", metadata,
      Column("id", Integer, primary_key=True),
      Column("nombre", String(150), nullable=False),
      Column("tipo", String(30)),
      Column("alcaldia_id", Integer, ForeignKey("alcaldias.id")),
      Column("direccion", String(200)), Column("telefono", String(40)),
      Column("lat", Float), Column("lon", Float))
Table("solicitudes", metadata,
      Column("id", Integer, primary_key=True),
      Column("adulto_id", Integer, ForeignKey("adultos.id"), nullable=False),
      Column("cuidador_id", Integer, ForeignKey("cuidadores.id")),
      Column("fecha_solicitud", DateTime), Column("fecha_asignacion", DateTime),
      Column("tipo_servicio", String(40)), Column("prioridad", String(10)),
      Column("estatus", String(15)), Column("notas", String(250)),
      CheckConstraint("estatus IN ('Pendiente','Asignada','En curso','Completada','Cancelada')", name="ck_sol_estatus"),
      CheckConstraint("prioridad IN ('Baja','Media','Alta')", name="ck_sol_prioridad"),
      Index("ix_sol_adulto", "adulto_id"), Index("ix_sol_cuidador", "cuidador_id"), Index("ix_sol_estatus", "estatus"))
Table("signos_vitales", metadata,
      Column("id", Integer, primary_key=True),
      Column("adulto_id", Integer, ForeignKey("adultos.id"), nullable=False),
      Column("fecha", DateTime),
      Column("sistolica", Integer), Column("diastolica", Integer),
      Column("glucosa", Integer), Column("estado_animo", String(10)),
      Column("actividad_min", Integer),
      CheckConstraint("sistolica BETWEEN 60 AND 250 AND diastolica BETWEEN 40 AND 150 AND glucosa BETWEEN 30 AND 500", name="ck_vitales_rango"),
      Index("ix_vit_adulto_fecha", "adulto_id", "fecha"))
Table("actividades", metadata,
      Column("id", Integer, primary_key=True),
      Column("adulto_id", Integer, ForeignKey("adultos.id"), nullable=False),
      Column("fecha", Date), Column("hora", String(5)),
      Column("actividad", String(120)), Column("tipo", String(30)),
      Column("completada", Boolean, default=False),
      Index("ix_act_adulto_fecha", "adulto_id", "fecha"))
# ---------------- Seguridad y privacidad ----------------
Table("usuarios", metadata,
      Column("id", Integer, primary_key=True),
      Column("username", String(60), nullable=False, unique=True),
      Column("nombre", String(120), nullable=False),
      Column("password_hash", String(255), nullable=False),
      Column("rol", String(15), nullable=False),
      Column("adulto_id", Integer, ForeignKey("adultos.id")),
      Column("cuidador_id", Integer, ForeignKey("cuidadores.id")),
      Column("activo", Boolean, default=True),
      Column("intentos_fallidos", Integer, default=0),
      Column("bloqueado_hasta", DateTime), Column("ultimo_acceso", DateTime), Column("creado", DateTime),
      CheckConstraint("rol IN ('coordinacion','familiar','cuidador')", name="ck_usuarios_rol"))
Table("consentimientos", metadata,
      Column("id", Integer, primary_key=True),
      Column("usuario_id", Integer, ForeignKey("usuarios.id"), nullable=False),
      Column("version", String(10), nullable=False), Column("fecha", DateTime, nullable=False),
      Column("dato_sensible", Boolean, nullable=False), Column("finalidad_secundaria", Boolean, default=False),
      Column("confidencialidad", Boolean, default=False), Column("revocado_en", DateTime),
      Index("ix_consent_usuario", "usuario_id"))
Table("solicitudes_arco", metadata,
      Column("id", Integer, primary_key=True),
      Column("folio", String(24)), Column("usuario_id", Integer, ForeignKey("usuarios.id"), nullable=False),
      Column("tipo", String(20), nullable=False), Column("descripcion", String(500)),
      Column("estatus", String(15), nullable=False), Column("fecha", DateTime, nullable=False),
      Column("fecha_limite", Date), Column("fecha_respuesta", DateTime), Column("respuesta", String(500)),
      CheckConstraint("estatus IN ('Recibida','En revisión','Atendida','Rechazada')", name="ck_arco_estatus"))
Table("bitacora", metadata,
      Column("id", Integer, primary_key=True),
      Column("fecha", DateTime, nullable=False), Column("usuario", String(60)), Column("rol", String(15)),
      Column("accion", String(40), nullable=False), Column("entidad", String(40)), Column("entidad_id", String(30)),
      Column("detalle", String(300)), Column("hash_prev", String(64), nullable=False),
      Column("hash_actual", String(64), nullable=False),
      Index("ix_bitacora_fecha", "fecha"))

DATE_COLS = {"solicitudes": ["fecha_solicitud", "fecha_asignacion"],
             "signos_vitales": ["fecha"], "actividades": ["fecha"],
             "bitacora": ["fecha"], "consentimientos": ["fecha", "revocado_en"],
             "solicitudes_arco": ["fecha", "fecha_respuesta", "fecha_limite"],
             "usuarios": ["bloqueado_hasta", "ultimo_acceso", "creado"]}
SIN_AUDITORIA = {"bitacora"}
VALORES_REGISTRABLES = {"estatus", "completada", "disponible", "prioridad"}  # únicos valores que se copian a la bitácora


@st.cache_resource
def get_engine():
    url = db_url()
    args = {}
    if url.startswith("postgresql"):
        args = {"connect_timeout": 5}
        if os.getenv("DB_SSLMODE"):
            args["sslmode"] = os.environ["DB_SSLMODE"]      # en producción: require / verify-full
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800, connect_args=args)


def con_reintentos(fn, intentos=3):
    """Disponibilidad: reintenta ante cortes breves de la base de datos."""
    for i in range(intentos):
        try:
            return fn()
        except OperationalError:
            if i == intentos - 1:
                raise
            time.sleep(0.5 * (i + 1))


@st.cache_data(ttl=30, show_spinner=False)
def load(name: str) -> pd.DataFrame:
    df = con_reintentos(lambda: pd.read_sql(select(metadata.tables[name]), get_engine()))
    for col in DATE_COLS.get(name, []):
        df[col] = pd.to_datetime(df[col])
    return df


def _registrar(accion, name, entidad_id, vals):
    if name in SIN_AUDITORIA:
        return
    from seguridad import auditar
    campos = ", ".join(f"{k}={v}" if k in VALORES_REGISTRABLES else k for k, v in vals.items())
    auditar(accion, name, entidad_id, campos[:290])


def insert_row(name: str, **vals):
    def op():
        with get_engine().begin() as conn:
            return conn.execute(insert(metadata.tables[name]).values(**vals)).inserted_primary_key[0]
    pk = con_reintentos(op)
    st.cache_data.clear()
    _registrar("CREAR", name, pk, vals)
    return pk


def insert_many(name: str, rows: list):
    def op():
        with get_engine().begin() as conn:
            conn.execute(insert(metadata.tables[name]), rows)
    con_reintentos(op)
    st.cache_data.clear()
    _registrar("CREAR_LOTE", name, "", {"filas": len(rows)})


def update_row(name: str, row_id: int, **vals):
    t = metadata.tables[name]
    def op():
        with get_engine().begin() as conn:
            conn.execute(update(t).where(t.c.id == int(row_id)).values(**vals))
    con_reintentos(op)
    st.cache_data.clear()
    _registrar("MODIFICAR", name, row_id, vals)


# ------------------------------------------------------------------
# Consultas compuestas
# ------------------------------------------------------------------
def with_alcaldia(df: pd.DataFrame) -> pd.DataFrame:
    al = load("alcaldias")[["id", "nombre"]].rename(
        columns={"id": "alcaldia_id", "nombre": "alcaldia"})
    return df.merge(al, on="alcaldia_id", how="left")


def solicitudes_full() -> pd.DataFrame:
    from seguridad import permitidos_adultos
    s = load("solicitudes")
    s = s[s.adulto_id.isin(permitidos_adultos())]
    a = with_alcaldia(load("adultos"))[
        ["id", "nombre", "alcaldia", "condicion", "lat", "lon"]].rename(
        columns={"id": "adulto_id", "nombre": "adulto",
                 "lat": "a_lat", "lon": "a_lon"})
    c = load("cuidadores")[["id", "nombre"]].rename(
        columns={"id": "cuidador_id", "nombre": "cuidador"})
    return s.merge(a, on="adulto_id", how="left").merge(c, on="cuidador_id", how="left")


def adulto_activo() -> pd.Series:
    """Adulto mayor activo, SIEMPRE validado contra los permisos del usuario (mínimo privilegio)."""
    from seguridad import permitidos_adultos
    ad = with_alcaldia(load("adultos"))
    ad = ad[ad.id.isin(permitidos_adultos())]
    if ad.empty:
        st.info("Por ahora no tiene personas asignadas.")
        st.stop()
    row = ad[ad.id == st.session_state.get("adulto_id")]
    return row.iloc[0] if len(row) else ad.iloc[0]


def haversine(lat1, lon1, lat2, lon2):
    """Distancia en km entre puntos (admite arreglos)."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi, dl = p2 - p1, np.radians(lon2) - np.radians(lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def horas_respuesta(sol: pd.DataFrame) -> pd.Series:
    d = sol.dropna(subset=["fecha_asignacion"])
    return (d.fecha_asignacion - d.fecha_solicitud).dt.total_seconds() / 3600


def ultima_lectura() -> pd.DataFrame:
    v = load("signos_vitales").sort_values("fecha")
    return v.groupby("adulto_id").tail(1)


def clasif_presion(s, d):
    if s >= 140 or d >= 90:
        return "Elevada", "bad"
    if s < 90 or d < 60:
        return "Baja", "warn"
    return "Normal", "ok"


def clasif_glucosa(g):
    if g > 140:
        return "Elevada", "bad"
    if g < 70:
        return "Baja", "bad"
    return "Normal", "ok"


def ranking_cuidadores(adulto, cuid, esp_req, pesos):
    """Puntaje 0-100 combinando cercanía, especialidad, calificación y experiencia."""
    c = cuid[cuid.disponible].copy()
    if c.empty:
        return c
    c["distancia_km"] = haversine(adulto.lat, adulto.lon, c.lat.values, c.lon.values)
    c["s_dist"] = np.clip(1 - c.distancia_km / 15, 0, 1)
    c["s_esp"] = np.where(c.especialidad == esp_req, 1.0,
                          np.where(c.especialidad == "Geriatría", 0.7, 0.3))
    c["s_cal"] = np.clip((c.calificacion - 3) / 2, 0, 1)
    c["s_exp"] = np.clip(c.experiencia_anios / 10, 0, 1)
    tot = sum(pesos.values()) or 1
    w = {k: v / tot for k, v in pesos.items()}
    for k in ["dist", "esp", "cal", "exp"]:
        c[f"p_{k}"] = 100 * w[k] * c[f"s_{k}"]
    c["score"] = c[["p_dist", "p_esp", "p_cal", "p_exp"]].sum(axis=1)
    return c.sort_values("score", ascending=False)


# ------------------------------------------------------------------
# Componentes visuales
# ------------------------------------------------------------------
def inject_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"], .stMarkdown, button, input, textarea {{ font-family:'Inter',sans-serif; }}
    .stApp {{ background:#F4F7FB; }}
    .block-container {{ padding-top:1.3rem; padding-bottom:3rem; max-width:1280px; }}
    [data-testid="stSidebar"] {{ background:#FFFFFF; border-right:1px solid #E3E9F3; }}
    .stAppDeployButton, footer, #MainMenu {{ display:none !important; }}
    h1,h2,h3 {{ color:{NAVY}; letter-spacing:-0.01em; }}
    .vp-header {{ background:linear-gradient(115deg,{NAVY} 0%,{BLUE} 62%,{TEAL} 135%);
        color:#fff; padding:22px 28px; border-radius:16px; margin-bottom:18px;
        box-shadow:0 6px 18px rgba(11,46,107,.18); }}
    .vp-title {{ font-size:1.6rem; font-weight:800; line-height:1.2; }}
    .vp-sub {{ opacity:.9; margin-top:4px; font-size:.98rem; }}
    .vp-kpi {{ background:#fff; border:1px solid #E3E9F3; border-top:4px solid var(--c);
        border-radius:14px; padding:14px 18px; box-shadow:0 1px 4px rgba(16,40,90,.05); height:100%; }}
    .vp-kpi .l {{ color:#5B6B86; font-size:.8rem; font-weight:600; text-transform:uppercase; letter-spacing:.04em; }}
    .vp-kpi .v {{ color:{NAVY}; font-size:1.9rem; font-weight:800; line-height:1.25; }}
    .vp-kpi .s {{ color:#5B6B86; font-size:.82rem; min-height:1.1em; }}
    .vp-card {{ background:#fff; border:1px solid #E3E9F3; border-radius:14px; padding:16px 20px;
        box-shadow:0 1px 4px rgba(16,40,90,.05); }}
    .vp-card h4 {{ margin:0 0 6px 0; color:{NAVY}; }}
    .chip {{ display:inline-block; background:#EAF1FB; color:{NAVY}; border:1px solid #D2E0F5;
        border-radius:999px; padding:4px 14px; margin:3px 6px 3px 0; font-size:.88rem; font-weight:500; }}
    .badge {{ display:inline-block; border-radius:999px; padding:2px 10px; font-size:.78rem; font-weight:700; }}
    .badge.ok {{ background:#E3F5EC; color:#1C7A4F; }}
    .badge.warn {{ background:#FFF2DC; color:#9A6310; }}
    .badge.bad {{ background:#FDE6E6; color:#A52C2C; }}
    .badge.info {{ background:#E6EFFB; color:{BLUE}; }}
    .vp-step {{ background:#fff; border:1px solid #E3E9F3; border-radius:12px; padding:12px 14px; text-align:center; }}
    .vp-step b {{ color:{BLUE}; font-size:1.3rem; }}
    .vp-step span {{ display:block; color:#33415C; font-size:.88rem; }}
    div[data-testid="stMetric"] {{ background:#fff; border:1px solid #E3E9F3; border-radius:12px; padding:10px 14px; }}
    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
        border-radius:10px; font-weight:600; }}
    button[kind="primary"], button[kind="primaryFormSubmit"] {{ background:{BLUE}; border-color:{BLUE}; }}
    </style>
    """, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "", icon: str = ""):
    st.markdown(
        f"<div class='vp-header'><div class='vp-title'>{icon} {title}</div>"
        f"<div class='vp-sub'>{subtitle}</div></div>", unsafe_allow_html=True)


def kpi(label, value, sub="", tone="blue"):
    st.markdown(
        f"<div class='vp-kpi' style='--c:{TONOS[tone]}'><div class='l'>{label}</div>"
        f"<div class='v'>{value}</div><div class='s'>{sub}</div></div>",
        unsafe_allow_html=True)


def kpi_row(items):
    cols = st.columns(len(items))
    for col, it in zip(cols, items):
        with col:
            kpi(*it)


def badge(text, tone="info"):
    return f"<span class='badge {tone}'>{text}</span>"


def style_fig(fig, height=340):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#33415C"),
        title=dict(font=dict(size=15, color=NAVY)),
        legend=dict(orientation="h", y=-0.15),
        colorway=PALETA)
    fig.update_xaxes(gridcolor="#E8EDF5")
    fig.update_yaxes(gridcolor="#E8EDF5")
    return fig


def tabla(df, **kw):
    st.dataframe(df, use_container_width=True, hide_index=True, **kw)


def mapa_base(lat=19.40, lon=-99.14, zoom=11):
    return folium.Map(location=[lat, lon], zoom_start=zoom,
                      tiles="OpenStreetMap", control_scale=True)


def estrellas(x: float) -> str:
    n = int(round(x))
    return "★" * n + "☆" * (5 - n)
