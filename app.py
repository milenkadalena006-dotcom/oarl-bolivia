import os
import re
import time
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from urllib.parse import quote_plus
import feedparser
from datetime import datetime, timedelta

# Importar el mapa modular desde la carpeta cartografia
from mapa_vial import generar_mapa_carreteras
# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="OARL | Observatorio de Alerta y Riesgo Logístico e Independiente",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 2. ESTILOS CSS INSTITUCIONALES
st.markdown("""
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
        padding: 12px 40px;
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
        padding: 30px 40px;
        color: white;
        border-bottom: 4px solid #008060;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        width: 100vw !important;
        box-sizing: border-box;
        margin: 0 !important;
    }
    .portal-title {
        font-size: 28px;
        font-weight: 800;
        letter-spacing: 0.5px;
        margin: 0;
        color: #ffffff;
        text-transform: uppercase;
    }
    .portal-subtitle {
        font-size: 13.5px;
        font-weight: 400;
        color: #94a3b8;
        margin-top: 6px;
        letter-spacing: 0.3px;
    }

    .content-body { padding: 30px 40px; width: 100%; box-sizing: border-box; }

    div.stButton > button {
        background-color: #002855 !important;
        color: #ffffff !important;
        border: 1px solid #004080 !important;
        font-weight: 600 !important;
        font-size: 11px !important;
        border-radius: 4px !important;
        transition: all 0.2s ease-in-out;
        width: 100% !important;
    }
    div.stButton > button:hover {
        background-color: #003366 !important;
        border-color: #008060 !important;
        color: #ffffff !important;
    }

    [data-testid="stMetricValue"] { color: #002855 !important; font-weight: 800 !important; font-size: 26px !important; }
    [data-testid="stMetricLabel"] { color: #334155 !important; font-weight: 700 !important; font-size: 12px !important; text-transform: uppercase; }
    </style>
""", unsafe_allow_html=True)

# 3. MATRICES DE COORDENADAS CON CONSULTAS DINÁMICAS Y SEMÁFORO INTELIGENTE
TERRITORIOS_BASE = {
    "Carretera al Norte (Santa Cruz)": {
        "lat": -17.3825, "lon": -63.1520,
        "query": "montero puerto pailon bloqueos santa cruz carretera"
    },
    "Eje Troncal Cochabamba - Occidente": {
        "lat": -17.4721, "lon": -66.4250,
        "query": "parotani sipe sipe bloqueos cochabamba carretera"
    },
    "Carretera Altiplano (La Paz - Oruro)": {
        "lat": -17.2150, "lon": -67.5520,
        "query": "conani apacheta bloqueos carretera la paz oruro"
    },
    "Nodo Logístico Senkata (El Alto)": {
        "lat": -16.5500, "lon": -68.2100,
        "query": "senkata el alto bloqueos combustible ypfb"
    },
    "Corredor Minero Potosí": {
        "lat": -19.7820, "lon": -65.7510,
        "query": "potosí carretera norte cooperativistas bloqueos"
    },
    "Acceso Fronterizo Tambo Quemado": {
        "lat": -18.2833, "lon": -69.1167,
        "query": "tambo quemado frontera chile bloqueos paso"
    },
    "Acceso Fronterizo Desaguadero": {
        "lat": -16.5650, "lon": -69.0380,
        "query": "desaguadero frontera peru bloqueos paso"
    },
    "Corredor del Chaco (Sucre - Tarija)": {
        "lat": -20.0210, "lon": -63.5210,
        "query": "yacuiba chaco bloqueos hidrocarburos carretera"
    }
}

