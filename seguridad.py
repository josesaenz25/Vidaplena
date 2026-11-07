"""Seguridad de VidaPlena: Confidencialidad, Integridad y Disponibilidad (CID / CIA).

Confidencialidad : autenticación, roles (RBAC), mínimo privilegio, cifrado de campos, consentimiento.
Integridad       : bitácora encadenada con hash (detecta alteraciones), validaciones, restricciones en BD.
Disponibilidad   : reintentos, verificación de estado, respaldos (backup.py), reinicio automático (Docker).
"""
import base64
import hashlib
import hmac
import os
import secrets
import time
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
from sqlalchemy import func, insert, select, text, update

import core
from core import get_engine, load, metadata

# ------------------------------------------------------------------ parámetros
ITERACIONES = int(os.getenv("PBKDF2_ITER", "600000"))     # OWASP 2023 para PBKDF2-HMAC-SHA256
MAX_INTENTOS = 5
BLOQUEO_MIN = 15
TIMEOUT_MIN = int(os.getenv("SESSION_TIMEOUT_MIN", "20"))
VERSION_AVISO = "2026-11-v1"
ARCO_DIAS_HABILES = int(os.getenv("ARCO_DIAS_HABILES", "20"))   # VERIFICAR contra la LFPDPPP vigente
ROLES = ("coordinacion", "familiar", "cuidador")
TIPOS_ARCO = ("Acceso", "Rectificación", "Cancelación", "Oposición", "Revocación del consentimiento")
GENESIS = "0" * 64


# ================================================================== CONFIDENCIALIDAD
# ---- contraseñas
def hash_password(pw: str, iteraciones: int = None) -> str:
    it = iteraciones or ITERACIONES
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, it)
    return f"pbkdf2_sha256${it}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verificar_password(pw: str, almacenado: str) -> bool:
    try:
        _, it, salt, dk = almacenado.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", pw.encode(), base64.b64decode(salt), int(it))
        return hmac.compare_digest(calc, base64.b64decode(dk))
    except Exception:
        return False


def politica_password(pw: str) -> str | None:
    """Devuelve el motivo de rechazo o None si cumple."""
    if len(pw) < 10:
        return "Debe tener al menos 10 caracteres."
    if pw.lower() == pw or pw.upper() == pw or not any(c.isdigit() for c in pw):
        return "Combina mayúsculas, minúsculas y números."
    return None


