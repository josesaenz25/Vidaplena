# VidaPlena CDMX — Sistema de gestión y monitoreo para adultos mayores

Python · Streamlit · PostgreSQL · SQLAlchemy · Plotly · Folium · Docker  (datos 100 % sintéticos)

## Puesta en marcha
1. `cp .env.example .env` y completa `DB_PASSWORD` y `FIELD_ENCRYPTION_KEY` (la instrucción para generarla está en el archivo).
2. `docker compose up -d`
3. `pip install -r requirements.txt`
4. `python seed.py --reset`   (BD nueva) — o `python seed.py` para **migrar** una BD existente (cifra teléfonos, crea usuarios).
   Las contraseñas demo se muestran una vez y se guardan en `credenciales_demo.txt` (no se sube a git).
5. `streamlit run app.py`
6. Pruebas: `python tests/test_seguridad.py` (SQLite temporal; 43 comprobaciones CID).

Nota: una migración sin `--reset` no agrega las restricciones CHECK/índices a tablas ya existentes; para tenerlas usa `--reset`.

## Seguridad y privacidad (CID)
- **Confidencialidad:** login, roles (coordinación / familiar / cuidador), mínimo privilegio, cifrado de teléfonos (Fernet), aviso de privacidad + consentimiento versionado, ARCO.
- **Integridad:** restricciones CHECK en BD, validación de formularios, bitácora encadenada con SHA-256 (detecta alteración o borrado).
- **Disponibilidad:** reintentos de conexión, pool con pre-ping, `restart: unless-stopped` + healthcheck, `backup.py`, página *Estado del sistema*.

El texto legal es una plantilla: requiere revisión de un profesional del derecho antes de usarse con datos reales.
