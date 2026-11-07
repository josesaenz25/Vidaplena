FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_THEME_BASE=light \
    STREAMLIT_THEME_PRIMARY_COLOR="#1F4FA3" \
    STREAMLIT_THEME_BACKGROUND_COLOR="#F4F7FB" \
    STREAMLIT_THEME_SECONDARY_BACKGROUND_COLOR="#FFFFFF" \
    STREAMLIT_THEME_TEXT_COLOR="#14213D"

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Render (y otros) inyectan la variable PORT; por defecto 10000.
EXPOSE 10000
CMD streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-10000} --server.headless=true