# ---- cifrado de campos (teléfonos)
def _fernet():
    from cryptography.fernet import Fernet
    key = os.getenv("FIELD_ENCRYPTION_KEY")
    if not key:
        raise core.ConfigError("Falta FIELD_ENCRYPTION_KEY. Genera una con: python -c "
                               "\"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
    return Fernet(key.encode())


def cifrar(valor: str) -> str:
    if not valor:
        return valor
    return "enc:" + _fernet().encrypt(valor.encode()).decode()


def descifrar(valor: str) -> str:
    if not valor or not str(valor).startswith("enc:"):
        return valor or ""
    from cryptography.fernet import InvalidToken
    try:
        return _fernet().decrypt(valor[4:].encode()).decode()
    except InvalidToken:
        return "[no descifrable]"


def enmascarar(tel: str) -> str:
    d = "".join(c for c in (tel or "") if c.isdigit())
    return ("•••• •• " + d[-2:]) if len(d) >= 2 else "••••"


def telefono(valor_cifrado: str, completo: bool = False) -> str:
    """Muestra el teléfono completo solo si el rol lo permite o se pide expresamente; si no, enmascarado."""
    tel = descifrar(valor_cifrado)
    return tel if (completo and usuario() and usuario()["rol"] in ("coordinacion", "cuidador")) else enmascarar(tel)


# ---- sesión
def usuario() -> dict | None:
    return st.session_state.get("usuario")


SALUDOS = {"dulce": "Bienvenida", "natalia": "Bienvenida", "luis": "Bienvenido"}


def saludo() -> str:
    """'Bienvenida Dulce', 'Bienvenido Luis'… (según el nombre de pila de la cuenta)."""
    u = usuario()
    if not u:
        return ""
    primero = u["nombre"].split()[0]
    return f"{SALUDOS.get(primero.lower(), 'Bienvenido/a')} {primero}"


def rol() -> str | None:
    u = usuario()
    return u["rol"] if u else None


def sesion_vigente() -> bool:
    u = usuario()
    if not u:
        return False
    if time.time() - st.session_state.get("ultima_actividad", 0) > TIMEOUT_MIN * 60:
        cerrar_sesion(motivo="TIMEOUT")
        return False
    st.session_state["ultima_actividad"] = time.time()
    return True


def cerrar_sesion(motivo="LOGOUT"):
    u = usuario()
    if u:
        auditar(motivo, "usuarios", u["id"], "", usuario_override=u)
    for k in list(st.session_state.keys()):
        del st.session_state[k]


def autenticar(username: str, password: str):
    """(usuario|None, mensaje). Bloqueo temporal tras MAX_INTENTOS fallos; sin revelar si el usuario existe."""
    t = metadata.tables["usuarios"]
    username = (username or "").strip().lower()
    evento = None            # la bitácora se escribe FUERA de la transacción (evita bloqueos)
    with get_engine().begin() as conn:
        r = conn.execute(select(t).where(t.c.username == username)).mappings().first()
        if r is None:
            hash_password(password, 1000)               # iguala tiempos de respuesta
            evento = ("LOGIN_FALLIDO", "", f"usuario inexistente: {username[:40]}", {"username": "—", "rol": ""})
            msg = "Usuario o contraseña incorrectos."
        elif r["bloqueado_hasta"] and r["bloqueado_hasta"] > datetime.now():
            mins = int((r["bloqueado_hasta"] - datetime.now()).total_seconds() // 60) + 1
            msg = f"Cuenta bloqueada temporalmente. Intenta de nuevo en {mins} min."
        elif not r["activo"] or not verificar_password(password, r["password_hash"]):
            n = (r["intentos_fallidos"] or 0) + 1
            vals = {"intentos_fallidos": n}
            if n >= MAX_INTENTOS:
                vals.update(intentos_fallidos=0, bloqueado_hasta=datetime.now() + timedelta(minutes=BLOQUEO_MIN))
            conn.execute(update(t).where(t.c.id == r["id"]).values(**vals))
            evento = ("LOGIN_FALLIDO", r["id"], f"intento {n}", {"username": r["username"], "rol": r["rol"]})
            msg = "Usuario o contraseña incorrectos."
        else:
            conn.execute(update(t).where(t.c.id == r["id"]).values(
                intentos_fallidos=0, bloqueado_hasta=None, ultimo_acceso=datetime.now()))
            msg = "ok"
    if evento:
        auditar(evento[0], "usuarios", evento[1], evento[2], usuario_override=evento[3])
    if msg != "ok":
        return None, msg
    u = {"id": int(r["id"]), "username": r["username"], "nombre": r["nombre"], "rol": r["rol"],
         "adulto_id": int(r["adulto_id"]) if r["adulto_id"] is not None else None,
         "cuidador_id": int(r["cuidador_id"]) if r["cuidador_id"] is not None else None}
    st.session_state["usuario"] = u
    st.session_state["ultima_actividad"] = time.time()
    auditar("LOGIN", "usuarios", u["id"], "", usuario_override=u)
    return u, "ok"


def cambiar_password(uid: int, actual: str, nueva: str) -> str | None:
    t = metadata.tables["usuarios"]
    with get_engine().begin() as conn:
        r = conn.execute(select(t.c.password_hash).where(t.c.id == uid)).first()
        if not r or not verificar_password(actual, r[0]):
            return "La contraseña actual no es correcta."
        motivo = politica_password(nueva)
        if motivo:
            return motivo
        conn.execute(update(t).where(t.c.id == uid).values(password_hash=hash_password(nueva)))
    auditar("CAMBIO_PASSWORD", "usuarios", uid, "")
    return None


# ---- control de acceso por rol (mínimo privilegio)
PAGINAS_POR_ROL = {
    "coordinacion": {"inicio", "programa", "salud", "solicitudes", "cuidadores", "matching", "mapa_cdmx",
                     "observatorio", "mapa_interactivo", "dashboard", "mis_derechos", "gestion_arco",
                     "auditoria", "estado_sistema", "aviso"},
    "familiar": {"inicio", "programa", "salud", "solicitudes", "mapa_cdmx", "mis_derechos", "aviso"},
    "cuidador": {"inicio", "programa", "salud", "solicitudes", "mis_derechos", "aviso"},
}


def requiere(pagina: str):
    """Llamar al inicio de cada vista: corta la ejecución si el rol no tiene acceso (defensa en profundidad)."""
    if not sesion_vigente() or pagina not in PAGINAS_POR_ROL.get(rol(), set()):
        auditar("ACCESO_DENEGADO", "pagina", pagina, "")
        st.error("No tienes permiso para ver esta sección.")
        st.stop()


def permitidos_adultos() -> list[int]:
    """IDs de adultos mayores a los que el usuario puede acceder. Sin sesión → ninguno."""
    u = usuario()
    if not u:
        return []
    if u["rol"] == "coordinacion":
        return [int(i) for i in load("adultos").id]
    if u["rol"] == "familiar":
        return [u["adulto_id"]] if u.get("adulto_id") else []
    s = load("solicitudes")
    s = s[(s.cuidador_id == u["cuidador_id"]) & s.estatus.isin(["Asignada", "En curso"])]
    return sorted({int(i) for i in s.adulto_id})


# ---- consentimiento / aviso de privacidad
def consentimiento_vigente(uid: int) -> dict | None:
    t = metadata.tables["consentimientos"]
    with get_engine().connect() as conn:
        r = conn.execute(select(t).where(t.c.usuario_id == uid, t.c.version == VERSION_AVISO,
                                         t.c.revocado_en.is_(None), t.c.dato_sensible.is_(True))
                         .order_by(t.c.id.desc())).mappings().first()
    return dict(r) if r else None


def registrar_consentimiento(uid: int, dato_sensible: bool, secundaria: bool, confidencialidad: bool):
    with get_engine().begin() as conn:
        conn.execute(insert(metadata.tables["consentimientos"]).values(
            usuario_id=uid, version=VERSION_AVISO, fecha=datetime.now(), dato_sensible=dato_sensible,
            finalidad_secundaria=secundaria, confidencialidad=confidencialidad))
    auditar("CONSENTIMIENTO", "consentimientos", uid,
            f"version={VERSION_AVISO} sensible={dato_sensible} secundaria={secundaria}")
    st.cache_data.clear()


def revocar_consentimiento(uid: int):
    t = metadata.tables["consentimientos"]
    with get_engine().begin() as conn:
        conn.execute(update(t).where(t.c.usuario_id == uid, t.c.revocado_en.is_(None))
                     .values(revocado_en=datetime.now()))
    auditar("REVOCACION", "consentimientos", uid, "revocación de consentimiento")
    st.cache_data.clear()


# ---- derechos ARCO
def dias_habiles_despues(desde: date, n: int) -> date:
    d = desde
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:          # no considera días inhábiles oficiales
            n -= 1
    return d


def crear_arco(uid: int, tipo: str, descripcion: str) -> str:
    t = metadata.tables["solicitudes_arco"]
    ahora = datetime.now()
    with get_engine().begin() as conn:
        n = conn.execute(select(func.count()).select_from(t)).scalar() + 1
        folio = f"ARCO-{ahora:%Y}-{n:05d}"
        conn.execute(insert(t).values(
            folio=folio, usuario_id=uid, tipo=tipo, descripcion=descripcion[:500], estatus="Recibida",
            fecha=ahora, fecha_limite=dias_habiles_despues(ahora.date(), ARCO_DIAS_HABILES)))
    auditar("ARCO_CREADA", "solicitudes_arco", folio, f"tipo={tipo}")
    st.cache_data.clear()
    return folio


def resolver_arco(arco_id: int, estatus: str, respuesta: str):
    t = metadata.tables["solicitudes_arco"]
    with get_engine().begin() as conn:
        conn.execute(update(t).where(t.c.id == arco_id).values(
            estatus=estatus, respuesta=respuesta[:500],
            fecha_respuesta=datetime.now() if estatus in ("Atendida", "Rechazada") else None))
    auditar("ARCO_RESUELTA", "solicitudes_arco", arco_id, f"estatus={estatus}")
    st.cache_data.clear()


def exportar_mis_datos(uid: int) -> dict:
    """Derecho de ACCESO: copia de los datos que el sistema guarda de la cuenta y, según el rol, de la persona atendida."""
    out = {}
    with get_engine().connect() as conn:
        for nombre in ("usuarios", "consentimientos", "solicitudes_arco"):
            t = metadata.tables[nombre]
            df = pd.read_sql(select(t).where((t.c.id if nombre == "usuarios" else t.c.usuario_id) == uid), conn)
            if nombre == "usuarios":
                df = df.drop(columns=["password_hash"])
            out[nombre] = df.astype(str).to_dict("records")
    u = usuario()
    if u and u.get("adulto_id"):
        aid = u["adulto_id"]
        for nombre in ("adultos", "signos_vitales", "solicitudes", "actividades"):
            t = metadata.tables[nombre]
            col = t.c.id if nombre == "adultos" else t.c.adulto_id
            df = pd.read_sql(select(t).where(col == aid), get_engine())
            if "telefono" in df:
                df["telefono"] = df["telefono"].map(descifrar)
            out[nombre] = df.astype(str).to_dict("records")
    auditar("ARCO_ACCESO_EXPORT", "usuarios", uid, "exportación de datos propios")
    return out


# ================================================================== INTEGRIDAD
def _hash_registro(prev: str, fecha: str, usuario_: str, rol_: str, accion: str, entidad: str,
                   entidad_id: str, detalle: str) -> str:
    base = "|".join([prev, fecha, usuario_ or "", rol_ or "", accion, entidad or "", str(entidad_id or ""), detalle or ""])
    return hashlib.sha256(base.encode()).hexdigest()


def auditar(accion: str, entidad: str = "", entidad_id="", detalle: str = "", usuario_override: dict | None = None):
    """Agrega un registro encadenado a la bitácora (hash del registro anterior + contenido)."""
    u = usuario_override or usuario() or {"username": "sistema", "rol": ""}
    t = metadata.tables["bitacora"]
    fecha = datetime.now().replace(microsecond=0)
    try:
        with get_engine().begin() as conn:
            if conn.dialect.name == "postgresql":
                conn.execute(text("LOCK TABLE bitacora IN SHARE ROW EXCLUSIVE MODE"))   # serializa la cadena
            prev = conn.execute(select(t.c.hash_actual).order_by(t.c.id.desc()).limit(1)).scalar() or GENESIS
            h = _hash_registro(prev, fecha.isoformat(), u.get("username"), u.get("rol"), accion, entidad,
                               entidad_id, detalle)
            conn.execute(insert(t).values(
                fecha=fecha, usuario=u.get("username"), rol=u.get("rol"), accion=accion, entidad=entidad,
                entidad_id=str(entidad_id or ""), detalle=detalle, hash_prev=prev, hash_actual=h))
    except Exception as e:                                   # la auditoría nunca debe tumbar la app, pero se avisa
        st.session_state["_aviso_auditoria"] = f"No se pudo registrar en bitácora: {type(e).__name__}"


def verificar_cadena() -> tuple[bool, int, int | None]:
    """(íntegra, registros_revisados, id_primer_registro_alterado)."""
    t = metadata.tables["bitacora"]
    df = pd.read_sql(select(t).order_by(t.c.id), get_engine())
    prev = GENESIS
    for r in df.itertuples():
        esperado = _hash_registro(prev, pd.Timestamp(r.fecha).to_pydatetime().isoformat(), r.usuario, r.rol,
                                  r.accion, r.entidad, r.entidad_id, r.detalle if isinstance(r.detalle, str) else "")
        if r.hash_prev != prev or r.hash_actual != esperado:
            return False, len(df), int(r.id)
        prev = r.hash_actual
    return True, len(df), None


# ================================================================== DISPONIBILIDAD
def estado_sistema() -> dict:
    """Verificación rápida de salud: BD, latencia, tablas, cadena de auditoría, cifrado."""
    res = {}
    t0 = time.perf_counter()
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        res["bd_ok"] = True
        res["latencia_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        with get_engine().connect() as conn:
            res["filas"] = {n: conn.execute(select(func.count()).select_from(metadata.tables[n])).scalar()
                            for n in ("adultos", "cuidadores", "solicitudes", "signos_vitales", "usuarios", "bitacora")}
    except Exception as e:
        res.update(bd_ok=False, error=type(e).__name__)
    ok, n, bad = verificar_cadena() if res.get("bd_ok") else (False, 0, None)
    res.update(cadena_ok=ok, cadena_n=n, cadena_bad=bad)
    try:
        _fernet()
        res["cifrado_ok"] = True
    except Exception:
        res["cifrado_ok"] = False
    return res
