"""Respaldo y restauración (Disponibilidad). Requiere pg_dump/psql en el PATH o Docker.

    python backup.py              # crea backups/vidaplena_AAAAMMDD_HHMM.sql (+ SHA-256 para verificar integridad)
    python backup.py --verificar backups/archivo.sql
Programa este script (cron / Programador de tareas) a diario y copia la carpeta a otro equipo o nube cifrada.
"""
import hashlib
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import core

core._cargar_env()
DIR = Path(__file__).parent / "backups"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def respaldar():
    DIR.mkdir(exist_ok=True)
    destino = DIR / f"vidaplena_{datetime.now():%Y%m%d_%H%M}.sql"
    env = dict(os.environ, PGPASSWORD=os.environ["DB_PASSWORD"])
    cmd = ["pg_dump", "-h", os.getenv("DB_HOST", "127.0.0.1"), "-p", os.getenv("DB_PORT", "5433"),
           "-U", os.environ["DB_USER"], "-d", os.getenv("DB_NAME", "vidaplena"), "-f", str(destino)]
    subprocess.run(cmd, check=True, env=env)
    (destino.with_suffix(".sha256")).write_text(sha256(destino))
    print("Respaldo creado:", destino)


def verificar(archivo):
    p = Path(archivo)
    ok = sha256(p) == p.with_suffix(".sha256").read_text().strip()
    print("Integridad del respaldo:", "OK" if ok else "ALTERADO")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    verificar(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == "--verificar" else respaldar()
