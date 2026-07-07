"""
Módulo: router

Responsabilidad:
    Encontrar la ruta óptima entre origen y destino en el grafo
    de calles penalizado, favoreciendo el corredor asignado por QAOA.

Algoritmo: Dijkstra con peso = risk_weight (penalizado por ML)
           + bonificación para aristas dentro del corredor QAOA.

Origen: Nuevo módulo (Fase 3.3)
"""

from typing import Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
import osmnx as ox


# ─── Configuración ──────────────────────────────────────────────────────────

DEFAULT_WEIGHT = "risk_weight"
CORRIDOR_BONUS = 0.7  # Aristas en corredor QAOA pesan 70% (30% descuento)
FALLBACK_WEIGHT = "length"  # Si risk_weight no existe, usar length


# ─── Definición de corredores (bounding boxes aproximados) ───────────────────

# Cada corredor se define como un rectángulo (lat_min, lat_max, lon_min, lon_max)
# que aproxima la zona de influencia de la avenida.

CORRIDOR_ZONES = {
    "R1": {  # Viaducto + Av. Revolución
        "lat_min": 19.390, "lat_max": 19.415,
        "lon_min": -99.185, "lon_max": -99.165,
    },
    "R2": {  # Circuito Interior
        "lat_min": 19.415, "lat_max": 19.455,
        "lon_min": -99.155, "lon_max": -99.130,
    },
    "R3": {  # Periférico Sur + Eje 10
        "lat_min": 19.335, "lat_max": 19.365,
        "lon_min": -99.205, "lon_max": -99.175,
    },
    "R4": {  # Eje Central + Reforma
        "lat_min": 19.410, "lat_max": 19.435,
        "lon_min": -99.145, "lon_max": -99.125,
    },
}


# ─── Funciones públicas ──────────────────────────────────────────────────────


def find_route(
    G: nx.MultiDiGraph,
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    preferred_corridor: Optional[str] = None,
    weight: str = DEFAULT_WEIGHT,
) -> Dict:
    """
    Encuentra la ruta óptima entre origen y destino.

    Parámetros
    ----------
    G : nx.MultiDiGraph
        Grafo de calles (debe tener atributo weight en aristas).
    origin_lat, origin_lon : float
        Coordenadas del punto de origen.
    dest_lat, dest_lon : float
        Coordenadas del punto de destino.
    preferred_corridor : str o None
        ID del corredor preferido por QAOA (ej. "R3").
        Si se proporciona, las aristas dentro del corredor reciben
        un descuento en el peso.
    weight : str
        Atributo de peso a usar para Dijkstra.

    Retorna
    -------
    dict con claves:
        - route_nodes: list[int], nodos del camino
        - route_coords: list[(lat, lon)], coordenadas para visualizar
        - distance_m: float, distancia total en metros
        - travel_time_s: float, tiempo estimado en segundos
        - risk_score: float, riesgo acumulado normalizado [0,1]
        - n_segments: int, número de segmentos de la ruta
        - preferred_corridor: str o None, corredor usado
    """
    # Encontrar nodos más cercanos a origen y destino
    origin_node = ox.nearest_nodes(G, X=origin_lon, Y=origin_lat)
    dest_node = ox.nearest_nodes(G, X=dest_lon, Y=dest_lat)

    if origin_node == dest_node:
        return _empty_result(origin_lat, origin_lon, preferred_corridor)

    # Aplicar bonificación de corredor si se especifica
    effective_weight = weight
    if preferred_corridor and preferred_corridor in CORRIDOR_ZONES:
        _apply_corridor_bonus(G, preferred_corridor, weight)
        effective_weight = "corridor_weight"

    # Verificar que el atributo de peso existe
    actual_weight = _resolve_weight(G, effective_weight)

    # Dijkstra
    try:
        route_nodes = nx.shortest_path(
            G, origin_node, dest_node, weight=actual_weight
        )
    except nx.NetworkXNoPath:
        # Si no hay camino, intentar sin penalización
        try:
            route_nodes = nx.shortest_path(
                G, origin_node, dest_node, weight=FALLBACK_WEIGHT
            )
        except nx.NetworkXNoPath:
            return _empty_result(origin_lat, origin_lon, preferred_corridor)

    # Extraer coordenadas de la ruta
    route_coords = []
    for node_id in route_nodes:
        node_data = G.nodes[node_id]
        route_coords.append((node_data["y"], node_data["x"]))

    # Calcular métricas
    distance_m = _compute_route_distance(G, route_nodes)
    travel_time_s = _compute_route_travel_time(G, route_nodes)
    risk_score = _compute_route_risk(G, route_nodes, weight)

    # Limpiar atributos temporales
    if preferred_corridor:
        _remove_corridor_bonus(G)

    return {
        "route_nodes": route_nodes,
        "route_coords": route_coords,
        "distance_m": distance_m,
        "travel_time_s": travel_time_s,
        "risk_score": risk_score,
        "n_segments": len(route_nodes) - 1,
        "preferred_corridor": preferred_corridor,
    }


