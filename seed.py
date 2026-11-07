"""Crea el esquema, carga datos sintéticos, cifra teléfonos y crea usuarios demo.

Uso:
    python seed.py            # crea tablas nuevas, migra una BD existente (cifra teléfonos) y crea usuarios
    python seed.py --reset    # BORRA y recrea las tablas de VidaPlena
"""
import math
import os
import random
import secrets
import sys
from datetime import date, datetime, timedelta

from faker import Faker
from sqlalchemy import create_engine, func, select, text

from core import (COND_ESP, CONDICIONES, ESPECIALIDADES, ESTATUS,
                  PLANTILLA_AGENDA, SERVICIOS_SOL, TIPOS_SERVICIO, haversine,
                  db_url, metadata)
import seguridad as seg

ALCALDIAS = [  # nombre, lat, lon, peso relativo de población adulta mayor
    ("Álvaro Obregón", 19.3587, -99.2036, 8), ("Azcapotzalco", 19.4869, -99.1844, 5),
    ("Benito Juárez", 19.3727, -99.1580, 6), ("Coyoacán", 19.3467, -99.1617, 7),
    ("Cuajimalpa", 19.3570, -99.2940, 2), ("Cuauhtémoc", 19.4326, -99.1332, 7),
    ("Gustavo A. Madero", 19.4833, -99.1130, 12), ("Iztacalco", 19.3950, -99.0970, 4),
    ("Iztapalapa", 19.3574, -99.0670, 16), ("La Magdalena Contreras", 19.3000, -99.2400, 2),
    ("Miguel Hidalgo", 19.4330, -99.2000, 5), ("Milpa Alta", 19.1920, -99.0230, 1.5),
    ("Tláhuac", 19.2870, -99.0050, 4), ("Tlalpan", 19.2900, -99.1670, 7),
    ("Venustiano Carranza", 19.4430, -99.1090, 5), ("Xochimilco", 19.2570, -99.1050, 4),
]

rng = random.Random(42)
fake = Faker("es_MX")
Faker.seed(42)


def jitter(lat, lon, km=2.5):
    return (lat + rng.uniform(-km, km) / 111,
            lon + rng.uniform(-km, km) / (111 * math.cos(math.radians(lat))))


def migrar(engine):
    """Migración no destructiva de una BD existente: amplía columnas, cifra teléfonos en claro y crea usuarios."""
    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            for t_ in ("adultos", "cuidadores"):
                conn.execute(text(f"ALTER TABLE {t_} ALTER COLUMN telefono TYPE VARCHAR(255)"))
        for t_ in ("adultos", "cuidadores"):
            tb = metadata.tables[t_]
            for r in conn.execute(select(tb.c.id, tb.c.telefono)).all():
                if r.telefono and not r.telefono.startswith("enc:"):
                    conn.execute(tb.update().where(tb.c.id == r.id).values(telefono=seg.cifrar(r.telefono)))
    crear_usuarios(engine)
    usuarios_equipo(engine)


EQUIPO = [  # usuario (minúsculas), nombre completo, variable de entorno con su contraseña, contraseña local de respaldo
    ("dulce diaz", "Dulce Carolina Díaz Martínez", "PASS_DULCE", "Dulce123"),
    ("natalia cruz", "Natalia Cruz González", "PASS_NATALIA", "Nat123"),
    ("luis trejo", "Luis Trejo", "PASS_LUIS", "Trejo123"),
]


def usuarios_equipo(engine):
    """Crea (si no existen) las cuentas del equipo con rol de coordinación. Funciona en una BD ya cargada."""
    T = metadata.tables["usuarios"]
    with engine.begin() as conn:
        for usr, nombre, var, pw_local in EQUIPO:
            if conn.execute(select(T.c.id).where(T.c.username == usr)).first():
                continue
            # En producción (APP_ENV=produccion) la contraseña DEBE venir de las variables/secretos; nunca del código.
            pw = os.getenv(var) or (None if os.getenv("APP_ENV") == "produccion" else pw_local)
            if not pw:
                print(f"AVISO: falta {var}; no se creó el usuario {usr}.")
                continue
            conn.execute(T.insert().values(
                username=usr, nombre=nombre, password_hash=seg.hash_password(pw), rol="coordinacion",
                activo=True, intentos_fallidos=0, creado=datetime.now()))
            print(f"Usuario del equipo creado: {usr}")


