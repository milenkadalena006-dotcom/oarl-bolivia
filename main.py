import os
import folium
import pandas as pd


def generar_datos_y_mapa():
  # 1. Matriz de datos estructurales (2023-2026)
  datos_estructurales = [
      {
          "ID_Nodo": "NOD-01",
          "Corredor": "Eje Central (Cochabamba - Santa Cruz)",
          "Tramo": "Parotani (Km 39)",
          "Frecuencia_Historica_Anual": 12,
          "Tipo_Riesgo_Recurrente": "Conflictos Sociales / Bloqueos",
          "Impacto_Comercial": "Crítico",
          "Dias_Interrupcion_Promedio": 4.5,
          "Latitud": -17.6534,
          "Longitud": -66.3812,
      },
      {
          "ID_Nodo": "NOD-02",
          "Corredor": "Eje Occidental (La Paz - Tambo Quemado)",
          "Tramo": "Patacamaya - Sica Sica",
          "Frecuencia_Historica_Anual": 8,
          "Tipo_Riesgo_Recurrente": "Paro Gremial / Aduanero",
          "Impacto_Comercial": "Alto",
          "Dias_Interrupcion_Promedio": 2.8,
          "Latitud": -17.2345,
          "Longitud": -67.8321,
      },
      {
          "ID_Nodo": "NOD-03",
          "Corredor": "Corredor Sur (Potosí - Villazón)",
          "Tramo": "El Portillo - Cruce Tojo",
          "Frecuencia_Historica_Anual": 5,
          "Tipo_Riesgo_Recurrente": "Vulnerabilidad Geológica / Desastre",
          "Impacto_Comercial": "Medio",
          "Dias_Interrupcion_Promedio": 3.0,
          "Latitud": -21.5355,
          "Longitud": -65.7531,
      },
      {
          "ID_Nodo": "NOD-04",
          "Corredor": "Eje Oriental (Santa Cruz - Puerto Suárez)",
          "Tramo": "Pailón - San José de Chiquitos",
          "Frecuencia_Historica_Anual": 6,
          "Tipo_Riesgo_Recurrente": "Restricción Logística / Exportación",
          "Impacto_Comercial": "Alto",
          "Dias_Interrupcion_Promedio": 2.0,
          "Latitud": -17.6652,
          "Longitud": -62.3781,
      },
  ]

  df = pd.DataFrame(datos_estructurales)
  os.makedirs("data", exist_ok=True)
  os.makedirs("outputs", exist_ok=True)
  df.to_csv("data/matriz_estructural_2023_2026.csv", index=False, encoding="utf-8")

  # 2. Generación del mapa analítico limpio
  lat_bolivia, lon_bolivia = -16.2902, -63.5887
  mapa = folium.Map(
      location=[lat_bolivia, lon_bolivia],
      zoom_start=6,
      tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
      attr="Esri, DeLorme, NAVTEQ, USGS",
  )

  for _, row in df.iterrows():
    color = (
        "red"
        if row["Impacto_Comercial"] == "Crítico"
        else "orange"
        if row["Impacto_Comercial"] == "Alto"
        else "blue"
    )
    popup_html = f"""
        <div style="font-family: Arial; width: 220px;">
            <h4 style="margin: 0; color: #b52a2a;">{row['Corredor']}</h4>
            <p style="margin: 4px 0;"><b>Tramo:</b> {row['Tramo']}</p>
            <p style="margin: 4px 0;"><b>Riesgo:</b> {row['Tipo_Riesgo_Recurrente']}</p>
            <p style="margin: 4px 0;"><b>Frecuencia:</b> {row['Frecuencia_Historica_Anual']} eventos/año</p>
            <p style="margin: 4px 0;"><b>Criticidad:</b> {row['Impacto_Comercial']}</p>
        </div>
        """
    folium.CircleMarker(
        location=[row["Latitud"], row["Longitud"]],
        radius=int(row["Frecuencia_Historica_Anual"] * 1.3),
        popup=folium.Popup(popup_html, max_width=250),
        tooltip=f"{row['Tramo']} ({row['Impacto_Comercial']})",
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.75,
    ).add_to(mapa)

  mapa.save("outputs/mapa_riesgo_estructural.html")
  print("[ÉXITO] Datos y cartografía estructural actualizados.")


if __name__ == "__main__":
  generar_datos_y_mapa()