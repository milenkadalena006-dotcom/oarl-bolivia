import folium
import streamlit.components.v1 as components

def generar_mapa_carreteras(db_nodos):
    # Usamos CartoDB Positron / Voyager para tener un fondo limpio pero con todas las etiquetas de carreteras, ciudades y países visibles
    m = folium.Map(
        location=[-16.2902, -63.5887], 
        zoom_start=6, 
        tiles="CartoDB Positron",
        attr="CartoDB"
    )
    
    # Forzar límites estrictos sobre el territorio boliviano
    bolivia_bounds = [[-22.9, -69.6], [-9.7, -57.4]]
    m.fit_bounds(bolivia_bounds)

    # Función del semáforo logístico (color según el riesgo)
    def obtener_color_riesgo(nivel):
        if nivel == 2:
            return "#dc3545" # 🔴 Rojo: Bloqueo / Peligro Alto
        elif nivel == 1:
            return "#ffc107" # 🟡 Amarillo: Restricción / Obras
        else:
            return "#198754" # 🟢 Verde: Estable / Operativo

    # --- SUPERPONER ÚNICAMENTE LOS PUNTOS DE CONTROL Y CONFLICTO ---
    for nodo_k, info_val in db_nodos.items():
        color_marker = obtener_color_riesgo(info_val["nivel_riesgo"])
        
        popup_html = f"""
        <div style="font-family: sans-serif; width: 220px;">
            <b style="color: #002855; font-size: 13px;">{info_val['punto']}</b><br>
            <hr style="margin: 4px 0;">
            <b>Estado:</b> {info_val['estado_semaforo']}<br>
            <p style="font-size: 11px; color: #475569; margin: 4px 0 0 0;">{info_val['descripcion']}</p>
        </div>
        """
            
        folium.CircleMarker(
            location=[info_val["lat"], info_val["lon"]],
            radius=9,
            color="#ffffff",
            weight=2,
            fill=True,
            fill_color=color_marker,
            fill_opacity=1.0,
            popup=folium.Popup(popup_html, max_width=280)
        ).add_to(m)
        
    # Renderizar el mapa limpio en Streamlit
    mapa_html = m._repr_html_()
    components.html(mapa_html, height=580, scrolling=True)