def find_route_comparison(
    G: nx.MultiDiGraph,
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    preferred_corridor: Optional[str] = None,
) -> Dict:
    """
    Encuentra dos rutas: la ruta sin penalización (más corta) y la ruta
    con penalización de riesgo. Útil para comparar en la UI.

    Retorna
    -------
    dict con claves:
        - safe_route: resultado de find_route con risk_weight
        - fast_route: resultado de find_route con length (sin penalización)
    """
    # Ruta segura (con penalización de riesgo + corredor QAOA)
    safe_route = find_route(
        G, origin_lat, origin_lon, dest_lat, dest_lon,
        preferred_corridor=preferred_corridor,
        weight=DEFAULT_WEIGHT,
    )

    # Ruta rápida (sin penalización, solo distancia)
    fast_route = find_route(
        G, origin_lat, origin_lon, dest_lat, dest_lon,
        preferred_corridor=None,
        weight=FALLBACK_WEIGHT,
    )

    return {
        "safe_route": safe_route,
        "fast_route": fast_route,
    }


# ─── Funciones auxiliares ────────────────────────────────────────────────────


def _apply_corridor_bonus(
    G: nx.MultiDiGraph, corridor_id: str, base_weight: str
) -> None:
    """Aplica descuento a aristas dentro del corredor preferido."""
    zone = CORRIDOR_ZONES[corridor_id]

    for u, v, key, data in G.edges(keys=True, data=True):
        base = data.get(base_weight, data.get("length", 1.0))

        # Verificar si el punto medio de la arista está en el corredor
        lat_u = G.nodes[u]["y"]
        lon_u = G.nodes[u]["x"]
        lat_v = G.nodes[v]["y"]
        lon_v = G.nodes[v]["x"]
        mid_lat = (lat_u + lat_v) / 2.0
        mid_lon = (lon_u + lon_v) / 2.0

        if _point_in_zone(mid_lat, mid_lon, zone):
            G[u][v][key]["corridor_weight"] = base * CORRIDOR_BONUS
        else:
            G[u][v][key]["corridor_weight"] = base


def _remove_corridor_bonus(G: nx.MultiDiGraph) -> None:
    """Elimina el atributo temporal corridor_weight."""
    for u, v, key in G.edges(keys=True):
        G[u][v][key].pop("corridor_weight", None)


def _point_in_zone(lat: float, lon: float, zone: dict) -> bool:
    """Verifica si un punto está dentro de una zona rectangular."""
    return (
        zone["lat_min"] <= lat <= zone["lat_max"]
        and zone["lon_min"] <= lon <= zone["lon_max"]
    )


def _resolve_weight(G: nx.MultiDiGraph, weight: str) -> str:
    """Verifica que el atributo de peso exista en al menos una arista."""
    for _, _, data in G.edges(data=True):
        if weight in data:
            return weight
        break
    return FALLBACK_WEIGHT


def _compute_route_distance(G: nx.MultiDiGraph, route_nodes: list) -> float:
    """Suma la distancia (length) de la ruta."""
    total = 0.0
    for i in range(len(route_nodes) - 1):
        u, v = route_nodes[i], route_nodes[i + 1]
        edge_data = G.get_edge_data(u, v)
        if edge_data:
            first_edge = list(edge_data.values())[0]
            total += first_edge.get("length", 0.0)
    return total


def _compute_route_travel_time(G: nx.MultiDiGraph, route_nodes: list) -> float:
    """Suma el tiempo estimado de recorrido (travel_time)."""
    total = 0.0
    for i in range(len(route_nodes) - 1):
        u, v = route_nodes[i], route_nodes[i + 1]
        edge_data = G.get_edge_data(u, v)
        if edge_data:
            first_edge = list(edge_data.values())[0]
            total += first_edge.get("travel_time", 0.0)
    return total


def _compute_route_risk(
    G: nx.MultiDiGraph, route_nodes: list, weight: str
) -> float:
    """
    Calcula un score de riesgo normalizado [0,1] para la ruta.
    Compara el peso penalizado vs el peso base (length).
    risk = 1 - (length / risk_weight). Si son iguales, risk = 0.
    """
    total_length = 0.0
    total_risk_weight = 0.0

    for i in range(len(route_nodes) - 1):
        u, v = route_nodes[i], route_nodes[i + 1]
        edge_data = G.get_edge_data(u, v)
        if edge_data:
            first_edge = list(edge_data.values())[0]
            length = first_edge.get("length", 1.0)
            risk_w = first_edge.get(weight, length)
            total_length += length
            total_risk_weight += risk_w

    if total_risk_weight == 0:
        return 0.0

    # Ratio: cuánto se desvía del camino base por la penalización
    ratio = total_length / total_risk_weight
    risk = 1.0 - ratio  # 0 = sin riesgo, cercano a 1 = mucho riesgo evitado
    return max(0.0, min(1.0, risk))


def _empty_result(lat: float, lon: float, corridor: Optional[str]) -> Dict:
    """Retorna un resultado vacío cuando no hay ruta posible."""
    return {
        "route_nodes": [],
        "route_coords": [(lat, lon)],
        "distance_m": 0.0,
        "travel_time_s": 0.0,
        "risk_score": 0.0,
        "n_segments": 0,
        "preferred_corridor": corridor,
    }