def crear_usuarios(engine):
    """Usuarios demo con contraseñas ALEATORIAS (se muestran una sola vez y se guardan en credenciales_demo.txt)."""
    if os.getenv("CREAR_USUARIOS_DEMO", "1") == "0":     # en la nube no se crean cuentas demo
        return
    T = metadata.tables
    with engine.begin() as conn:
        if conn.execute(select(func.count()).select_from(T["usuarios"])).scalar():
            return
        activos = conn.execute(text(
            "SELECT DISTINCT cuidador_id, adulto_id FROM solicitudes "
            "WHERE estatus IN ('Asignada','En curso') AND cuidador_id IS NOT NULL ORDER BY cuidador_id")).all()
        cuidadores_con_caso = []
        for cid, aid in activos:
            if cid not in [c for c, _ in cuidadores_con_caso]:
                cuidadores_con_caso.append((cid, aid))
        demo = [("coordinacion", "Coordinación VidaPlena", "coordinacion", None, None)]
        for k, (cid, aid) in enumerate(cuidadores_con_caso[:2], 1):
            demo.append((f"cuidador{k}", f"Cuidador demo {k}", "cuidador", None, cid))
        for k in (1, 2):
            demo.append((f"familiar{k}", f"Familiar demo {k}", "familiar", k, None))
        creds = []
        for usr, nom, rol, aid, cid in demo:
            pw = "Vp" + secrets.token_urlsafe(9) + "7"
            conn.execute(T["usuarios"].insert().values(
                username=usr, nombre=nom, password_hash=seg.hash_password(pw), rol=rol, adulto_id=aid,
                cuidador_id=cid, activo=True, intentos_fallidos=0, creado=datetime.now()))
            creds.append(f"{usr:14s} {pw:22s} rol={rol}" + (f" adulto_id={aid}" if aid else "") +
                         (f" cuidador_id={cid}" if cid else ""))
    texto = "\n".join(creds)
    try:
        with open("credenciales_demo.txt", "w", encoding="utf-8") as f:
            f.write("Credenciales DEMO (datos sintéticos). Cámbialas desde 'Mis derechos'. NO subir a git.\n" + texto + "\n")
    except OSError:
        pass
    print("\nUsuarios demo creados (guardados en credenciales_demo.txt):\n" + texto)


