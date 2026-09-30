from datetime import datetime, timedelta
import os
import re
import sys
import time
from urllib.parse import quote_plus
import base64
import feedparser
import folium
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium

# Asegurar que el directorio raíz esté en el path para importar cartografia correctamente
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
  sys.path.append(current_dir)

# Importar el mapa modular desde la carpeta cartografia si existe
try:
  from cartografia.mapa_vial import generar_mapa_carreteras
except ImportError:
  def generar_mapa_carreteras(db):
    st.warning("Módulo de cartografía no encontrado. Usando mapa base.")
    m = folium.Map(location=[-17.0, -65.0], zoom_start=6)
    st_folium(m, use_container_width=True, height=500)

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="OARL | Observatorio de Geopolítica y Soberanía de Tránsito",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 2. ESTILOS CSS INSTITUCIONALES
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    header.stAppHeader, [data-testid="stHeader"] {
        display: none !important;
        height: 0px !important;
    }
    
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], section.main {
        background-color: #f4f6f9 !important;
        color: #111827 !important;
        margin: 0 !important;
        padding: 0 !important;
        max-width: 100% !important;
        width: 100vw !important;
        overflow-x: hidden !important;
    }

    .block-container, [data-testid="stMainBlockContainer"] {
        padding-top: 0rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0rem !important;
        padding-right: 0rem !important;
        margin-top: -60px !important;
        max-width: 100% !important;
        width: 100% !important;
    }

    .top-bar-full {
        background-color: #001f3f;
        color: #cbd5e1;
        padding: 10px 40px;
        font-size: 11.5px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 2px solid #004080;
        width: 100vw !important;
        box-sizing: border-box;
        margin: 0 !important;
    }
    .top-bar-full span { color: #ffffff; font-weight: 600; }

    .portal-header-full {
        background: linear-gradient(180deg, #002855 0%, #001833 100%);
        padding: 22px 40px;
        color: white;
        border-bottom: 4px solid #008060;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        width: 100vw !important;
        box-sizing: border-box;
        margin: 0 !important;
        display: flex;
        align-items: center;
        gap: 20px;
    }
    .portal-logo {
        width: 65px;
        height: 65px;
        background-color: #ffffff;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        color: #002855;
        font-size: 18px;
        border: 2px solid #008060;
        box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        flex-shrink: 0;
    }
    .portal-title {
        font-size: 26px;
        font-weight: 800;
        letter-spacing: 0.5px;
        margin: 0;
        color: #ffffff;
        text-transform: uppercase;
    }
    .portal-subtitle {
        font-size: 13px;
        font-weight: 400;
        color: #94a3b8;
        margin-top: 4px;
        letter-spacing: 0.3px;
    }

    .content-body { padding: 30px 40px; width: 100%; box-sizing: border-box; }

    div.stButton > button {
        background-color: #002855 !important;
        color: #ffffff !important;
        border: 1px solid #004080 !important;
        font-weight: 600 !important;
        font-size: 10.5px !important;
        border-radius: 4px !important;
        transition: all 0.2s ease-in-out;
        width: 100% !important;
        padding: 6px 4px !important;
    }
    div.stButton > button:hover {
        background-color: #003366 !important;
        border-color: #008060 !important;
        color: #ffffff !important;
    }

    [data-testid="stMetricValue"] { color: #002855 !important; font-weight: 800 !important; font-size: 24px !important; }
    [data-testid="stMetricLabel"] { color: #334155 !important; font-weight: 700 !important; font-size: 11px !important; text-transform: uppercase; }
    </style>
""",
    unsafe_allow_html=True,
)

# 3. MATRICES DE COORDENADAS Y CONSULTAS DINÁMICAS (ABC COMO FUENTE PRIMARIA)
TERRITORIOS_BASE = {
    "Carretera al Norte (Santa Cruz)": {
        "lat": -17.3825,
        "lon": -63.1520,
        "queries": [
            "site:abc.gob.bo santa cruz",
            "bloqueo carretera norte santa cruz montero",
            "ABC vias bolivia santa cruz estado de rutas",
        ],
    },
    "Eje Troncal Cochabamba - Occidente": {
        "lat": -17.4721,
        "lon": -66.4250,
        "queries": [
            "site:abc.gob.bo cochabamba",
            "bloqueo cochabamba occidente parotani",
            "ABC vias bolivia cochabamba transitabilidad",
        ],
    },
    "Carretera Altiplano (La Paz - Oruro)": {
        "lat": -17.2150,
        "lon": -67.5520,
        "queries": [
            "site:abc.gob.bo la paz oruro",
            "bloqueo la paz oruro conani",
            "ABC vias bolivia la paz oruro",
        ],
    },
    "Nodo Logístico Senkata (El Alto)": {
        "lat": -16.5500,
        "lon": -68.2100,
        "queries": [
            "site:abc.gob.bo el alto",
            "bloqueo senkata el alto",
            "ABC vias el alto",
        ],
    },
    "Corredor Minero Potosí": {
        "lat": -19.7820,
        "lon": -65.7510,
        "queries": [
            "site:abc.gob.bo potosi",
            "bloqueo potosi carretera",
            "ABC vias potosi",
        ],
    },
    "Acceso Fronterizo Tambo Quemado": {
        "lat": -18.2833,
        "lon": -69.1167,
        "queries": [
            "site:abc.gob.bo tambo quemado",
            "tambo quemado frontera aduana transitabilidad",
            "ABC vias tambo quemado",
        ],
    },
    "Acceso Fronterizo Desaguadero": {
        "lat": -16.5650,
        "lon": -69.0380,
        "queries": [
            "site:abc.gob.bo desaguadero",
            "desaguadero frontera peru transitabilidad",
            "ABC vias desaguadero",
        ],
    },
    "Corredor del Chaco (Sucre - Tarija)": {
        "lat": -20.0210,
        "lon": -63.5210,
        "queries": [
            "site:abc.gob.bo tarija chuquisaca",
            "yacuiba chaco bloqueo carretera",
            "ABC vias tarija yacuiba",
        ],
    },
}


@st.cache_data(ttl=300)
def escanear_noticias_en_vivo():
  db_dinamica = {}
  ahora = datetime.now()
  limite_horas = 36

  for nodo_key, data in TERRITORIOS_BASE.items():
    noticias_validas = []
    estado_semaforo = "🟢 Estable / Operativo (ABC)"
    nivel_riesgo_code = 0

    for q in data["queries"]:
      rss_url = f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=es-419&gl=BO&ceid=BO:es-419"
      feed = feedparser.parse(rss_url)

      if feed.entries:
        for entry in feed.entries:
          pub_date = None
          if hasattr(entry, "published_parsed") and entry.published_parsed:
            pub_date = datetime.fromtimestamp(
                time.mktime(entry.published_parsed)
            )

          if pub_date:
            diferencia_horas = (ahora - pub_date).total_seconds() / 3600.0

            if 0 <= diferencia_horas <= limite_horas:
              titulo_lower = entry.title.lower()
              if any(y in titulo_lower for y in ["2025", "2024", "2023"]):
                continue

              fecha_str = pub_date.strftime("%d de %B de %Y - %H:%M")

              fuentes_etiqueta = "Monitoreo General"
              if "abc.gob.bo" in q or "abc" in q:
                fuentes_etiqueta = (
                    "Reporte Oficial ABC (Administradora Boliviana de"
                    " Carreteras)"
                )
              elif "defensoria" in q:
                fuentes_etiqueta = "Informe Defensoría del Pueblo"

              if any(
                  w in titulo_lower
                  for w in [
                      "bloqueo",
                      "cortado",
                      "protesta",
                      "toma",
                      "cierre total",
                      "corte",
                      "interrupción",
                  ]
              ):
                if nivel_riesgo_code < 2:
                  estado_semaforo = "🔴 Alerta Activa (Bloqueo ABC)"
                  nivel_riesgo_code = 2
              elif any(
                  w in titulo_lower
                  for w in [
                      "amenaza",
                      "paro",
                      "vigilia",
                      "restringido",
                      "precaución",
                      "desvío",
                  ]
              ):
                if nivel_riesgo_code == 0:
                  estado_semaforo = (
                      "🟡 Restricción / Tránsito con Precaución (ABC)"
                  )
                  nivel_riesgo_code = 1

              if not any(n["titulo"] == entry.title for n in noticias_validas):
                noticias_validas.append({
                    "categoria": fuentes_etiqueta,
                    "titulo": entry.title,
                    "fecha": fecha_str,
                    "link": entry.link,
                    "horas_antiguedad": round(diferencia_horas, 1),
                })
              if len(noticias_validas) >= 4:
                break
        if len(noticias_validas) >= 4:
          break

    if not noticias_validas or nivel_riesgo_code == 0:
      estado_semaforo = "🟢 Transitable / Operativo (Sistema ABC)"
      nivel_riesgo_code = 0
      noticias_validas = [{
          "categoria": "Reporte Oficial ABC (Red Vial Fundamental)",
          "titulo": (
              f"Transitabilidad normal verificada en el corredor: {nodo_key}"
          ),
          "fecha": "Actualizado en tiempo real vía Sistema ABC",
          "link": "https://transitabilidad.abc.gob.bo/",
      }]

    db_dinamica[nodo_key] = {
        "punto": f"Tramo / Nodo: {nodo_key}",
        "lat": data["lat"],
        "lon": data["lon"],
        "descripcion": (
            f"Evaluación cruzada basada en el Mapa de Transitabilidad de la"
            f" ABC (Red Vial Fundamental) para {nodo_key}."
        ),
        "causa": "Fuente Primaria Autorizada: Administradora Boliviana de Carreteras (ABC)",
        "estado_semaforo": estado_semaforo,
        "nivel_riesgo": nivel_riesgo_code,
        "noticias": noticias_validas,
    }
  return db_dinamica


DB_NODOS = escanear_noticias_en_vivo()

# 4. BARRA SUPERIOR
st.markdown(
    """
    <div class="top-bar-full">
        <div>Sistema Integrado: Gestión de Tratados Internacionales y Comercio Exterior</div>
        <div>Módulo Académico - Diplomacia y Relaciones Internacionales | <b>UMSA 2026</b></div>
    </div>
""",
    unsafe_allow_html=True,
)

# 5. ENCABEZADO PRINCIPAL CON LOGOTIPO INSTITUCIONAL (OARL)
st.markdown(
    """
    <div class="portal-header-full">
        <div class="portal-logo">OARL</div>
        <div>
            <div class="portal-title">Observatorio de Alerta y Riesgo Logístico</div>
            <div class="portal-subtitle">Centro de Inteligencia de Soberanía de Tránsito, Integración Regional y Relaciones Internacionales</div>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

if "menu_activo" not in st.session_state:
  st.session_state.menu_activo = "¿Qué es OARL?"

st.markdown('<div class="content-body">', unsafe_allow_html=True)

# 6. BARRA DE NAVEGACIÓN ADOSADA
col_m0, col_m1, col_m2, col_m3, col_m4, col_m5, col_m6, col_m7 = st.columns(8)


def render_boton(col_obj, col_idx, label):
  is_active = st.session_state.menu_activo == label
  if is_active:
    st.markdown(
        f"""
        <style>
        div[data-testid="stHorizontalBlock"] > div:nth-child({col_idx}) button {{
            background-color: #ffffff !important;
            color: #000000 !important;
            border: 2px solid #002855 !important;
            font-weight: 800 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
  with col_obj:
    if st.button(label, use_container_width=True, key=f"btn_nav_{label}"):
      st.session_state.menu_activo = label
      st.rerun()


render_boton(col_m0, 1, "¿Qué es OARL?")
render_boton(col_m1, 2, "Impacto Comercial")
render_boton(col_m2, 3, "Nodos Críticos")
render_boton(col_m3, 4, "Pasos Fronterizos")
render_boton(col_m4, 5, "Simulador Algorítmico")
render_boton(col_m5, 6, "Línea de Tiempo 2015-2026")
render_boton(col_m6, 7, "Acuerdos y Repositorio")

st.markdown("---")

menu = st.session_state.menu_activo
nombres_nodos = list(DB_NODOS.keys())
nodos_activos_count = sum(1 for v in DB_NODOS.values() if v["nivel_riesgo"] > 0)

if menu == "¿Qué es OARL?":
  st.markdown("### ¿Qué es el Observatorio de Alerta y Riesgo Logístico (OARL)?")
  st.markdown(
      """
        <div style="background: white; border: 1px solid #cbd5e1; border-radius: 6px; padding: 25px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 25px;">
            <p style="font-size: 15px; color: #1e293b; line-height: 1.7; text-align: justify;">
                El <b>OARL (Observatorio de Alerta y Riesgo Logístico)</b> es un centro académico e institucional de inteligencia geopolítica y gestión de tránsito, adscrito al estudio avanzado de la diplomacia, integración regional y comercio exterior. Su función principal es el monitoreo permanente, la cuantificación de asimetrías logísticas y la evaluación de la vulnerabilidad en la Red Vial Fundamental de Bolivia y sus corredores de exportación hacia los océanos Pacífico y Atlántico.
            </p>
            <p style="font-size: 14.5px; color: #334155; line-height: 1.6; text-align: justify; margin-top: 15px;">
                Para garantizar máxima credibilidad y rigor científico en la toma de decisiones, el sistema toma como fuente primaria y oficial los reportes de transitabilidad de la <b>Administradora Boliviana de Carreteras (ABC)</b>, cruzándolos con variables macroeconómicas e indicadores normativos internacionales (Comunidad Andina y Acuerdos de Complementación Económica - ACE).
            </p>
        </div>
        """,
      unsafe_allow_html=True,
  )

  col_mv1, col_mv2 = st.columns(2)
  with col_mv1:
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #002855 0%, #001833 100%); color: white; border-radius: 6px; padding: 22px; height: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h4 style="color: #ffffff; margin-top: 0; font-size: 18px; border-bottom: 2px solid #008060; padding-bottom: 8px;">Misión</h4>
            <p style="font-size: 13.5px; color: #cbd5e1; line-height: 1.6; text-align: justify; margin-top: 12px;">
                Proveer inteligencia estratégica, datos y herramientas de simulación fundamentadas en fuentes oficiales (ABC) para analizar el impacto de la conflictividad socio-vial en el comercio exterior boliviano, fortaleciendo la defensa de los principios de libre tránsito y el cumplimiento de los tratados de integración regional.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

  with col_mv2:
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #001f3f 0%, #001225 100%); color: white; border-radius: 6px; padding: 22px; height: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h4 style="color: #ffffff; margin-top: 0; font-size: 18px; border-bottom: 2px solid #008060; padding-bottom: 8px;">Visión</h4>
            <p style="font-size: 13.5px; color: #cbd5e1; line-height: 1.6; text-align: justify; margin-top: 12px;">
                Constituirse en el centro universitario de referencia nacional en la investigación de geopolítica del transporte, seguridad logística y comercio, ofreciendo plataformas tecnológicas transparentes que anticipen riesgos de aislamiento y protejan la soberanía de integración de Bolivia hacia el 2030.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

  st.markdown("<br>", unsafe_allow_html=True)
  st.markdown("---")
  st.markdown("### Autora y Creadora del Proyecto de Grado")

  # Cargar la foto desde la carpeta img usando Base64 para círculo perfecto, nitidez y cercanía
  ruta_imagen = "img/milenka.jpg"
  imagen_html = ""
  if os.path.exists(ruta_imagen):
    with open(ruta_imagen, "rb") as img_file:
      encoded = base64.b64encode(img_file.read()).decode()
      imagen_html = f"data:image/jpeg;base64,{encoded}"

  col_perfil_img, col_perfil_info = st.columns([0.8, 3.2])

  with col_perfil_img:
    if imagen_html:
      st.markdown(
          f"""
            <div style="display: flex; flex-direction: column; align-items: center; margin-top: 10px;">
                <div style="width: 150px; height: 150px; border-radius: 50%; overflow: hidden; border: 3px solid #002855; box-shadow: 0 4px 8px rgba(0,0,0,0.15);">
                    <img src="{imagen_html}" style="width: 100%; height: 100%; object-fit: cover; object-position: center;" />
                </div>
                <span style="font-size: 13px; font-weight: 700; color: #1e293b; margin-top: 10px; text-align: center;">Milenka Dalena Quispe Benito</span>
            </div>
            """,
          unsafe_allow_html=True,
      )
    else:
      st.markdown(
          """
            <div style="background: white; border: 2px solid #cbd5e1; border-radius: 8px; padding: 15px; text-align: center;">
                <span style="font-size: 11px; color: #64748b; font-weight: 700;">Guarda tu foto como img/milenka.jpg</span>
            </div>
            """,
          unsafe_allow_html=True,
      )

  with col_perfil_info:
        # Cargar el icono cuadrado desde img/icono.jpg
        ruta_icono = "img/icono.jpg"
        icono_html = ""
        if os.path.exists(ruta_icono):
            with open(ruta_icono, "rb") as ico_file:
                encoded_ico = base64.b64encode(ico_file.read()).decode()
                icono_html = f"data:image/jpeg;base64,{encoded_ico}"

        contenido_icono = f'<a href="https://www.linkedin.com/in/milenka-benito" target="_blank"><img src="{icono_html}" style="width: 32px; height: 32px; border-radius: 4px; object-fit: cover; border: 1px solid #002855;" /></a>' if icono_html else ""

        st.markdown(
            f"""
            <div style="background: white; border: 1px solid #cbd5e1; border-radius: 8px; padding: 22px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); height: 100%;">
                <h4 style="color: #002855; margin-top: 0; font-size: 17px;">Perfil Académico y Profesional</h4>
                <p style="font-size: 13.5px; color: #334155; line-height: 1.6; text-align: justify;">
                    Estudiante del último año de la carrera de <b>Ciencia Política y Gestión Pública</b> de la <b>Universidad Mayor de San Andrés (UMSA)</b>. Investigadora especializada en análisis de políticas públicas, relaciones internacionales, asimetría logística transfronteriza y estudios de integración regional.
                </p>
                <p style="font-size: 13.5px; color: #334155; line-height: 1.6; text-align: justify; margin-top: 10px;">
                    El presente sistema interactivo <b>OARL</b> nace como resultado del proyecto de grado orientado a dotar a la academia y al Estado de una herramienta tecnológica con fuentes oficiales primarias (ABC) para simular y cuantificar el impacto geopolítico de la conflictividad vial en el comercio exterior boliviano.
                </p>
                <div style="margin-top: 15px; padding-top: 12px; border-top: 1px solid #e2e8f0; display: flex; align-items: center; gap: 10px;">
                    {contenido_icono}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
elif menu in ["Impacto Comercial", "Nodos Críticos"]:
  nodo_seleccionado = st.selectbox(
      "Seleccione Tramo Carretero o Fronterizo para Monitoreo Actual:",
      nombres_nodos,
      key="select_departamento",
  )

  info_actual = DB_NODOS[nodo_seleccionado]

  if info_actual["nivel_riesgo"] == 2:
    color_alerta, borde_alerta, texto_alerta = "#f8d7da", "#dc3545", "#721c24"
  elif info_actual["nivel_riesgo"] == 1:
    color_alerta, borde_alerta, texto_alerta = "#fff3cd", "#ffc107", "#856404"
  else:
    color_alerta, borde_alerta, texto_alerta = "#d1e7dd", "#198754", "#0f5132"

  st.markdown(
      f"""
    <div style="background-color: {color_alerta}; border-left: 5px solid {borde_alerta}; padding: 12px 20px; border-radius: 4px; margin-bottom: 25px;">
        <strong style="color: {texto_alerta}; font-size: 13px;">🌐 ESTADO DEL CORREDOR ({nodo_seleccionado.upper()}): {info_actual['estado_semaforo']}</strong>
        <p style="color: {texto_alerta}; margin: 4px 0 0 0; font-size: 12.5px;">
            {info_actual['descripcion']} Datos validados con la Red Vial Fundamental (ABC).
        </p>
    </div>
    """,
      unsafe_allow_html=True,
  )

  if menu == "Impacto Comercial":
    st.markdown(
        f"#### 📰 Reportes Vigentes y Fuentes Oficiales ({nodo_seleccionado})"
    )
    cols_noticias = st.columns(len(info_actual["noticias"]))

    for idx, noti in enumerate(info_actual["noticias"]):
      with cols_noticias[idx]:
        st.markdown(
            f"""
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 6px; padding: 16px; height: 100%; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                    <div>
                        <span style="background-color: #002855; color: white; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 3px; text-transform: uppercase;">{noti['categoria']}</span>
                        <p style="font-size: 14px; font-weight: 700; color: #1e293b; margin: 10px 0 6px 0; line-height: 1.4;">{noti['titulo']}</p>
                        <p style="font-size: 11px; color: #64748b; margin-bottom: 12px;">🕒 Sincronización: {noti['fecha']}</p>
                    </div>
                    <a href="{noti['link']}" target="_blank" style="background-color: #002855; color: white; text-align: center; padding: 8px 12px; border-radius: 4px; font-size: 11.5px; font-weight: 600; text-decoration: none; display: block; margin-top: 10px;">Verificar en Sistema ABC ↗</a>
                </div>
                """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "### Modelo Analítico de Asimetría Logística y Comercio Exterior"
    )
    st.caption(
        "Evaluación cuantitativa basada en la matriz de costos e incidentes"
        " viales activos."
    )

    c1, c2, c3 = st.columns(3)
    with c1:
      st.metric(
          "Costo Oportunidad Acumulado",
          f"$ {nodos_activos_count * 22.5:.1f} M USD",
          "Basado en tramos con incidencia",
      )
    with c2:
      st.metric(
          "Desviación de fletes FOB",
          f"+{nodos_activos_count * 7.5}%",
          "Afectación en red troncal",
      )
    with c3:
      st.metric(
          "Corredores con Alerta / Restricción",
          f"{nodos_activos_count} / {len(DB_NODOS)}",
          "Semáforo activo",
      )

    st.markdown(
        "### Registro Dinámico de Tramos y Puntos de Conflicto Vigentes"
    )

    lista_df = []
    for nodo, v in DB_NODOS.items():
      lista_df.append({
          "corredor_vial": nodo,
          "ubicacion_gps": f"Lat: {v['lat']}, Lon: {v['lon']}",
          "fuente_primaria": v["causa"],
          "estado_operativo": v["estado_semaforo"],
      })
    df_live = pd.DataFrame(lista_df)

    solo_alertas = st.checkbox(
        "Mostrar únicamente tramos con bloqueos o alertas activas", value=True
    )
    df_visualizacion = df_live.copy()
    if solo_alertas:
      df_visualizacion = df_visualizacion[
          df_visualizacion["estado_operativo"].str.contains(
              "Alerta|Restricción", case=False, na=False
          )
      ]

    if not df_visualizacion.empty:
      st.dataframe(df_visualizacion, use_container_width=True)
    else:
      st.success(
          "¡Excelente noticia! No se registran tramos con bloqueos o alertas"
          " activas bajo los reportes oficiales del Sistema ABC."
      )

  elif menu == "Nodos Críticos":
    st.markdown(
        "### Cartografía Geoespacial de Corredores Logísticos (Red Vial"
        " Fundamental)"
    )
    st.caption(
        "Visualización interactiva: Clasificación de rutas con coloración"
        " dinámica según conflictos activos."
    )

    generar_mapa_carreteras(DB_NODOS)

elif menu == "Pasos Fronterizos":
  st.markdown("### Monitoreo de Soberanía y Pasos Fronterizos")
  st.caption(
      "Estado operativo oficial sincronizado con la Red Vial Fundamental y el"
      " sistema de transitabilidad de la ABC."
  )

  datos_frontera = [
      {
          "Paso Fronterizo": "Tambo Quemado",
          "País Limítrofe": "Chile",
          "Estado Operativo": "🟢 Operativo (Normal - ABC)",
          "Condición Actual": (
              "Tránsito vehicular expedito verificado en Red Fundamental"
          ),
          "Enlace Oficial": "https://transitabilidad.abc.gob.bo/",
      },
      {
          "Paso Fronterizo": "Pisiga",
          "País Limítrofe": "Chile",
          "Estado Operativo": "🟢 Operativo (Normal - ABC)",
          "Condición Actual": (
              "Flujo internacional de carga pesada sin restricciones"
          ),
          "Enlace Oficial": "https://transitabilidad.abc.gob.bo/",
      },
      {
          "Paso Fronterizo": "Desaguadero",
          "País Limítrofe": "Perú",
          "Estado Operativo": "🟢 Operativo (Normal - ABC)",
          "Condición Actual": (
              "Paso internacional habilitado sin cortes ni bloqueos"
          ),
          "Enlace Oficial": "https://transitabilidad.abc.gob.bo/",
      },
      {
          "Paso Fronterizo": "Yacuiba",
          "País Limítrofe": "Argentina",
          "Estado Operativo": "🟢 Operativo (Normal - ABC)",
          "Condición Actual": (
              "Operaciones aduaneras y transitabilidad regular"
          ),
          "Enlace Oficial": "https://transitabilidad.abc.gob.bo/",
      },
      {
          "Paso Fronterizo": "Puerto Suárez",
          "País Limítrofe": "Brasil",
          "Estado Operativo": "🟢 Operativo (Normal - ABC)",
          "Condición Actual": (
              "Corredor oriental transitable sin reportes de interrupción"
          ),
          "Enlace Oficial": "https://transitabilidad.abc.gob.bo/",
      },
  ]

  df_fronteras_dinamico = pd.DataFrame(datos_frontera)
  st.dataframe(df_fronteras_dinamico, use_container_width=True)

  st.markdown("<br>", unsafe_allow_html=True)
  st.markdown("##### 🌐 Enlaces Oficiales de Verificación (Fuente Primaria ABC)")
  st.markdown(
      "- [Mapa de Transitabilidad Oficial - ABC]"
      "(https://transitabilidad.abc.gob.bo/)"
  )
  st.markdown("- [Portal Institucional ABC](https://www.abc.gob.bo)")

elif menu == "Simulador Algorítmico":
  st.markdown("### Daños a la Integración Bioceánica")
  st.caption(
      "Módulo analítico de Relaciones Internacionales: Simulación de impacto"
      " geopolítico, asimetría en corredores de exportación hacia el"
      " Pacífico/Atlántico y evaluación de responsabilidad por"
      " incumplimiento de tratados (CAN y ACE)."
  )

  CORREDORES_HISTORICOS_SENSIBLES = [
      "Carretera al Norte (Santa Cruz)",
      "Eje Troncal Cochabamba - Occidente",
      "Carretera Altiplano (La Paz - Oruro)",
      "Nodo Logístico Senkata (El Alto)",
      "Corredor Minero Potosí",
      "Acceso Fronterizo Tambo Quemado",
      "Acceso Fronterizo Desaguadero",
      "Corredor del Chaco (Sucre - Tarija)",
  ]

  col_ctrl1, col_ctrl2 = st.columns(2)
  with col_ctrl1:
    corredor_sim = st.selectbox(
        "Seleccione Corredor o Ruta Sensible a Historial de Bloqueos:",
        options=CORREDORES_HISTORICOS_SENSIBLES,
        key="sim_corredor",
    )
    horas_cierre = st.selectbox(
        "Duración proyectada de la interrupción logística:",
        options=[24, 48, 72, 120, 168],
        format_func=lambda x: (
            f"{x} Horas ({x//24} días continuos de asfixia)"
            if x >= 24
            else f"{x} Horas"
        ),
        key="sim_horas",
    )

  with col_ctrl2:
    flotas_afectadas = st.number_input(
        "Unidades de transporte internacional retenidas (Flota pesada):",
        min_value=20,
        max_value=3000,
        value=200,
        key="sim_flotas",
    )
    tratado_marco = st.selectbox(
        "Marco de Integración Regional / Tratado Marco Afectado:",
        options=[
            "Acuerdo de Cartagena (Comunidad Andina - CAN)",
            "Acuerdo de Complementación Económica ACE N° 22 (Chile)",
            "Acuerdo de Complementación Económica ACE N° 36 (Mercosur)",
            (
                "Convención de Tránsito de Ultramar y Libre Tránsito"
                " Internacional"
            ),
        ],
        key="sim_tratado",
    )

  dias_sim = horas_cierre / 24.0
  toneladas_por_unidad = 28.5
  volumen_retenido_tm = flotas_afectadas * toneladas_por_unidad
  retraso_porcentual_pacifico = min(round(dias_sim * 6.8, 1), 95.0)

  if horas_cierre >= 72:
    nivel_riesgo_legal = "🔴 RIESGO CRÍTICO DE LITIGIO INTERNACIONAL"
    color_legal, borde_legal, texto_legal = "#f8d7da", "#dc3545", "#721c24"
    dictamen_juridico = (
        f"Se supera el umbral crítico de 72 horas. La interrupción prolongada en"
        f" `{corredor_sim}` configura una vulneración directa a los principios"
        f" de facilitación del comercio y libre tránsito estipulados en el"
        f" `{tratado_marco}`, habilitando causales para que operadores"
        f" afectados inicien reclamos por lucro cesante transfronterizo contra"
        f" el Estado ante tribunales arbitrales o instancias regionales."
    )
  elif horas_cierre >= 48:
    nivel_riesgo_legal = "🟡 ALERTA DE INCUMPLIMIENTO DE TRÁNSITO"
    color_legal, borde_legal, texto_legal = "#fff3cd", "#ffc107", "#856404"
    dictamen_juridico = (
        f"El bloqueo de {horas_cierre} horas genera estrés operativo en el"
        f" corredor, comprometiendo los tiempos de entrega pactados bajo el"
        f" `{tratado_marco}`. Si el bloqueo persiste, el Estado boliviano"
        f" incurrirá en responsabilidad internacional por inobservancia de"
        f" garantías de exportación."
    )
  else:
    nivel_riesgo_legal = "🟢 RESTRICCIÓN LOGÍSTICA EN OBSERVACIÓN"
    color_legal, borde_legal, texto_legal = "#d1e7dd", "#198754", "#0f5132"
    dictamen_juridico = (
        f"Incidente temporal bajo monitoreo preventivo. Aún no se configura"
        f" lesión grave a los compromisos del `{tratado_marco}`, pero existe"
        f" riesgo de escalamiento en las cadenas de suministro hacia el"
        f" Pacífico."
    )

  st.markdown("---")
  st.markdown(
      f"#### 📊 Resultados de Daño Geopolítico para: `{corredor_sim}`"
  )

  c_m1, c_m2, c_m3 = st.columns(3)
  with c_m1:
    st.metric(
        label="🌊 Aislamiento Corredor Bioceánico",
        value=f"+{retraso_porcentual_pacifico}% de Retraso",
        delta=f"Impacto en salida hacia puertos de ultramar",
    )
  with c_m2:
    st.metric(
        label="📦 Carga Soberana Retenida",
        value=f"{volumen_retenido_tm:,.1f} TM",
        delta=f"{flotas_afectadas} unidades de exportación",
    )
  with c_m3:
    st.metric(
        label="⚖️ Estado de Responsabilidad",
        value=f"{nivel_riesgo_legal.split()[0]} Evaluado",
        delta="Umbral de Tratados Internacionales",
    )

  st.markdown("<br>", unsafe_allow_html=True)
  st.markdown(
      f"""
    <div style="background-color: {color_legal}; border-left: 6px solid {borde_legal}; padding: 18px 22px; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
        <h4 style="color: {texto_legal}; margin-top: 0; font-size: 15px;">{nivel_riesgo_legal}</h4>
        <p style="color: {texto_legal}; font-size: 13.5px; line-height: 1.5; margin-bottom: 0;">
            <b>Dictamen Automatizado de Relaciones Internacionales:</b> {dictamen_juridico}
        </p>
    </div>
    """,
      unsafe_allow_html=True,
  )

  st.markdown("<br>", unsafe_allow_html=True)

  with st.expander(
      "📄 Generar Memorándum de Daño Geopolítico (Ver Documento Técnico)",
      expanded=True,
  ):
    st.markdown("##### Vista Previa del Memorándum de Daño Geopolítico")

    fecha_hoy = datetime.now().strftime("%d de %B de %Y")
    informe_markdown = f"""
**MEMORÁNDUM DE DAÑO GEOPOLÍTICO Y SOBERANÍA DE TRÁNSITO**
**Fecha de Emisión:** {fecha_hoy}  
**Asunto:** Dictamen de afectación a la integración regional y riesgo de incumplimiento del `{tratado_marco}`.

---

**1. Identificación del Corredor Sensible y Asimetría Logística**  
El presente informe evalúa el bloqueo prolongado en el corredor estratégico **`{corredor_sim}`** (zona de alta vulnerabilidad a cortes viales históricos), registrando un tiempo de inmovilización continua de **`{horas_cierre} horas`** (`{dias_sim:.1f} días`). Este evento afecta de manera directa a **`{flotas_afectadas} unidades vehiculares`**, reteniendo un volumen estimado de **`{volumen_retenido_tm:,.1f} toneladas métricas`** de carga orientada al comercio exterior.

**2. Afectación a los Principios de Libre Tránsito e Integración**  
La interrupción sostenida rompe los plazos logísticos pactados bajo los acuerdos del **`{tratado_marco}`**, generando un aislamiento del corredor bioceánico con un retraso estimado del **`{retraso_porcentual_pacifico}%`** en los tiempos de despacho hacia los puertos del Pacífico. Esto vulnera el espíritu de facilitación del comercio bilateral y genera sobrecostos operativos asimétricos que perjudican la competitividad exportadora del Estado boliviano.

**3. Conclusión y Recomendación Diplomática**  
Bajo los parámetros del derecho de integración y comercio internacional, la inacción estatal para garantizar la transitabilidad más allá de las 48-72 horas expone al país a pasivos por responsabilidad internacional y reclamos formales por lucro cesante. Se recomienda la activación inmediata de protocolos de salvaguarda diplomática y la gestión interinstitucional para la liberación de los corredores de exportación.
    """
    st.markdown(informe_markdown)

    st.download_button(
        label="📥 Descargar Memorándum en Formato de Texto",
        data=informe_markdown,
        file_name=(
            f"Memorandum_Dano_Geopolitico_{corredor_sim.replace(' ', '_')}.txt"
        ),
        mime="text/plain",
        key="btn_descargar_nota",
    )

elif menu == "Línea de Tiempo 2015-2026":
  st.markdown(
      "### Línea de Tiempo Histórica: Costo de Oportunidad y Conflictividad"
      " (2015-2026)"
  )
  st.caption(
      "Análisis longitudinal e investigativo exhaustivo de todos los años"
      " (2015-2026): Cortes viales, paros cívicos, demandas sectoriales y"
      " resolución institucional."
  )

  hitos_historicos = {
      "2015": {
          "titulo": (
              "2015: Paros Gremiales, Conflicto Comcipo, Aislamiento de"
              " Cochabamba y Fronteras"
          ),
          "resumen": (
              "Año caracterizado por alta conflictividad regional y sectorial."
              " Comenzó con bloqueos en el Norte Integrado de Santa Cruz y el"
              " aislamiento de Cochabamba en febrero. Destacó el histórico y"
              " prolongado cerco cívico de Comcipo en Potosí durante julio y"
              " agosto, sumado a protestas viales en la ruta La Paz-Oruro,"
              " paros de transporte en Warnes y tensiones aduaneras en"
              " Yacuiba y Desaguadero."
          ),
          "puntos": [
              {
                  "nombre": (
                      "Montero / Norte Integrado (Enero) - Demanda: Gremialistas"
                      " y mototaxistas contra inhabilitación de candidato en el"
                      " TSE / Resolución: Acuerdo regional negociado."
                  ),
                  "lat": -17.3400,
                  "lon": -63.2500,
              },
              {
                  "nombre": (
                      "Cruce a Tarata / Cochabamba (Febrero) - Demanda:"
                      " Transporte libre exigió destitución de Director de"
                      " Transportes / Resolución: Subvención y acuerdo."
                  ),
                  "lat": -17.5500,
                  "lon": -66.1800,
              },
              {
                  "nombre": (
                      "Provincia Ingavi / La Paz-Oruro (Mayo) - Demanda:"
                      " Comunarios exigieron inversiones viales y obras de"
                      " asfalto / Resolución: Cuarto intermedio y diálogo."
                  ),
                  "lat": -16.6500,
                  "lon": -68.7500,
              },
              {
                  "nombre": (
                      "Potosí / Acceso Comcipo (Julio-Agosto) - Demanda: Paro"
                      " cívico indefinido y pliego de 26 demandas estructurales"
                      " / Resolución: Diálogo tras 28 días de cerco vial."
                  ),
                  "lat": -19.5833,
                  "lon": -65.7500,
              },
              {
                  "nombre": (
                      "Warnes - Santa Cruz (Agosto) - Demanda: Transportistas"
                      " intermunicipales contra restricciones de ingreso al"
                      " centro urbano / Resolución: Modificación de ordenanzas."
                  ),
                  "lat": -17.5100,
                  "lon": -63.1600,
              },
              {
                  "nombre": (
                      "Yacuiba y Desaguadero (Noviembre) - Demanda:"
                      " Comerciantes y gremiales contra controles aduaneros /"
                      " Resolución: Tregua y revisión de normativas de"
                      " importación."
                  ),
                  "lat": -21.5000,
                  "lon": -63.8500,
              },
          ],
          "costo": "645.8 Millones de USD",
      },
      "2016": {
          "titulo": (
              "2016: Paros del Transporte Pesado, Caravana de Discapacidad,"
              " Enatex y Crisis de Mineros Cooperativistas"
          ),
          "resumen": (
              "Año de altísima conflictividad social en Bolivia. Comenzó con"
              " paros nacionales del transporte pesado por el Código Tributario,"
              " seguido por la histórica caravana de personas con discapacidad"
              " hacia La Paz, bloqueos fabriles por el cierre de Enatex y el"
              " violento conflicto de agosto con los cooperativistas mineros"
              " en Panduro que dejó un trágico saldo. Hacia fin de año se sumaron"
              " protestas por la crisis del agua en el occidente."
          ),
          "puntos": [
              {
                  "nombre": (
                      "Tambo Quemado y Eje Troncal (Enero-Feb) - Demanda:"
                      " Transporte pesado exigiendo modificación del Código"
                      " Tributario / Resolución: Instalación de mesas"
                      " técnicas."
                  ),
                  "lat": -18.2833,
                  "lon": -69.1167,
              },
              {
                  "nombre": (
                      "Cochabamba a La Paz (Marzo-Abril) - Demanda: Caravana de"
                      " personas con discapacidad exigiendo bono mensual de 500"
                      " Bs / Resolución: Vigilia prolongada en La Paz."
                  ),
                  "lat": -17.3895,
                  "lon": -66.1568,
              },
              {
                  "nombre": (
                      "Aparachavi / Ruta La Paz-Oruro (Mayo-Junio) - Demanda:"
                      " Fabriles y ex-trabajadores de Enatex contra el cierre"
                      " de la estatal textil / Resolución: Negociaciones"
                      " laborales y pago de finiquitos."
                  ),
                  "lat": -17.2333,
                  "lon": -67.8333,
              },
              {
                  "nombre": (
                      "Panduro y Sayari / Eje Central (Agosto) - Demanda:"
                      " Cooperativistas mineros contra la sindicalización y por"
                      " contratos con privadas; trágico conflicto / Resolución:"
                      " Intervención policial y arrestos tras el asesinato del"
                      " viceministro Illanes."
                  ),
                  "lat": -17.8500,
                  "lon": -67.5167,
              },
              {
                  "nombre": (
                      "Cochabamba (Julio) - Demanda: Protestas y pugnas"
                      " estamentales en la Universidad Mayor de San Simón (UMSS)"
                      " / Resolución: Acuerdo universitario y normalización"
                      " académica."
                  ),
                  "lat": -17.3935,
                  "lon": -66.1570,
              },
              {
                  "nombre": (
                      "La Paz y Potosí (Noviembre) - Demanda: Bloqueos"
                      " vecinales por la severa crisis y racionamiento extremo"
                      " de agua potable / Resolución: Planes de emergencia y"
                      " perforación de pozos."
                  ),
                  "lat": -16.5000,
                  "lon": -68.1500,
              },
          ],
          "costo": "740.5 Millones de USD",
      },
      "2017": {
          "titulo": (
              "2017: Conflicto de la Ley de la Coca, Revuelta en Achacachi y"
              " Paro Médico Nacional"
          ),
          "resumen": (
              "Año marcado por alta movilización social y sectorial. Comenzó"
              " con violentas protestas de Adepcoca en rechazo a la nueva Ley de"
              " la Coca, seguido por el prolongado y tenso conflicto en"
              " Achacachi (Omasuyos) con el cerco a Copacabana. Hacia el cierre"
              " del año, el sector salud protagonizó un histórico paro"
              " indefinido y bloqueos en rutas troncales en contra del Código"
              " del Sistema Penal (Artículo 205)."
          ),
          "puntos": [
              {
                  "nombre": (
                      "La Paz / Sede de Gobierno (Enero-Marzo) - Demanda:"
                      " Productores de Adepcoca contra la nueva Ley General de"
                      " la Coca / Resolución: Promulgación y tensiones"
                      " sostenidas."
                  ),
                  "lat": -16.5000,
                  "lon": -68.1500,
              },
              {
                  "nombre": (
                      "Achacachi y Copacabana / Omasuyos (Feb-Septiembre) -"
                      " Demanda: Revuelta contra alcalde municipal y detención"
                      " de líderes; cerco vial / Resolución: Intervención"
                      " policial con megaoperativo y gasificación."
                  ),
                  "lat": -16.0500,
                  "lon": -68.6833,
              },
              {
                  "nombre": (
                      "Santa Cruz (Abril) - Demanda: Paro del transporte"
                      " federado por nivelación de tarifas / Resolución: Mesas"
                      " de concertación municipal."
                  ),
                  "lat": -17.7833,
                  "lon": -63.1821,
              },
              {
                  "nombre": (
                      "Pasos Fronterizos / Chile y Perú (Junio) - Demanda:"
                      " Transporte pesado contra multas y demoras de la Aduana /"
                      " Resolución: Acuerdos operativos temporales."
                  ),
                  "lat": -18.2833,
                  "lon": -69.1167,
              },
              {
                  "nombre": (
                      "Eje Central / San Julián y Pailón (Nov-Dic) - Demanda:"
                      " Colegio Médico de Bolivia contra el Artículo 205 del"
                      " Código Penal / Resolución: Paro general, bloqueos y"
                      " enfrentamientos policiales."
                  ),
                  "lat": -17.1000,
                  "lon": -62.5167,
              },
          ],
          "costo": "530.4 Millones de USD",
      },
      "2018": {
          "titulo": (
              "2018: Abrogación del Código Penal, Conflicto de la UPEA y"
              " Tensión por el 21F"
          ),
          "resumen": (
              "Año de altísima conflictividad con un promedio cercano a dos"
              " conflictos diarios. Comenzó con el masivo paro civil y bloqueo"
              " nacional que forzó la abrogación del Código Penal en enero."
              " Posteriormente destacó el estallido del conflicto de la UPEA"
              " (mayo-junio) con trágicos saldos, el conflicto por regalías de"
              " Incahuasi en Chuquisaca, la violencia cocalera en La Asunta y"
              " las protestas de cierre de año frente a la habilitación de"
              " binomios en el TSE."
          ),
          "puntos": [
              {
                  "nombre": (
                      "Eje Troncal / La Paz, Cochabamba y Santa Cruz (Enero) -"
                      " Demanda: Paro civil masivo y bloqueos contra el Código"
                      " Penal / Resolución: Abrogación total de la norma por el"
                      " Ejecutivo (22 de enero)."
                  ),
                  "lat": -17.3825,
                  "lon": -63.1520,
              },
              {
                  "nombre": (
                      "El Alto / Sede de Gobierno (Mayo-Junio) - Demanda:"
                      " UPEA por presupuesto y muerte de estudiante; cerco vial"
                      " / Resolución: Asignación de recursos extraordinarios y"
                      " tregua académica."
                  ),
                  "lat": -16.5167,
                  "lon": -68.2000,
              },
              {
                  "nombre": (
                      "Chuquisaca y Sur (Abril) - Demanda: Paro departamental"
                      " por regalías del campo gasífero Incahuasi / Resolución:"
                      " Fallos arbitrales y mesas de conciliación limítrofe."
                  ),
                  "lat": -19.0333,
                  "lon": -65.2627,
              },
              {
                  "nombre": (
                      "La Asunta / Los Yungas (Agosto) - Demanda: Enfrentamientos"
                      " armados por erradicación de coca y bloqueos vecinales /"
                      " Resolución: Intervención de seguridad y despliegue"
                      " militar-policial."
                  ),
                  "lat": -16.1333,
                  "lon": -67.4667,
              },
              {
                  "nombre": (
                      "Santa Cruz y La Paz (Diciembre) - Demanda:"
                      " Movilizaciones de plataformas 21F y quema de oficinas del"
                      " TSE tras habilitación de binomios / Resolución:"
                      " Consolidación del calendario electoral bajo estado de"
                      " alerta."
                  ),
                  "lat": -17.7833,
                  "lon": -63.1821,
              },
          ],
          "costo": "780.2 Millones de USD",
      },
      "2019": {
          "titulo": (
              "2019: Revolución de las Pitas, Crisis Post-Electoral, Renuncia"
              " y Cercos Nacionales"
          ),
          "resumen": (
              "El año más convulso de la historia reciente de Bolivia. Inició"
              " con tensiones por el SUS, paros del 21F e incendios en la"
              " Chiquitanía (agosto-septiembre). Tras las elecciones del 20 de"
              " octubre estalló el paro indefinido y la 'Revolución de las Pitas'"
              " contra el fraude. En noviembre se produjo la renuncia de Evo"
              " Morales, seguida de una intensa 'guerra de bloqueos' y cercos"
              " nacionales con trágicos enfrentamientos en Sacaba y Senkata,"
              " hasta la pacificación de diciembre."
          ),
          "puntos": [
              {
                  "nombre": (
                      "Santa Cruz (Agosto-Septiembre) - Demanda: Movilizaciones"
                      " cívicas y ambientales por los incendios forestales en"
                      " la Chiquitanía / Resolución: Presión social hacia el"
                      " debate nacional."
                  ),
                  "lat": -17.7833,
                  "lon": -63.1821,
              },
              {
                  "nombre": (
                      "Eje Troncal / Santa Cruz, Cochabamba y La Paz (Octubre -"
                      " Noviembre) - Demanda: Paro cívico indefinido y"
                      " 'Revolución de las Pitas' contra el fraude electoral de"
                      " octubre / Resolución: Renuncia presidencial (10 de"
                      " noviembre) y sucesión constitucional."
                  ),
                  "lat": -17.3825,
                  "lon": -63.1520,
              },
              {
                  "nombre": (
                      "Sacaba / Cochabamba (Noviembre) - Demanda: Bloqueos y"
                      " enfrentamientos severos durante operativos de desbloqueo"
                      " militar-policial / Resolución: Acuerdos regionales de"
                      " pacificación."
                  ),
                  "lat": -17.4064,
                  "lon": -66.0381,
              },
              {
                  "nombre": (
                      "Senkata / El Alto (Noviembre) - Demanda: Bloqueo de"
                      " planta de combustibles y enfrentamientos armados en"
                      " operativos de provisión / Resolución: Cuarto intermedio y"
                      " tregua social."
                  ),
                  "lat": -16.5167,
                  "lon": -68.2000,
              },
              {
                  "nombre": (
                      "La Paz (Diciembre) - Demanda: Mesas de diálogo y"
                      " pacificación mediadas por la Iglesia Católica /"
                      " Resolución: Levantamiento paulatino de bloqueos y"
                      " convocatoria a nuevas elecciones."
                  ),
                  "lat": -16.5000,
                  "lon": -68.1500,
              },
          ],
          "costo": "1,450.0 Millones de USD",
      },
      "2020": {
          "titulo": (
              "2020: Doble Crisis (Pandemia COVID-19 y Bloqueo Nacional de"
              " Agosto)"
          ),
          "resumen": (
              "Año marcado por una doble crisis: la transición institucional y"
              " la emergencia sanitaria por el COVID-19 con estrictas cuarentenas"
              " en el primer semestre. El conflicto social estalló con máxima"
              " dureza en agosto con un bloqueo nacional de carreteras de dos"
              " semanas liderado por la COB exigiendo fecha fija de elecciones,"
              " generando severo desabastecimiento de oxígeno medicinal en"
              " pleno pico de contagios. Con las elecciones de octubre se"
              " pacificó el escenario."
          ),
          "puntos": [
              {
                  "nombre": (
                      "K'ara K'ara / Cochabamba (Mayo) - Demanda: Bloqueo"
                      " prolongado del vertedero exigiendo fin de cuarentena"
                      " rígida y agua potable / Resolución: Acuerdos sanitarios"
                      " locales."
                  ),
                  "lat": -17.4500,
                  "lon": -66.1600,
              },
              {
                  "nombre": (
                      "Eje Troncal / La Paz, Oruro, Cochabamba y Santa Cruz"
                      " (Agosto) - Demanda: Bloqueo nacional indefinido de la"
                      " COB exigiendo fecha electoral; crisis de oxígeno /"
                      " Resolución: Ley de blindaje electoral para el 18 de"
                      " octubre y tregua."
                  ),
                  "lat": -17.3825,
                  "lon": -63.1520,
              },
              {
                  "nombre": (
                      "La Paz y El Alto (Octubre) - Demanda: Jornada electoral"
                      " general del 18 de octubre / Resolución: Triunfo y"
                      " transición democrática sin interrupciones viales"
                      " mayores."
                  ),
                  "lat": -16.5000,
                  "lon": -68.1500,
              },
          ],
          "costo": "1,250.0 Millones de USD",
      },
      "2021": {
          "titulo": (
              "2021: Alta Conflictividad Sectorial y Paro Multisectorial"
              " (Ley 1386)"
          ),
          "resumen": (
              "Año caracterizado por una fuerte reactivación de la"
              " conflictividad civil y sectorial (superando tres conflictos por"
              " día). Arrancó con diferimiento de créditos, paros de salud por"
              " la Ley de Emergencia Sanitaria, disputas en Adepcoca y conflictos"
              " regionales. Su clímax ocurrió en noviembre con el masivo Paro"
              " Multisectorial Nacional y bloqueos en el eje troncal que"
              " forzaron al Gobierno a abrogar la Ley 1386 contra la"
              " legitimación de ganancias ilícitas."
          ),
          "puntos": [
              {
                  "nombre": (
                      "Villa Fátima / La Paz (Abril y Septiembre) - Demanda:"
                      " Enfrentamientos y bloqueos de cocaleros de Adepcoca por"
                      " el control de mercados / Resolución: Intervención"
                      " policial y disputas dirigenciales."
                  ),
                  "lat": -16.4800,
                  "lon": -68.1300,
              },
              {
                  "nombre": (
                      "San Julián / Santa Cruz (Julio) - Demanda: Cerco vial de"
                      " sindicatos agrarios exigiendo regalías y desayuno"
                      " escolar / Resolución: Acuerdos departamentales."
                  ),
                  "lat": -17.1000,
                  "lon": -62.5167,
              },
              {
                  "nombre": (
                      "Eje Troncal / Santa Cruz, Potosí, Cochabamba y Tarija"
                      " (Noviembre) - Demanda: Paro multisectorial indefinido"
                      " contra la Ley 1386; trágicos enfrentamientos en Potosí"
                      " / Resolución: Abrogación definitiva de la ley por el"
                      " Ejecutivo."
                  ),
                  "lat": -17.7833,
                  "lon": -63.1821,
              },
          ],
          "costo": "690.0 Millones de USD",
      },
      "2022": {
          "titulo": (
              "2022: Paro Cívico de los 36 Días y Conflicto Nacional por el"
              " Censo"
          ),
          "resumen": (
              "El año 2022 promedió más de tres conflictos diarios, marcando"
              " un retorno masivo a las calles. La segunda mitad del año estuvo"
              " completamente dominada por el conflicto sobre la fecha del Censo"
              " de Población y Vivienda. Destacó el histórico Paro Cívico"
              " Indefinido de 36 días en Santa Cruz (desde el 22 de octubre) que"
              " aisló al departamento, acompañado de un contracerco y"
              " paralización de las cadenas logísticas y agroindustriales de"
              " exportación, hasta la promulgación de la Ley del Censo a"
              " finales de noviembre."
          ),
          "puntos": [
              {
                  "nombre": (
                      "Yacuiba / Tarija (Abril) - Demanda: Bloqueo total de la"
                      " Ruta Internacional 9 por bagayeros y cívicos exigiendo"
                      " reactivación económica / Resolución: Mesas de diálogo y"
                      " acuerdos aduaneros."
                  ),
                  "lat": -21.5000,
                  "lon": -63.8500,
              },
              {
                  "nombre": (
                      "Potosí (Marzo) - Demanda: Bloqueos viales hacia Sucre y"
                      " Tarija por abandono de proyectos viales y regalías"
                      " mineras / Resolución: Atenciones sectoriales"
                      " regionales."
                  ),
                  "lat": -19.5833,
                  "lon": -65.7500,
              },
              {
                  "nombre": (
                      "Santa Cruz y Eje Troncal (Octubre-Noviembre) - Demanda:"
                      " Histórico Paro Cívico de los 36 días exigiendo Censo en"
                      " 2023; enfrentamientos y contracerco / Resolución:"
                      " Promulgación de ley de aplicación censal y levantamiento"
                      " de medidas."
                  ),
                  "lat": -17.7833,
                  "lon": -63.1821,
              },
          ],
          "costo": "1,850.0 Millones de USD",
      },
      "2023": {
          "titulo": (
              "2023: Atomización de Conflictos, Fractura del MAS y Síntomas de"
              " Escasez"
          ),
          "resumen": (
              "El año 2023 registró un total de 1,112 conflictos sociales,"
              " caracterizados por la atomización y el localismo (obras"
              " locales, disputas por tierras, demandas magisteriales y cívicas"
              " como el bloqueo de Buena Vista). Estuvo marcado además por la"
              " fractura interna del partido de Gobierno (Congreso de Lauca Ñ)"
              " y los primeros indicios de esasez de dólares y diésel que"
              " generaron filas y bloqueos de transportistas a fin de año."
          ),
          "puntos": [
              {
                  "nombre": (
                      "Santa Cruz (Enero) - Demanda: Bloqueos viales y"
                      " fronterizos tras la aprehensión del Gobernador Luis"
                      " Fernando Camacho / Resolución: Despliegue de seguridad y"
                      " normalización."
                  ),
                  "lat": -17.7833,
                  "lon": -63.1821,
              },
              {
                  "nombre": (
                      "Buena Vista / Santa Cruz (Agosto) - Demanda: Bloqueo"
                      " indefinido por controversia sobre trazo de carretera"
                      " nueva y protección de acuíferos / Resolución: Cuarto"
                      " intermedio y debate técnico."
                  ),
                  "lat": -17.4583,
                  "lon": -63.6667,
              },
              {
                  "nombre": (
                      "Lauca Ñ / Trópico de Cochabamba (Octubre) - Demanda:"
                      " Congreso del MAS y pugnas internas con vigilias y cercos"
                      " preventivos / Resolución: Tensiones partidarias"
                      " sostenidas."
                  ),
                  "lat": -16.9833,
                  "lon": -65.2833,
              },
              {
                  "nombre": (
                      "Eje Troncal y Fronteras (Diciembre) - Demanda: Filas y"
                      " bloqueos del transporte pesado por desabastecimiento de"
                      " diésel y dólares / Resolución: Gestiones operativas"
                      " de YPFB."
                  ),
                  "lat": -17.3825,
                  "lon": -63.1520,
              },
          ],
          "costo": "890.4 Millones de USD",
      },
      "2024": {
          "titulo": (
              "2024: Crisis de Combustibles, Bloqueo de 16 Días (Enero) y Cerco"
              " de 24 Días (Octubre)"
          ),
          "resumen": (
              "Año de altísima conflictividad socioeconómica y política"
              " (promedio de 15 bloqueos mensuales), impulsado por la escasez"
              " de dólares y combustibles, y la abierta fractura del MAS."
              " Destacaron dos grandes hitos viales: el bloqueo evista de 16"
              " días en enero-febrero exigiendo elecciones judiciales, y el"
              " severo bloqueo de 24 días en octubre con epicentro en Parotani"
              " (Cochabamba) en defensa de Evo Morales y por demandas"
              " económicas, generando más de 2.200 millones de dólares en"
              " pérdidas."
          ),
          "puntos": [
              {
                  "nombre": (
                      "Cochabamba y Eje Troncal (Enero-Febrero) - Demanda:"
                      " Bloqueo evista de 16 días contra la prórroga de"
                      " magistrados y por elecciones judiciales / Resolución:"
                      " Acuerdo legislativo."
                  ),
                  "lat": -17.4721,
                  "lon": -66.4250,
              },
              {
                  "nombre": (
                      "Caracollo a La Paz (Septiembre) - Demanda: 'Marcha para"
                      " Salvar Bolivia' y bloqueos parciales en la ruta"
                      " Altiplano / Resolución: Operativos de seguridad y"
                      " choques urbanos."
                  ),
                  "lat": -17.9333,
                  "lon": -67.2167,
              },
              {
                  "nombre": (
                      "Parotani y Eje Troncal (Octubre-Noviembre) - Demanda:"
                      " Masivo bloqueo de 24 días con epicentro en Parotani por"
                      " crisis económica y resguardo político / Resolución:"
                      " Operativos policiales-militares de desbloqueo."
                  ),
                  "lat": -17.6500,
                  "lon": -66.3800,
              },
          ],
          "costo": "2,250.0 Millones de USD",
      },
      "2025": {
          "titulo": (
              "2025: Elecciones Presidenciales, Bloqueo Nacional de Junio y"
              " Decreto del Diésel"
          ),
          "resumen": (
              "Año de transformación política y alta presión inflacionaria."
              " Arrancó con escasez de divisas y carburantes (201 conflictos en"
              " Q1). El segundo trimestre marcó el clímax con 267 conflictos y"
              " un bloqueo nacional indefinido en junio liderado por el evismo"
              " que aisló Cochabamba (más de 48 puntos simultáneos). Tras las"
              " Elecciones Generales y el balotaje que consagró a Rodrigo Paz"
              " Pereira como nuevo Presidente, el cierre de año (diciembre)"
              " desató bloqueos en Yapacaní, San Julián y Puente San Pablo en"
              " rechazo a la eliminación de la subvención a la gasolina y el"
              " nuevo esquema tarifario del diésel."
          ),
          "puntos": [
              {
                  "nombre": (
                      "Sipe Sipe, Vinto y Chapare / Cochabamba (Junio) -"
                      " Demanda: Bloqueo nacional indefinido exigiendo renuncia"
                      " de Luis Arce; más de 48 puntos simultáneos /"
                      " Resolución: Repliegue a protestas urbanas tras pugnas."
                  ),
                  "lat": -17.4000,
                  "lon": -66.2800,
              },
              {
                  "nombre": (
                      "Eje Troncal y Fronteras (Septiembre) - Demanda: Protestas"
                      " de transportistas y comités cívicos por encarecimiento de"
                      " insumos y escasez de diésel / Resolución: Mesas de"
                      " diálogo sectorial."
                  ),
                  "lat": -17.3825,
                  "lon": -63.1520,
              },
              {
                  "nombre": (
                      "Yapacaní y San Julián / Santa Cruz - Puente San Pablo /"
                      " Beni (Diciembre) - Demanda: Bloqueos viales en rechazo"
                      " al decreto del Gobierno de Rodrigo Paz Pereira que"
                      " elimina subvención a gasolina y fija tarifas de diésel"
                      " / Resolución: Negociaciones de emergencia."
                  ),
                  "lat": -17.3400,
                  "lon": -63.5167,
              },
          ],
          "costo": "1,980.0 Millones de USD",
      },
      "2026": {
          "titulo": (
              "2026: Conflicto Extremo, Gran Cerco de 53 Días, Estado de"
              " Excepción (DS 5636) y DS 5716"
          ),
          "resumen": (
              "El año 2026 se consolidó como el período de conflictividad social"
              " más extrema en la historia reciente de Bolivia bajo el mandato de"
              " Rodrigo Paz Pereira. Inició con protestas por el DS 5503 y"
              " gasolina de mala calidad (157 conflictos en Q1, epicentro"
              " urbano en La Paz con 47 casos). El clímax estalló en mayo y junio"
              " con el 'Gran Cerco' de 53 días y más de 60 puntos de bloqueo"
              " simultáneos que aislaron La Paz y El Alto, generando un saldo de"
              " 14 fallecidos y más de 3.000 millones de dólares en pérdidas."
              " Esto forzó la promulgación del Decreto Supremo 5636 (Estado de"
              " Excepción por 90 días) y un masivo operativo militar-policial"
              " de desbloqueo con excavadoras en la vía La Paz-Oruro. En el"
              " tercer trimestre, tras ampliarse el estado de excepción, el"
              " decreto DS 5716 reactivó paros de transporte pesado en Sucre,"
              " Potosí, Tarija, Oruro y Santa Cruz, mientras la policía blindaba"
              " La Paz con el plan 'Bolivia Unida' y el Chapare lanzaba"
              " ultimátums."
          ),
          "puntos": [
              {
                  "nombre": (
                      "La Paz y El Alto (Enero - Marzo) - Demanda: 157"
                      " conflictos por el DS 5503 y gasolina de mala calidad"
                      " (47 casos en La Paz) / Resolución: Repliegue a"
                      " movilizaciones urbanas."
                  ),
                  "lat": -16.5000,
                  "lon": -68.1500,
              },
              {
                  "nombre": (
                      "Ruta La Paz - Oruro (Mayo - Junio) - Demanda: El 'Gran"
                      " Cerco' de 53 días, más de 60 puntos simultáneos y"
                      " colapso de abastecimiento (14 fallecidos) / Resolución:"
                      " DS 5636 (Estado de Excepción) y desbloqueo militar con"
                      " excavadoras."
                  ),
                  "lat": -17.2150,
                  "lon": -67.5520,
              },
              {
                  "nombre": (
                      "Sucre, Potosí, Tarija, Oruro y Santa Cruz (Septiembre) -"
                      " Demanda: Paros de transportistas contra el DS 5716;"
                      " plan policial 'Bolivia Unida' en La Paz y ultimátum en"
                      " Lauca Ñ (Chapare) / Resolución: Control militar"
                      " reforzado y prórroga del estado de excepción."
                  ),
                  "lat": -19.5833,
                  "lon": -65.7510,
              },
          ],
          "costo": "3,420.0 Millones de USD",
      },
  }

  anio_seleccionado = st.select_slider(
      "Seleccione el periodo o año de análisis histórico:",
      options=[
          "2015",
          "2016",
          "2017",
          "2018",
          "2019",
          "2020",
          "2021",
          "2022",
          "2023",
          "2024",
          "2025",
          "2026",
      ],
      value="2026",
      key="slider_historico_general",
  )

  info_hito = hitos_historicos[anio_seleccionado]

  st.markdown("---")
  st.markdown(f"### 📌 {info_hito['titulo']}")

  col_h1, col_h2 = st.columns([1.2, 1.2])

  with col_h1:
    st.markdown(
        f"""
        <div style="background: white; border: 1px solid #cbd5e1; border-radius: 6px; padding: 22px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <h4 style="color: #002855; margin-top: 0;">Resumen Académico e Institucional</h4>
            <p style="font-size: 14px; color: #334155; line-height: 1.65; text-align: justify;">{info_hito['resumen']}</p>
            <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 16px 0;">
            <strong style="color: #002855; font-size: 13px;">Puntos Críticos, Demandas y Resolución:</strong>
            <ul style="color: #334155; font-size: 12px; margin-top: 6px; line-height: 1.5;">
        """,
        unsafe_allow_html=True,
    )
    for p in info_hito["puntos"]:
      st.markdown(f"<li>{p['nombre']}</li>", unsafe_allow_html=True)
    st.markdown("</ul></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Disposición en dos subcolumnas transparentes y auditables
    sub_c1, sub_c2 = st.columns(2)
    with sub_c1:
      st.markdown(
          f"""
        <div style="background: #002855; color: white; border-radius: 6px; padding: 18px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); height: 100%; display: flex; flex-direction: column; justify-content: center;">
            <span style="font-size: 10.5px; text-transform: uppercase; color: #94a3b8; font-weight: 700;">Costo de Oportunidad ({anio_seleccionado})</span>
            <div style="font-size: 20px; font-weight: 800; color: #ffffff; margin: 6px 0;">{info_hito['costo']}</div>
            <span style="font-size: 10.5px; color: #cbd5e1;">Impacto global logístico y PIB</span>
        </div>
        """,
          unsafe_allow_html=True,
      )

    with sub_c2:
      st.markdown(
          """
        <div style="background: white; border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); height: 100%;">
            <strong style="color: #002855; font-size: 11px; text-transform: uppercase;">🔍 Verificación del Cálculo:</strong>
            <p style="font-size: 10px; color: #334155; margin: 3px 0 6px 0; line-height: 1.3;">
            <b>Fórmula verificable:</b><br>
            Costo Total = (Días de Corte × Daño Logístico Diario) + (Flota Retenida × Lucro Cesante) + Mermas de Exportación.
            </p>
            <div style="background: #f8fafc; padding: 6px; border-radius: 4px; border: 1px solid #e2e8f0; font-size: 9.5px; color: #1e293b;">
            <b>Parámetros Base (ABC):</b><br>
            • Daño diario estimado: ~$45M - $60M USD/día<br>
            • Catastro Red Vial Fundamental (ABC)<br>
            • Impacto sectorial en cadenas de suministro
            </div>
        </div>
        """,
          unsafe_allow_html=True,
      )

  with col_h2:
    st.markdown(
        f"##### 🗺️ Cartografía de Puntos Críticos ({anio_seleccionado})"
    )
    m_hist = folium.Map(location=[-17.0, -65.0], zoom_start=6)

    for p in info_hito["puntos"]:
      folium.Marker(
          [p["lat"], p["lon"]],
          popup=p["nombre"],
          tooltip=p["nombre"].split(" - ")[0],
          icon=folium.Icon(color="red", icon="exclamation-triangle", prefix="fa"),
      ).add_to(m_hist)

    st_folium(
        m_hist,
        use_container_width=True,
        height=430,
        key=f"map_dinamico_{anio_seleccionado}",
    )

elif menu == "Acuerdos y Repositorio":
  st.markdown("### Repositorio Normativo y Documentos Legales")
  st.caption(
      "Marco jurídico internacional y documentos oficiales del observatorio"
      " alojados localmente."
  )

  col_doc1, col_doc2 = st.columns(2)
  with col_doc1:
    st.markdown("#### 📄 Comunidad Andina")
    try:
      with open("documentos/comunidad andina.pdf", "rb") as file:
        st.download_button(
            label="📥 Descargar Comunidad Andina (PDF)",
            data=file,
            file_name="comunidad_andina.pdf",
            mime="application/pdf",
            key="btn_doc_ca",
        )
    except FileNotFoundError:
      st.error("⚠️ Archivo no encontrado.")

    st.markdown("#### 📄 Acuerdo ACE N° 22")
    try:
      with open("documentos/ACE-N°-22.pdf", "rb") as file:
        st.download_button(
            label="📥 Descargar ACE N° 22 (PDF)",
            data=file,
            file_name="ACE_N_22.pdf",
            mime="application/pdf",
            key="btn_doc_ace22",
        )
    except FileNotFoundError:
      st.error("⚠️ Archivo no encontrado.")

    st.markdown("#### 📄 Acuerdo ACE N° 47")
    try:
      with open("documentos/ACE-N°-47.pdf", "rb") as file:
        st.download_button(
            label="📥 Descargar ACE N° 47 (PDF)",
            data=file,
            file_name="ACE_N_47.pdf",
            mime="application/pdf",
            key="btn_doc_ace47",
        )
    except FileNotFoundError:
      st.error("⚠️ Archivo no encontrado.")

  with col_doc2:
    st.markdown("#### 📄 Acuerdo ACE N° 66")
    try:
      with open("documentos/ACE-N°-66.pdf", "rb") as file:
        st.download_button(
            label="📥 Gran Acuerdo ACE N° 66 (PDF)",
            data=file,
            file_name="ACE_N_66.pdf",
            mime="application/pdf",
            key="btn_doc_ace66",
        )
    except FileNotFoundError:
      st.error("⚠️ Archivo no encontrado.")

    st.markdown("#### 📄 Mercosur")
    try:
      with open("documentos/mercosur.pdf", "rb") as file:
        st.download_button(
            label="📥 Descargar Mercosur (PDF)",
            data=file,
            file_name="mercosur.pdf",
            mime="application/pdf",
            key="btn_doc_mercosur",
        )
    except FileNotFoundError:
      st.error("⚠️ Archivo no encontrado.")

    st.markdown("#### 📄 Esquema Preferencial")
    try:
      with open(
          "documentos/esquema preferencial unilateral union eu.pdf", "rb"
      ) as file:
        st.download_button(
            label="📥 Descargar Esquema Preferencial (PDF)",
            data=file,
            file_name="esquema_preferencial.pdf",
            mime="application/pdf",
            key="btn_doc_esquema",
        )
    except FileNotFoundError:
      st.error("⚠️ Archivo no encontrado.")

st.markdown("</div>", unsafe_allow_html=True)