@st.cache_data(ttl=300)
def escanear_noticias_en_vivo():
    db_dinamica = {}
    ahora = datetime.now()
    limite_ttl_horas = 72 # Vigencia de 3 días
    
    for nodo_key, data in TERRITORIOS_BASE.items():
        rss_url = f"https://news.google.com/rss/search?q={quote_plus(data['query'])}&hl=es-419&gl=BO&ceid=BO:es-419"
        feed = feedparser.parse(rss_url)
        
        noticias_validas = []
        estado_semaforo = "🟢 Estable / Operativo"
        nivel_riesgo_code = 0 # 0: Verde, 1: Amarillo, 2: Rojo
        
        if feed.entries:
            for entry in feed.entries:
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                
                if pub_date:
                    diferencia_horas = (ahora - pub_date).total_seconds() / 3600.0
                    
                    if 0 <= diferencia_horas <= limite_ttl_horas:
                        fecha_str = pub_date.strftime("%d de %B de %Y - %H:%M")
                        titulo_lower = entry.title.lower()
                        
                        if any(w in titulo_lower for w in ["bloqueo", "cortado", "protesta", "toma", "cierre total"]):
                            estado_semaforo = "🔴 Alerta Activa (Bloqueo)"
                            nivel_riesgo_code = 2
                        elif any(w in titulo_lower for w in ["restringido", "obras", "horario", "lento", "mantenimiento", "precaución", "retraso"]):
                            if nivel_riesgo_code < 2:
                                estado_semaforo = "🟡 Restricción / Obras"
                                nivel_riesgo_code = max(nivel_riesgo_code, 1)

                        noticias_validas.append({
                            "categoria": estado_semaforo,
                            "titulo": entry.title,
                            "fecha": fecha_str,
                            "link": entry.link,
                            "horas_antiguedad": round(diferencia_horas, 1)
                        })
                        if len(noticias_validas) >= 3:
                            break
        
        db_dinamica[nodo_key] = {
            "punto": f"Tramo / Nodo: {nodo_key}",
            "lat": data["lat"],
            "lon": data["lon"],
            "descripcion": f"Monitoreo con TTL de 72h y semáforo dinámico en corredor: {nodo_key}.",
            "causa": "Verificación algorítmica con decaimiento temporal",
            "estado_semaforo": estado_semaforo,
            "nivel_riesgo": nivel_riesgo_code,
            "noticias": noticias_validas if noticias_validas else [{
                "categoria": "🟢 Estable / Operativo",
                "titulo": f"Sin incidentes viales reportados en las últimas 72 horas en {nodo_key}",
                "fecha": "Actualizado en tiempo real",
                "link": f"https://www.google.com/search?q={quote_plus(data['query'])}&tbm=nws"
            }]
        }
    return db_dinamica

DB_NODOS = escanear_noticias_en_vivo()

# 4. BARRA SUPERIOR
st.markdown("""
    <div class="top-bar-full">
        <div>Sistema Automatizado con Semáforo Dinámico y TTL de 72h</div>
        <div>Módulo Académico Institucional - UMSA | <b>Ciclo 2026</b></div>
    </div>
""", unsafe_allow_html=True)

# 5. ENCABEZADO PRINCIPAL
st.markdown("""
    <div class="portal-header-full">
        <div class="portal-title">OARL — Observatorio de Alerta y Riesgo Logístico</div>
        <div class="portal-subtitle">Plataforma con Semáforos Multicriterio y Precisión en Corredores Viales</div>
    </div>
""", unsafe_allow_html=True)

if 'menu_activo' not in st.session_state:
    st.session_state.menu_activo = "Impacto Comercial"

st.markdown('<div class="content-body">', unsafe_allow_html=True)

col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

def render_boton(col, label):
    is_active = (st.session_state.menu_activo == label)
    if is_active:
        st.markdown(f"""
        <style>
        div[data-testid="stHorizontalBlock"] > div:nth-child({col}) button {{
            background-color: #ffffff !important;
            color: #000000 !important;
            border: 2px solid #002855 !important;
            font-weight: 800 !important;
        }}
        </style>
        """, unsafe_allow_html=True)
    with col:
        if st.button(label, use_container_width=True, key=f"btn_nav_{label}"):
            st.session_state.menu_activo = label
            st.rerun()

