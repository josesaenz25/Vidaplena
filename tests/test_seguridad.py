"""Pruebas automáticas CID. Ejecutar: python tests/test_seguridad.py  (usa SQLite temporal, no toca PostgreSQL)."""
import os, sys, tempfile, time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
os.chdir(RAIZ); sys.path.insert(0, str(RAIZ))
tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/t.db"
os.environ["PBKDF2_ITER"] = "2000"
from cryptography.fernet import Fernet
os.environ["FIELD_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

import seed
seed.main(reset=True)
cred = {l.split()[0]: l.split()[1] for l in Path("credenciales_demo.txt").read_text().splitlines()[1:] if l.strip()}
os.remove("credenciales_demo.txt")

from streamlit.testing.v1 import AppTest
from sqlalchemy import text
import core
ok_n = 0
def check(nombre, cond):
    global ok_n
    print(("PASA  " if cond else "FALLA ") + nombre)
    if not cond: sys.exit(1)
    ok_n += 1

def nueva():
    at = AppTest.from_file("app.py", default_timeout=60); at.run(); return at
def login(at, u, p):
    at.text_input[0].set_value(u); at.text_input[1].set_value(p); at.button[0].click(); at.run(); return at
def aceptar(at, opcional=False):
    at.checkbox[0].check(); at.checkbox[2].check()
    if opcional: at.checkbox[1].check()
    at.button[0].click(); at.run(); return at
def sin_error(at): return not at.exception

# --- Confidencialidad
at = nueva(); check("1 Sin sesión se muestra login (no datos)", len(at.text_input) == 2 and not at.sidebar.button)
at = login(nueva(), "coordinacion", "mala"); check("2 Contraseña incorrecta rechazada", any("incorrectos" in e.value for e in at.error))
for _ in range(5): at = login(nueva(), "familiar1", "mala")
at = login(nueva(), "familiar1", cred["familiar1"]); check("3 Bloqueo tras 5 intentos (aun con clave correcta)", any("bloqueada" in e.value for e in at.error))
at = login(nueva(), "coordinacion", cred["coordinacion"])
check("4 Sin consentimiento no se accede a datos (compuerta)", any("tu privacidad" in m.value for m in at.markdown) and not at.sidebar.button)
at.checkbox[0].check(); at.button[0].click(); at.run()
check("5 Consentimiento incompleto rechazado", any("consentimiento" in e.value for e in at.error))
at = aceptar(at); check("6 Tras aceptar entra y no hay errores", sin_error(at) and any("Cerrar sesión" == b.label for b in at.sidebar.button))
eng = core.get_engine()
with eng.connect() as c:
    tel = c.execute(text("SELECT telefono FROM adultos LIMIT 1")).scalar()
    n_cons = c.execute(text("SELECT COUNT(*) FROM consentimientos")).scalar()
check("7 Teléfono almacenado cifrado", tel.startswith("enc:") and len(tel) > 40)
check("8 Consentimiento versionado en BD", n_cons == 1)

# coordinación ve todo
paginas = {"dashboard", "observatorio", "matching", "cuidadores", "auditoria", "estado_sistema", "gestion_arco", "mapa_interactivo"}
for p in sorted(paginas):
    a2 = at; a2.switch_page(f"views/{p}.py"); a2.run()
    check(f"9 Coordinación abre {p} sin error", sin_error(a2))

# familiar: mínimo privilegio
at = login(nueva(), "familiar2", cred["familiar2"]); at = aceptar(at)
check("10 Familiar entra", sin_error(at))
opts = at.sidebar.selectbox[0].options if at.sidebar.selectbox else []
check("11 Familiar solo ve a su adulto mayor", len(opts) == 1)
uf = at.session_state["usuario"]
for p in ("dashboard", "auditoria", "cuidadores", "gestion_arco", "observatorio", "matching", "estado_sistema"):
    # defensa en profundidad: aunque alguien abra la vista directamente, la propia vista la bloquea
    v = AppTest.from_file(f"views/{p}.py", default_timeout=60)
    v.session_state["usuario"] = uf; v.session_state["ultima_actividad"] = time.time(); v.run()
    check(f"12 Familiar NO accede a {p} (RBAC en la vista)", any("permiso" in e.value for e in v.error))
v = AppTest.from_file("views/dashboard.py"); v.run()
check("12b Sin sesión la vista tampoco muestra datos", any("permiso" in e.value for e in v.error))
at = login(nueva(), "familiar2", cred["familiar2"]); at = aceptar(at) if at.checkbox else at
at.switch_page("views/solicitudes.py"); at.run()
check("13 Familiar abre solicitudes sin error", sin_error(at))
at.switch_page("views/salud.py"); at.run()
check("14 Familiar ve salud propia sin tabla de alertas globales", sin_error(at) and not any("Alertas del sistema" in m.value for m in at.markdown))

# cuidador: solo asignados
at = login(nueva(), "cuidador1", cred["cuidador1"]); at = aceptar(at)
check("15 Cuidador entra", sin_error(at))
with eng.connect() as c:
    esperados = c.execute(text("SELECT COUNT(DISTINCT adulto_id) FROM solicitudes WHERE cuidador_id=(SELECT cuidador_id FROM usuarios WHERE username='cuidador1') AND estatus IN ('Asignada','En curso')")).scalar()
check("16 Cuidador solo ve adultos con caso activo asignado", len(at.sidebar.selectbox[0].options) == esperados)

# --- ARCO + consentimiento revocable
at = login(nueva(), "familiar2", cred["familiar2"])
at.switch_page("views/mis_derechos.py"); at.run()
check("17 Mis derechos sin error", sin_error(at))
import seguridad as seg
folio = seg.crear_arco(2 if False else int(eng.connect().execute(text("SELECT id FROM usuarios WHERE username='familiar2'")).scalar()), "Acceso", "Quiero una copia de mis datos")
with eng.connect() as c:
    fl = c.execute(text("SELECT fecha, fecha_limite FROM solicitudes_arco")).first()
check("18 ARCO crea folio y fecha límite", folio.startswith("ARCO-") and str(fl[1]) > str(fl[0])[:10])

# --- Integridad
ok, n, bad = seg.verificar_cadena()
check(f"19 Bitácora encadenada íntegra ({n} registros)", ok and n > 20)
with eng.begin() as c:
    c.execute(text("UPDATE bitacora SET usuario='intruso' WHERE id=5"))
ok, n, bad = seg.verificar_cadena()
check("20 Alteración de un registro detectada", (not ok) and bad == 5)
with eng.begin() as c:
    c.execute(text("UPDATE bitacora SET usuario=(SELECT usuario FROM bitacora WHERE id=4) WHERE id=5"))  # (el original no es recuperable: solo probamos detección)
with eng.begin() as c:
    c.execute(text("DELETE FROM bitacora WHERE id=7"))
ok, n, bad = seg.verificar_cadena()
check("21 Borrado de un registro detectado", not ok)
for sql, nombre in [("INSERT INTO signos_vitales(adulto_id,fecha,sistolica,diastolica,glucosa) VALUES (1,'2026-01-01',999,80,90)", "presión imposible"),
                    ("INSERT INTO solicitudes(adulto_id,fecha_solicitud,estatus,prioridad) VALUES (1,'2026-01-01','Inventado','Alta')", "estatus inválido"),
                    ("UPDATE adultos SET edad=5 WHERE id=1", "edad fuera de rango")]:
    try:
        with eng.begin() as c: c.execute(text(sql))
        rechazado = False
    except Exception:
        rechazado = True
    check(f"22 BD rechaza dato inválido: {nombre}", rechazado)

# --- cifrado / contraseñas / timeout
check("23 Cifrado ida y vuelta", seg.descifrar(seg.cifrar("55 1234 5678")) == "55 1234 5678")
h = seg.hash_password("Abcdef1234"); check("24 Hash PBKDF2 con sal (dos hashes distintos)", h != seg.hash_password("Abcdef1234") and seg.verificar_password("Abcdef1234", h) and not seg.verificar_password("x", h))
check("25 Política de contraseñas", seg.politica_password("corta") and seg.politica_password("abcdefghijkl") and not seg.politica_password("Abcdefghi1"))
at = login(nueva(), "coordinacion", cred["coordinacion"]); at = aceptar(at) if at.checkbox else at
at.session_state["ultima_actividad"] = time.time() - 3600; at.run()
check("26 Sesión expira por inactividad", len(at.text_input) == 2)
with eng.connect() as c:
    check("27 Contraseñas no están en claro", all("$" in r[0] and cred_pw not in r[0] for r in c.execute(text("SELECT password_hash FROM usuarios")) for cred_pw in cred.values()))
# --- cuentas del equipo y saludo
for usr, pw, esperado in [("Dulce Diaz", "Dulce123", "Bienvenida Dulce"), ("Natalia Cruz", "Nat123", "Bienvenida Natalia"), ("Luis Trejo", "Trejo123", "Bienvenido Luis")]:
    at = login(nueva(), usr, pw); at = aceptar(at) if at.checkbox else at
    check(f"28 {usr}: entra y la pantalla principal dice '{esperado}'", sin_error(at) and any(esperado in m.value for m in at.markdown))
print(f"\nTODAS LAS PRUEBAS PASARON ({ok_n})")
