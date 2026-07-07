"""
Módulo: risk_penalizer

Responsabilidad:
    Modificar los pesos de las aristas del grafo de calles basándose
    en la proximidad a puntos de encharcamiento reportados.

    Las aristas cercanas a zonas con alta frecuencia de encharcamiento
    reciben un peso mayor (penalización), haciendo que Dijkstra las evite.

Lógica:
    nuevo_peso = peso_base * (1 + penalty_factor)
    penalty_factor = frecuencia_normalizada * decay(distancia)

Origen: Nuevo módulo (Fase 3.2)
"""

from typing import Optional

import numpy as np
import pandas as pd
import networkx as nx


# ─── Configuración por defecto ───────────────────────────────────────────────

DEFAULT_INFLUENCE_RADIUS_M = 500.0   # Radio de influencia de un encharcamiento (metros)
DEFAULT_MAX_PENALTY = 3.0            # Multiplicador máximo del peso (3x = evitar fuertemente)
DEFAULT_WEIGHT_ATTRIBUTE = "risk_weight"  # Nombre del atributo de peso penalizado


# ─── Funciones públicas ──────────────────────────────────────────────────────


def penalize_graph(
    G: nx.MultiDiGraph,
    df_encharcamientos: pd.DataFrame,
    influence_radius_m: float = DEFAULT_INFLUENCE_RADIUS_M,
    max_penalty: float = DEFAULT_MAX_PENALTY,
    weight_attribute: str = DEFAULT_WEIGHT_ATTRIBUTE,
) -> nx.MultiDiGraph:
    """
    Aplica penalizaciones de riesgo a las aristas del grafo.

    Para cada arista, calcula la penalización basada en la cercanía
    y frecuencia de encharcamientos reportados.

    Parámetros
    ----------
    G : nx.MultiDiGraph
        Grafo de calles (debe tener 'length' en aristas, 'x'/'y' en nodos).
    df_encharcamientos : pd.DataFrame
        DataFrame con columnas: lat_round, lon_round, frecuencia.
        (Salida de identify_critical_points o agrupamiento similar)
    influence_radius_m : float
        Radio máximo de influencia de un punto de encharcamiento (metros).
    max_penalty : float
        Factor multiplicativo máximo (ej. 3.0 = triplica el peso).
    weight_attribute : str
        Nombre del atributo donde se guarda el peso penalizado.

    Retorna
    -------
    nx.MultiDiGraph
        El mismo grafo (modificado in-place) con atributo weight_attribute
        en cada arista.
    """
    print(f"  🔄 Penalizando grafo con {len(df_encharcamientos)} puntos de riesgo...")
    print(f"     Radio de influencia: {influence_radius_m} m")
    print(f"     Penalización máxima: {max_penalty}x")

    # Preparar puntos de encharcamiento como arrays
    flood_points = df_encharcamientos[["lat_round", "lon_round"]].values
    flood_freqs = df_encharcamientos["frecuencia"].values

    # Normalizar frecuencias (0 a 1)
    freq_max = flood_freqs.max() if flood_freqs.max() > 0 else 1
    flood_freqs_norm = flood_freqs / freq_max

    # Pre-calcular coordenadas de nodos para búsqueda rápida
    node_coords = {}
    for node_id, data in G.nodes(data=True):
        node_coords[node_id] = (data["y"], data["x"])  # (lat, lon)

    # Aplicar penalización a cada arista
    edges_penalized = 0
    total_edges = G.number_of_edges()

    for u, v, key, data in G.edges(keys=True, data=True):
        base_length = data.get("length", 1.0)

        # Calcular el punto medio de la arista
        lat_u, lon_u = node_coords[u]
        lat_v, lon_v = node_coords[v]
        mid_lat = (lat_u + lat_v) / 2.0
        mid_lon = (lon_u + lon_v) / 2.0

        # Calcular penalización acumulada
        penalty = _compute_penalty(
            mid_lat, mid_lon,
            flood_points, flood_freqs_norm,
            influence_radius_m, max_penalty,
        )

        # Aplicar penalización al peso
        risk_weight = base_length * (1.0 + penalty)
        G[u][v][key][weight_attribute] = risk_weight

        if penalty > 0.01:
            edges_penalized += 1

    pct = (edges_penalized / total_edges * 100) if total_edges > 0 else 0
    print(f"  ✓ Penalización aplicada:")
    print(f"     Aristas afectadas: {edges_penalized:,} / {total_edges:,} ({pct:.1f}%)")

    return G


def get_penalty_at_point(
    lat: float,
    lon: float,
    df_encharcamientos: pd.DataFrame,
    influence_radius_m: float = DEFAULT_INFLUENCE_RADIUS_M,
    max_penalty: float = DEFAULT_MAX_PENALTY,
) -> float:
    """
    Calcula la penalización de riesgo en un punto específico.
    Útil para visualización.

    Retorna
    -------
    float
        Factor de penalización [0, max_penalty].
    """
    flood_points = df_encharcamientos[["lat_round", "lon_round"]].values
    flood_freqs = df_encharcamientos["frecuencia"].values
    freq_max = flood_freqs.max() if flood_freqs.max() > 0 else 1
    flood_freqs_norm = flood_freqs / freq_max

    return _compute_penalty(
        lat, lon, flood_points, flood_freqs_norm,
        influence_radius_m, max_penalty,
    )


# ─── Funciones auxiliares ────────────────────────────────────────────────────


def _haversine_fast(lat1: float, lon1: float, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """
    Haversine vectorizado: distancia de un punto a múltiples puntos.
    Retorna distancias en metros.
    """
    R = 6_371_000
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def _compute_penalty(
    lat: float,
    lon: float,
    flood_points: np.ndarray,
    flood_freqs_norm: np.ndarray,
    influence_radius_m: float,
    max_penalty: float,
) -> float:
    """
    Calcula la penalización total en un punto dado todos los encharcamientos.

    Usa una función de decay lineal: penalty decae linealmente con la distancia
    y es proporcional a la frecuencia normalizada.
    """
    # Distancias a todos los puntos de encharcamiento
    distances = _haversine_fast(
        lat, lon,
        flood_points[:, 0],  # lat
        flood_points[:, 1],  # lon
    )

    # Solo considerar puntos dentro del radio de influencia
    within_radius = distances < influence_radius_m

    if not np.any(within_radius):
        return 0.0

    # Decay lineal: 1 en el centro, 0 en el borde del radio
    decay = 1.0 - (distances[within_radius] / influence_radius_m)

    # Penalización = suma de (frecuencia_norm * decay) para cada punto cercano
    penalties = flood_freqs_norm[within_radius] * decay

    # Saturar al máximo
    total_penalty = min(float(np.sum(penalties)), max_penalty)

    return total_penalty