def main(reset: bool):
    engine = create_engine(db_url())
    with engine.begin() as conn:
        if reset:
            cascade = " CASCADE" if engine.dialect.name == "postgresql" else ""
            for t in reversed(metadata.sorted_tables):
                conn.execute(text(f"DROP TABLE IF EXISTS {t.name}{cascade}"))
        metadata.create_all(conn)
        if conn.execute(select(func.count()).select_from(metadata.tables["adultos"])).scalar():
            migrar(engine)
            print("Ya hay datos de negocio. Usa --reset para recrearlos.")
            return

    T = metadata.tables
    now = datetime.now()
    alc_ids = {}
    with engine.begin() as conn:
        for i, (n, la, lo, _) in enumerate(ALCALDIAS, 1):
            conn.execute(T["alcaldias"].insert().values(id=i, nombre=n, lat=la, lon=lo))
            alc_ids[i] = (n, la, lo)
        pesos = [a[3] for a in ALCALDIAS]

        # --- Adultos mayores ---
        adultos = []
        for i in range(1, 201):
            aid = rng.choices(range(1, 17), weights=pesos)[0]
            _, la, lo = alc_ids[aid]
            lat, lon = jitter(la, lo)
            sexo = rng.choice(["F", "M"])
            nombre = (fake.first_name_female() if sexo == "F" else fake.first_name_male()
                      ) + " " + fake.last_name() + " " + fake.last_name()
            cond = rng.choices(CONDICIONES, weights=[28, 22, 18, 12, 20])[0]
            if cond == "Demencia / Alzheimer":
                nivel = rng.choices(["Media", "Alta"], weights=[40, 60])[0]
            elif cond == "Movilidad reducida":
                nivel = rng.choices(["Media", "Alta"], weights=[60, 40])[0]
            else:
                nivel = rng.choices(["Baja", "Media"], weights=[65, 35])[0]
            adultos.append(dict(
                id=i, nombre=nombre, edad=int(min(98, max(60, rng.gauss(74, 8)))),
                sexo=sexo, alcaldia_id=aid, telefono=seg.cifrar(fake.phone_number()[:30]),
                condicion=cond, nivel_dependencia=nivel, lat=lat, lon=lon))
        conn.execute(T["adultos"].insert(), adultos)

        # --- Cuidadores ---
        cuid = []
        for i in range(1, 51):
            aid = rng.randint(1, 16)
            _, la, lo = alc_ids[aid]
            lat, lon = jitter(la, lo, 3)
            sexo = rng.choice(["F", "M"])
            nombre = (fake.first_name_female() if sexo == "F" else fake.first_name_male()
                      ) + " " + fake.last_name() + " " + fake.last_name()
            cuid.append(dict(
                id=i, nombre=nombre, alcaldia_id=aid,
                especialidad=rng.choices(ESPECIALIDADES, weights=[20, 25, 15, 15, 25])[0],
                experiencia_anios=rng.randint(1, 20),
                calificacion=round(rng.uniform(3.4, 5.0), 1),
                tarifa_hora=float(rng.randrange(90, 230, 10)),
                disponible=rng.random() < 0.72,
                telefono=seg.cifrar(fake.phone_number()[:30]), lat=lat, lon=lon))
        conn.execute(T["cuidadores"].insert(), cuid)

        # --- Servicios cercanos ---
        serv, sid = [], 1
        for aid, (n, la, lo) in alc_ids.items():
            for tipo in TIPOS_SERVICIO:
                for k in range(rng.randint(1, 2)):
                    lat, lon = jitter(la, lo, 3)
                    pref = {"Centro de salud": "Centro de Salud", "Farmacia": "Farmacia",
                            "Programa social": "Programa Social", "Centro de día": "Centro de Día"}[tipo]
                    serv.append(dict(
                        id=sid, nombre=f"{pref} {fake.last_name()} - {n}", tipo=tipo,
                        alcaldia_id=aid, direccion=fake.street_address()[:190],
                        telefono=fake.phone_number()[:40], lat=lat, lon=lon))
                    sid += 1
        conn.execute(T["servicios"].insert(), serv)

        # --- Solicitudes ---
        sol = []
        for i in range(1, 201):
            ad = rng.choice(adultos)
            edad_dias = rng.random() * 180
            fecha = now - timedelta(days=edad_dias, hours=rng.uniform(0, 12))
            est = rng.choices(ESTATUS, weights=[15, 20, 20, 38, 7])[0]
            if edad_dias > 30 and est == "Pendiente":
                est = "Completada"
            cid, fasig = None, None
            if est in ("Asignada", "En curso", "Completada"):
                cand = rng.sample(cuid, 8)
                best = min(cand, key=lambda c: haversine(ad["lat"], ad["lon"], c["lat"], c["lon"]))
                cid = best["id"]
                fasig = min(now, fecha + timedelta(hours=rng.uniform(1, 48)))
            sol.append(dict(
                id=i, adulto_id=ad["id"], cuidador_id=cid, fecha_solicitud=fecha,
                fecha_asignacion=fasig, tipo_servicio=rng.choice(SERVICIOS_SOL),
                prioridad=rng.choices(["Baja", "Media", "Alta"], weights=[25, 50, 25])[0],
                estatus=est, notas=""))
        conn.execute(T["solicitudes"].insert(), sol)

        # --- Signos vitales ---
        vit = []
        for ad in adultos:
            for k in range(10):
                f = now - timedelta(days=rng.uniform(0, 20), hours=rng.uniform(0, 12))
                if k == 0:
                    f = now - timedelta(hours=rng.uniform(1, 30))
                sis = 118 + (22 if ad["condicion"] == "Hipertensión" else 0) + rng.gauss(0, 9)
                dia = 76 + (12 if ad["condicion"] == "Hipertensión" else 0) + rng.gauss(0, 6)
                glu = 92 + (55 if ad["condicion"] == "Diabetes" else 0) + rng.gauss(0, 14)
                vit.append(dict(
                    adulto_id=ad["id"], fecha=f, sistolica=int(sis), diastolica=int(dia),
                    glucosa=int(glu),
                    estado_animo=rng.choices(["Bien", "Regular", "Bajo"], weights=[60, 30, 10])[0],
                    actividad_min=rng.randint(0, 60)))
        conn.execute(T["signos_vitales"].insert(), vit)

        # --- Agenda de actividades (7 días + hoy) ---
        acts = []
        for ad in adultos:
            adh = rng.uniform(0.6, 0.95)
            for d in range(0, 8):
                dia = date.today() - timedelta(days=d)
                for hora, act, tipo in PLANTILLA_AGENDA:
                    if d == 0:
                        hecho = int(hora[:2]) < now.hour and rng.random() < adh
                    else:
                        hecho = rng.random() < adh
                    acts.append(dict(adulto_id=ad["id"], fecha=dia, hora=hora,
                                     actividad=act, tipo=tipo, completada=hecho))
        conn.execute(T["actividades"].insert(), acts)
        if engine.dialect.name == "postgresql":
            for t_ in ("alcaldias", "adultos", "cuidadores", "servicios",
                       "solicitudes", "signos_vitales", "actividades"):
                conn.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{t_}','id'), "
                    f"(SELECT COALESCE(MAX(id),1) FROM {t_}))"))

    crear_usuarios(engine)
    usuarios_equipo(engine)
    print(f"Listo: {len(adultos)} adultos, {len(cuid)} cuidadores, {len(serv)} servicios, "
          f"{len(sol)} solicitudes, {len(vit)} lecturas, {len(acts)} actividades.")


if __name__ == "__main__":
    main("--reset" in sys.argv)
