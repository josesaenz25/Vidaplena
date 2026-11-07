"""Panel de bienvenida de la pantalla de inicio (lado izquierdo del login).

Si existe assets/portada.png se usa esa imagen (por ejemplo, tu logo en alta resolución);
si no, se dibuja un logo y un skyline de la CDMX en SVG (vectorial, se ve nítido en cualquier pantalla).
"""
import base64
from pathlib import Path

ASSETS = Path(__file__).parent / "assets"

LOGO_SVG = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 210'>
<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='#1F4FA3'/><stop offset='1' stop-color='#4C8BE0'/></linearGradient></defs>
<path d='M92 92 L200 12 L308 92 L308 178 Q308 196 290 196 L110 196 Q92 196 92 178 Z' fill='none' stroke='url(#g)' stroke-width='11' stroke-linejoin='round'/>
<circle cx='176' cy='82' r='16' fill='#1F4FA3'/><circle cx='226' cy='78' r='12' fill='#4C8BE0'/>
<path d='M200 168 C150 136 140 100 168 100 C184 100 196 108 200 118 C204 108 218 98 234 100 C262 104 252 138 200 168 Z' fill='url(#g)'/>
</svg>"""

SKYLINE_SVG = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 190'>
<g fill='none' stroke='#1F4FA3' stroke-width='2' stroke-linejoin='round' stroke-linecap='round'>
<path d='M8 176 H392'/>
<!-- edificio izquierdo -->
<path d='M18 176 V118 L34 104 L50 118 V176 M26 130 H42 M26 146 H42 M26 162 H42'/>
<!-- torre -->
<path d='M62 176 V70 H86 V176 M74 70 V40 M68 70 H80 M68 86 H80 M68 102 H80 M68 118 H80 M68 134 H80 M68 150 H80'/>
<!-- catedral -->
<path d='M104 176 V128 H166 V176 M104 128 V100 L112 90 L120 100 V128 M150 128 V100 L158 90 L166 100 V128 M124 128 Q135 98 146 128 M118 150 H152 M116 164 H154'/>
<!-- Ángel de la Independencia -->
<path d='M172 176 V168 H228 V176 M180 168 V158 H220 V168 M190 158 V66 H210 V158 M186 66 H214 M192 66 V58 H208 V66 M196 112 H204'/>
<circle cx='200' cy='44' r='6'/>
<path d='M200 52 L184 34 M200 52 L216 34 M194 50 L178 42 M206 50 L222 42 M200 50 V58'/>
<!-- Bellas Artes -->
<path d='M238 176 V128 H318 V176 M246 128 V116 H310 V128 M258 116 Q278 78 298 116 M278 90 V80 M274 80 H282 M252 150 H304 M252 164 H304 M262 128 V176 M278 128 V176 M294 128 V176'/>
<!-- torre derecha -->
<path d='M330 176 V96 L342 84 L354 96 V176 M338 112 H346 M338 130 H346 M338 148 H346'/>
<path d='M362 176 V130 H388 V176 M370 140 H380 M370 154 H380'/>
</g></svg>"""


def _uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode()


def _archivo_uri(p: Path) -> str:
    mime = "image/svg+xml" if p.suffix == ".svg" else "image/png"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


CSS = """
<style>
.vp-portada{background:#fff;border:1px solid #E6E9EF;border-radius:24px;padding:2.2rem 1.8rem 2rem;
  box-shadow:0 8px 30px rgba(31,79,163,.10);text-align:center;max-width:460px;margin:2.5rem auto 1rem}
.vp-portada img{max-width:100%}
.vp-portada .t{font-size:2.5rem;font-weight:800;color:#14213D;line-height:1.1;margin:.2rem 0 .4rem;letter-spacing:-.5px}
.vp-portada .t span{color:#1F4FA3}
.vp-portada .s{color:#14213D;font-size:1.08rem;line-height:1.35;margin:.2rem auto 1.2rem;max-width:380px}
.vp-portada .f{color:#14213D;font-size:1.3rem;font-weight:600;line-height:1.3;margin:1.2rem auto 0;max-width:340px}
</style>"""


def panel_html() -> str:
    """Prioridad: 1) assets/portada_personalizada.png (imagen completa en alta resolución, opcional)
    2) logo vectorial (assets/logo_icono.svg, logo_nombre.svg, skyline.svg)  3) dibujo integrado."""
    custom = ASSETS / "portada_personalizada.png"
    if custom.exists():
        return CSS + (f"<div class='vp-portada'><img src='{_archivo_uri(custom)}' style='width:88%' "
                      "alt='VidaPlena CDMX'/></div>")
    ico, nom, sky = (ASSETS / "logo_icono.svg", ASSETS / "logo_nombre.svg", ASSETS / "skyline.svg")
    if ico.exists() and nom.exists() and sky.exists():     # vectorial: nítido a cualquier tamaño
        return CSS + f"""
<div class='vp-portada'>
  <img src='{_archivo_uri(ico)}' style='width:34%' alt='VidaPlena CDMX'/>
  <div style='margin:.8rem 0 .6rem'><img src='{_archivo_uri(nom)}' style='width:88%' alt='VidaPlena CDMX'/></div>
  <div class='s'>Bienestar y cuidado para nuestros adultos mayores</div>
  <img src='{_archivo_uri(sky)}' style='width:92%' alt='Ciudad de México'/>
  <div class='f'>Una ciudad que cuida a quienes siempre nos han dado más vida</div>
</div>"""
    return CSS + f"""
<div class='vp-portada'>
  <img src='{_uri(LOGO_SVG)}' style='width:62%' alt='VidaPlena CDMX'/>
  <div class='t'>VidaPlena <span>CDMX</span></div>
  <div class='s'>Bienestar y cuidado para nuestros adultos mayores</div>
  <img src='{_uri(SKYLINE_SVG)}' style='width:96%' alt='Ciudad de México'/>
  <div class='f'>Una frase</div>
</div>""".replace("Una frase", "Una ciudad que cuida a quienes siempre nos han dado más vida")
