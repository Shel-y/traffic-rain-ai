"""
Traffic Rain Risk Optimizer — Interfaz de navegación.

Mapa interactivo de CDMX con routing punto a punto que evade
zonas de encharcamiento usando ML + QAOA + Dijkstra.

Uso:
    streamlit run app.py
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import numpy as np
import pandas as pd
from pathlib import Path

# ─── Configuración de la página ──────────────────────────────────────────────

st.set_page_config(
    page_title="Traffic Rain Risk Optimizer",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Importar módulos del proyecto ───────────────────────────────────────────

from src import config
from src.data_loader import load_and_filter
from src.risk_scoring import identify_critical_points
from src.graph_builder import build_graph
from src.risk_penalizer import penalize_graph
from src.router import find_route_comparison


# ─── Puntos de interés (origen/destino) ─────────────────────────────────────

LOCATIONS = {
    "CU (Ciudad Universitaria)": {"lat": 19.3320, "lon": -99.1870},
    "Metro Coyoacán": {"lat": 19.3500, "lon": -99.1560},
    "Pedregal de San Ángel": {"lat": 19.3250, "lon": -99.1950},
    "Colinas del Ajusco": {"lat": 19.2840, "lon": -99.2200},
    "Jardines del Pedregal": {"lat": 19.3250, "lon": -99.2110},
    "La Joya": {"lat": 19.2850, "lon": -99.1640},
    "Barrio San Miguel (Iztapalapa)": {"lat": 19.3550, "lon": -99.0840},
    "Tlalpan Centro": {"lat": 19.2940, "lon": -99.1700},
    "Villa Coapa": {"lat": 19.3020, "lon": -99.1440},
    "San Jerónimo": {"lat": 19.3380, "lon": -99.2050},
    "El Reloj": {"lat": 19.2980, "lon": -99.1810},
    "Huipulco": {"lat": 19.2970, "lon": -99.1560},
}

# Colores
SAFE_ROUTE_COLOR = "#2ecc71"   # Verde
FAST_ROUTE_COLOR = "#95a5a6"   # Gris
FLOOD_MARKER_COLOR = "red"
CORRIDOR_COLORS = {
    "R1": "#e74c3c", "R2": "#3498db", "R3": "#2ecc71", "R4": "#f39c12",
}


# ─── Caché de datos pesados ──────────────────────────────────────────────────


@st.cache_resource(show_spinner="Cargando grafo de calles...")
def load_graph():
    """Carga o descarga el grafo de calles (se ejecuta una sola vez)."""
    return build_graph()


@st.cache_resource(show_spinner="Cargando datos de encharcamientos...")
def load_flood_data():
    """Carga y agrupa los datos de encharcamiento."""
    df = load_and_filter(
        csv_path=config.RAW_CSV_PATH,
        reporte_filter=config.REPORTE_FILTER,
        coordinate_decimals=config.COORDINATE_DECIMALS,
    )
    # Agrupar en puntos críticos con frecuencia
    puntos = (
        df.groupby(["lat_round", "lon_round"])
        .agg(frecuencia=("lat_round", "count"))
        .reset_index()
        .sort_values("frecuencia", ascending=False)
    )
    return puntos


@st.cache_resource(show_spinner="Penalizando grafo con datos de riesgo...")
def get_penalized_graph(_G, _flood_data):
    """Aplica penalización de riesgo al grafo."""
    return penalize_graph(_G, _flood_data)


# ─── Funciones de visualización ──────────────────────────────────────────────


def create_map(center_lat: float, center_lon: float, zoom: int = 13) -> folium.Map:
    """Crea el mapa base."""
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom,
        tiles="CartoDB positron",
        control_scale=True,
    )
    return m


def add_flood_markers(m: folium.Map, flood_data: pd.DataFrame, top_n: int = 20) -> folium.Map:
    """Agrega marcadores de zonas de encharcamiento (top N más frecuentes)."""
    top_points = flood_data.head(top_n)

    for _, row in top_points.iterrows():
        radius = max(4, min(15, row["frecuencia"] * 0.7))
        folium.CircleMarker(
            location=[row["lat_round"], row["lon_round"]],
            radius=radius,
            color=FLOOD_MARKER_COLOR,
            fill=True,
            fill_color=FLOOD_MARKER_COLOR,
            fill_opacity=0.4,
            opacity=0.6,
            tooltip=f"⚠️ Encharcamientos: {int(row['frecuencia'])}",
        ).add_to(m)

    return m


def add_route_to_map(
    m: folium.Map,
    route_coords: list,
    color: str,
    weight: int = 5,
    opacity: float = 0.8,
    tooltip: str = "",
    dash_array: str = None,
) -> folium.Map:
    """Dibuja una ruta en el mapa."""
    if len(route_coords) < 2:
        return m

    line_kwargs = {
        "locations": route_coords,
        "color": color,
        "weight": weight,
        "opacity": opacity,
        "tooltip": tooltip,
    }
    if dash_array:
        line_kwargs["dash_array"] = dash_array

    folium.PolyLine(**line_kwargs).add_to(m)
    return m


def add_markers(
    m: folium.Map,
    origin: dict,
    dest: dict,
    origin_name: str,
    dest_name: str,
) -> folium.Map:
    """Agrega marcadores de origen y destino."""
    # Origen (verde)
    folium.Marker(
        location=[origin["lat"], origin["lon"]],
        popup=f"<b>Origen:</b> {origin_name}",
        tooltip=f"📍 {origin_name}",
        icon=folium.Icon(color="green", icon="play", prefix="fa"),
    ).add_to(m)

    # Destino (azul)
    folium.Marker(
        location=[dest["lat"], dest["lon"]],
        popup=f"<b>Destino:</b> {dest_name}",
        tooltip=f"🏁 {dest_name}",
        icon=folium.Icon(color="blue", icon="flag-checkered", prefix="fa"),
    ).add_to(m)

    return m


# ─── UI Principal ────────────────────────────────────────────────────────────


def main():
    # ─── Sidebar ─────────────────────────────────────────────────────────────
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/rain--v1.png", width=60)
        st.title("🌧️ Traffic Rain")
        st.caption("Optimizador de Rutas en Lluvia")
        st.markdown("---")

        # Selectores de origen/destino
        st.subheader("📍 Navegación")

        origin_name = st.selectbox(
            "Origen",
            options=list(LOCATIONS.keys()),
            index=0,
        )

        dest_name = st.selectbox(
            "Destino",
            options=list(LOCATIONS.keys()),
            index=7,
        )

        st.markdown("---")

        # Opciones avanzadas
        st.subheader("⚙️ Opciones")

        show_flood_zones = st.checkbox("Mostrar zonas de encharcamiento", value=True)
        show_fast_route = st.checkbox("Comparar con ruta más corta", value=True)

        n_flood_markers = st.slider(
            "Puntos de riesgo visibles",
            min_value=5, max_value=50, value=20,
        )

        st.markdown("---")

        # Botón principal
        calculate = st.button(
            "🚀 Calcular Ruta Segura",
            type="primary",
            use_container_width=True,
        )

        st.markdown("---")
        st.caption("🧠 ML + ⚛️ QAOA + 🗺️ Dijkstra")
        st.caption("Datos: SACMEX (Datos Abiertos CDMX)")

    # ─── Área principal ──────────────────────────────────────────────────────

    # Header
    st.markdown(
        "<h1 style='margin-bottom:0'>🌧️ Traffic Rain Risk Optimizer</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:gray;margin-top:0'>"
        "Navegación inteligente que evade encharcamientos usando IA y Computación Cuántica"
        "</p>",
        unsafe_allow_html=True,
    )

    # Cargar datos (cacheados)
    G = load_graph()
    flood_data = load_flood_data()
    G = get_penalized_graph(G, flood_data)

    # Estado de la sesión
    if "route_result" not in st.session_state:
        st.session_state.route_result = None

    # Calcular ruta
    if calculate:
        if origin_name == dest_name:
            st.error("⚠️ El origen y el destino deben ser diferentes.")
        else:
            origin = LOCATIONS[origin_name]
            dest = LOCATIONS[dest_name]

            with st.spinner("Calculando ruta óptima..."):
                result = find_route_comparison(
                    G,
                    origin["lat"], origin["lon"],
                    dest["lat"], dest["lon"],
                    preferred_corridor="R3",  # Corredor asignado por QAOA para la zona sur
                )
                st.session_state.route_result = result
                st.session_state.origin_name = origin_name
                st.session_state.dest_name = dest_name

    # Layout: métricas arriba, mapa abajo
    if st.session_state.route_result:
        result = st.session_state.route_result
        safe = result["safe_route"]
        fast = result["fast_route"]

        # Tarjetas de métricas
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            dist_km = safe["distance_m"] / 1000
            st.metric(
                "🛣️ Distancia",
                f"{dist_km:.1f} km",
                delta=f"{(safe['distance_m'] - fast['distance_m'])/1000:+.1f} km vs rápida"
                if show_fast_route else None,
            )

        with col2:
            time_min = safe["travel_time_s"] / 60
            st.metric(
                "⏱️ Tiempo estimado",
                f"{time_min:.0f} min",
                delta=f"{(safe['travel_time_s'] - fast['travel_time_s'])/60:+.0f} min"
                if show_fast_route else None,
            )

        with col3:
            risk_pct = safe["risk_score"] * 100
            risk_label = "Bajo" if risk_pct < 10 else "Medio" if risk_pct < 30 else "Alto"
            st.metric(
                "⚠️ Riesgo evitado",
                risk_label,
                delta=f"{risk_pct:.0f}% del trayecto penalizado",
            )

        with col4:
            corridor = safe["preferred_corridor"] or "—"
            corridor_name = config.RUTAS_NOMBRES.get(corridor, "—")
            st.metric("🛤️ Corredor QAOA", corridor_name)

    # Mapa
    origin = LOCATIONS[origin_name]
    dest = LOCATIONS[dest_name]
    center_lat = (origin["lat"] + dest["lat"]) / 2
    center_lon = (origin["lon"] + dest["lon"]) / 2

    m = create_map(center_lat, center_lon, zoom=13)

    # Zonas de encharcamiento
    if show_flood_zones:
        m = add_flood_markers(m, flood_data, top_n=n_flood_markers)

    # Rutas calculadas
    if st.session_state.route_result:
        result = st.session_state.route_result
        safe = result["safe_route"]
        fast = result["fast_route"]

        # Ruta rápida (gris, detrás)
        if show_fast_route and fast["route_coords"]:
            m = add_route_to_map(
                m, fast["route_coords"],
                color=FAST_ROUTE_COLOR, weight=4, opacity=0.5,
                tooltip="Ruta más corta (sin considerar riesgo)",
                dash_array="8",
            )

        # Ruta segura (verde, encima)
        if safe["route_coords"]:
            m = add_route_to_map(
                m, safe["route_coords"],
                color=SAFE_ROUTE_COLOR, weight=6, opacity=0.9,
                tooltip="✓ Ruta segura (evita encharcamientos)",
            )

    # Marcadores de origen/destino
    m = add_markers(m, origin, dest, origin_name, dest_name)

    # Renderizar mapa
    st_folium(m, width=None, height=550, use_container_width=True)

    # Info adicional debajo del mapa
    if st.session_state.route_result:
        with st.expander("ℹ️ Detalles técnicos"):
            result = st.session_state.route_result
            safe = result["safe_route"]

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Algoritmo de routing:**")
                st.markdown("- Dijkstra sobre grafo penalizado")
                st.markdown(f"- Segmentos de ruta: {safe['n_segments']:,}")
                st.markdown(f"- Corredor preferido: {safe['preferred_corridor']}")

            with col_b:
                st.markdown("**Stack tecnológico:**")
                st.markdown("- 🧠 Random Forest (penalización ML)")
                st.markdown("- ⚛️ QAOA p=1 (asignación de corredor)")
                st.markdown("- 🗺️ Dijkstra (routing calle por calle)")
                st.markdown("- 📊 Datos: SACMEX Abiertos")


if __name__ == "__main__":
    main()