render_boton(col_m1, "Impacto Comercial")
render_boton(col_m2, "Nodos Críticos")
render_boton(col_m3, "Pasos Fronterizos")
render_boton(col_m4, "Simulador Algorítmico")
render_boton(col_m5, "Acuerdos y Repositorio")

st.markdown("---")

menu = st.session_state.menu_activo
nombres_nodos = list(DB_NODOS.keys())
nodos_activos_count = sum(1 for v in DB_NODOS.values() if v["nivel_riesgo"] > 0)

if menu in ["Impacto Comercial", "Nodos Críticos"]:
    nodo_seleccionado = st.selectbox(
        "Seleccione Tramo Carretero o Fronterizo para Monitoreo Actual:",
        nombres_nodos,
        key="select_departamento"
    )

    info_actual = DB_NODOS[nodo_seleccionado]
    
    if info_actual["nivel_riesgo"] == 2:
        color_alerta, borde_alerta, texto_alerta = "#f8d7da", "#dc3545", "#721c24"
    elif info_actual["nivel_riesgo"] == 1:
        color_alerta, borde_alerta, texto_alerta = "#fff3cd", "#ffc107", "#856404"
    else:
        color_alerta, borde_alerta, texto_alerta = "#d1e7dd", "#198754", "#0f5132"

    st.markdown(f"""
    <div style="background-color: {color_alerta}; border-left: 5px solid {borde_alerta}; padding: 12px 20px; border-radius: 4px; margin-bottom: 25px;">
        <strong style="color: {texto_alerta}; font-size: 13px;">🌐 ESTADO DEL CORREDOR ({nodo_seleccionado.upper()}): {info_actual['estado_semaforo']}</strong>
        <p style="color: {texto_alerta}; margin: 4px 0 0 0; font-size: 12.5px;">
            {info_actual['descripcion']} Semáforo multicriterio sincronizado en tiempo real.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if menu == "Impacto Comercial":
        st.markdown(f"#### 📰 Reportes Vigentes ({nodo_seleccionado})")
        cols_noticias = st.columns(len(info_actual["noticias"]))

        for idx, noti in enumerate(info_actual["noticias"]):
            with cols_noticias[idx]:
                st.markdown(f"""
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 6px; padding: 16px; height: 100%; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                    <div>
                        <span style="background-color: #002855; color: white; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 3px; text-transform: uppercase;">{noti['categoria']}</span>
                        <p style="font-size: 14px; font-weight: 700; color: #1e293b; margin: 10px 0 6px 0; line-height: 1.4;">{noti['titulo']}</p>
                        <p style="font-size: 11px; color: #64748b; margin-bottom: 12px;">🕒 Publicación: {noti['fecha']}</p>
                    </div>
                    <a href="{noti['link']}" target="_blank" style="background-color: #002855; color: white; text-align: center; padding: 8px 12px; border-radius: 4px; font-size: 11.5px; font-weight: 600; text-decoration: none; display: block; margin-top: 10px;">Leer fuente original ↗</a>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Modelo Analítico de Asimetría Logística y Comercio Exterior")
        st.caption("Evaluación cuantitativa basada en la matriz de costos e incidentes viales activos.")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Costo Oportunidad Acumulado", f"$ {nodos_activos_count * 22.5:.1f} M USD", "Basado en tramos con incidencia")
        with c2:
            st.metric("Desviación de fletes FOB", f"+{nodos_activos_count * 7.5}%", "Afectación en red troncal")
        with c3:
            st.metric("Corredores con Alerta / Restricción", f"{nodos_activos_count} / {len(DB_NODOS)}", "Semáforo activo")

        st.markdown("### Registro Dinámico de Tramos y Puntos de Conflicto Vigentes")
        
        lista_df = []
        for nodo, v in DB_NODOS.items():
            lista_df.append({
                "corredor_vial": nodo,
                "ubicacion_gps": f"Lat: {v['lat']}, Lon: {v['lon']}",
                "causa": v["causa"], 
                "estado_operativo": v["estado_semaforo"]
            })
        df_live = pd.DataFrame(lista_df)
        st.dataframe(df_live, use_container_width=True)

    elif menu == "Nodos Críticos":
        st.markdown("### Cartografía Geoespacial de Corredores Logísticos (Red Vial Fundamental)")
        st.caption("Visualización interactiva: Clasificación de rutas (Principales, Secundarias y Terciarias) con coloración dinámica según conflictos activos.")
        
        # Invocamos la función modular externa que genera el mapa de carreteras
        generar_mapa_carreteras(DB_NODOS)

elif menu == "Pasos Fronterizos":
    st.markdown("### Monitoreo de Soberanía y Pasos Fronterizos")
    st.caption("Estado operativo de las principales fronteras aduaneras sincronizado con fuentes en tiempo real.")

    PASOS_FRONTERIZOS_BASE = {
        "Tambo Quemado": {"pais": "Chile", "query": "tambo quemado frontera chile paso abierto cerrado"},
        "Pisiga": {"pais": "Chile", "query": "pisiga colchane frontera horario paso abierto"},
        "Desaguadero": {"pais": "Perú", "query": "desaguadero frontera peru paso bloqueado abierto"},
        "Yacuiba": {"pais": "Argentina", "query": "yacuiba frontera argentina aduana paso"},
        "Puerto Suárez": {"pais": "Brasil", "query": "puerto suarez frontera brasil puerto quijarro"}
    }

    @st.cache_data(ttl=300)
    def escanear_fronterizos():
        datos_frontera = []
        for paso, meta in PASOS_FRONTERIZOS_BASE.items():
            rss_url = f"https://news.google.com/rss/search?q={quote_plus(meta['query'])}&hl=es-419&gl=BO&ceid=BO:es-419"
            feed = feedparser.parse(rss_url)
            
            estado_operativo = "🟢 Operativo (Normal)"
            detalle_reciente = "Tránsito fluido reportado"
            
            if feed.entries:
                for entry in feed.entries[:3]:
                    titulo_lower = entry.title.lower()
                    if any(w in titulo_lower for w in ["bloqueo", "cortado", "protesta", "cierre total"]):
                        estado_operativo = "🔴 Alerta Activa (Bloqueo)"
                        detalle_reciente = entry.title
                        break
                    elif any(w in titulo_lower for w in ["restringido", "obras", "horario", "lento", "mantenimiento", "retraso"]):
                        estado_operativo = "🟡 Restricción / Obras"
                        detalle_reciente = entry.title
                        break

            datos_frontera.append({
                "Paso Fronterizo": paso,
                "País Limítrofe": meta["pais"],
                "Estado Operativo": estado_operativo,
                "Último Reporte / Condición": detalle_reciente
            })
        return pd.DataFrame(datos_frontera)

    df_fronteras_dinamico = escanear_fronterizos()
    st.dataframe(df_fronteras_dinamico, use_container_width=True)

elif menu == "Simulador Algorítmico":
    st.markdown("### Motor de Simulación Predictiva de Impacto Logístico")
    st.caption("Modelo econométrico basado en costos de estadía (Demurrage) e inmovilización de capital.")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        dias_bloqueo = st.slider("Días estimados de interrupción en la red troncal:", 1, 30, 10, key="slider_dias")
        flotas_afectadas = st.number_input("Parque automotor retenido (Unidades de transporte):", min_value=50, max_value=5000, value=max(1, nodos_activos_count) * 250, key="input_flotas")
    
    with col_s2:
        valor_promedio_carga = st.selectbox(
            "Valor FOB promedio por unidad de transporte:",
            options=[30000, 50000, 80000],
            format_func=lambda x: f"${x:,} USD (Carga general / Agroindustrial / Minera)",
            key="select_valor_carga"
        )
        costo_demurrage_diario = st.slider("Costo de estadía / Demurrage diario por unidad ($ USD):", 150, 300, 200, key="slider_demurrage")

    total_demurrage = dias_bloqueo * flotas_afectadas * costo_demurrage_diario
    tasa_diaria_capital = 0.08 / 365
    total_inmovilizacion = flotas_afectadas * valor_promedio_carga * tasa_diaria_capital * dias_bloqueo
    perdida_total = total_demurrage + total_inmovilizacion

    st.markdown("---")
    c_m1, c_m2, c_m3 = st.columns(3)
    with c_m1:
        st.metric(label="Lucro Cesante (Demurrage)", value=f"${total_demurrage:,.2f} USD")
    with c_m2:
        st.metric(label="Costo Financiero de Capital", value=f"${total_inmovilizacion:,.2f} USD")
    with c_m3:
        st.metric(label="Impacto Logístico Total Estimado", value=f"${perdida_total:,.2f} USD")

elif menu == "Acuerdos y Repositorio":
    st.markdown("### Repositorio Normativo y Documentos Legales")
    st.caption("Marco jurídico internacional y documentos oficiales del observatorio alojados localmente.")
    
    col_doc1, col_doc2 = st.columns(2)
    with col_doc1:
        st.markdown("#### 📄 Comunidad Andina")
        try:
            with open("documentos/comunidad andina.pdf", "rb") as file:
                st.download_button(label="📥 Descargar Comunidad Andina (PDF)", data=file, file_name="comunidad_andina.pdf", mime="application/pdf", key="btn_doc_ca")
        except FileNotFoundError:
            st.error("⚠️ Archivo no encontrado.")

        st.markdown("#### 📄 Acuerdo ACE N° 22")
        try:
            with open("documentos/ACE-N°-22.pdf", "rb") as file:
                st.download_button(label="📥 Descargar ACE N° 22 (PDF)", data=file, file_name="ACE_N_22.pdf", mime="application/pdf", key="btn_doc_ace22")
        except FileNotFoundError:
            st.error("⚠️ Archivo no encontrado.")

        st.markdown("#### 📄 Acuerdo ACE N° 47")
        try:
            with open("documentos/ACE-N°-47.pdf", "rb") as file:
                st.download_button(label="📥 Descargar ACE N° 47 (PDF)", data=file, file_name="ACE_N_47.pdf", mime="application/pdf", key="btn_doc_ace47")
        except FileNotFoundError:
            st.error("⚠️ Archivo no encontrado.")

    with col_doc2:
        st.markdown("#### 📄 Acuerdo ACE N° 66")
        try:
            with open("documentos/ACE-N°-66.pdf", "rb") as file:
                st.download_button(label="📥 Gran Acuerdo ACE N° 66 (PDF)", data=file, file_name="ACE_N_66.pdf", mime="application/pdf", key="btn_doc_ace66")
        except FileNotFoundError:
            st.error("⚠️ Archivo no encontrado.")

        st.markdown("#### 📄 Mercosur")
        try:
            with open("documentos/mercosur.pdf", "rb") as file:
                st.download_button(label="📥 Descargar Mercosur (PDF)", data=file, file_name="mercosur.pdf", mime="application/pdf", key="btn_doc_mercosur")
        except FileNotFoundError:
            st.error("⚠️ Archivo no encontrado.")

        st.markdown("#### 📄 Esquema Preferencial")
        try:
            with open("documentos/esquema preferencial unilateral union eu.pdf", "rb") as file:
                st.download_button(label="📥 Descargar Esquema Preferencial (PDF)", data=file, file_name="esquema_preferencial.pdf", mime="application/pdf", key="btn_doc_esquema")
        except FileNotFoundError:
            st.error("⚠️ Archivo no encontrado.")

st.markdown("</div>", unsafe_allow_html=True)
