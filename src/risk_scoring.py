"""
Módulo 2: Generación de la matriz de scores (compatibilidad/riesgo).

Responsabilidades separadas internamente:
    1. identify_critical_points: análisis geográfico (agrupamiento, top-N)
    2. compute_scores: cálculo de distancias y normalización a scores

Origen: Notebook 01 (celdas 5-final)
"""

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


# ─── Funciones auxiliares ────────────────────────────────────────────────────


def _haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Distancia en metros entre dos puntos geográficos (fórmula de Haversine)."""
    R = 6_371_000  # radio de la Tierra en metros
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return float(2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a)))


def _distance_point_to_route(
    point: Tuple[float, float],
    route: List[Tuple[float, float]],
) -> float:
    """
    Distancia mínima en metros de un punto a una polilínea (ruta).

    Parámetros
    ----------
    point : (lon, lat)
    route : lista de (lon, lat) que definen la polilínea
    """
    min_dist = float("inf")
    p = np.array(point)
    for i in range(len(route) - 1):
        a = np.array(route[i])
        b = np.array(route[i + 1])
        ab = b - a
        ap = p - a
        dot_ab = np.dot(ab, ab)
        if dot_ab == 0:
            t = 0.0
        else:
            t = float(np.clip(np.dot(ap, ab) / dot_ab, 0.0, 1.0))
        closest = a + t * ab
        dist = _haversine(p[0], p[1], closest[0], closest[1])
        min_dist = min(min_dist, dist)
    return min_dist


# ─── Función 1: Análisis geográfico ─────────────────────────────────────────


def identify_critical_points(
    df_encharcamientos: pd.DataFrame,
    n_top: int,
) -> pd.DataFrame:
    """
    Agrupa encharcamientos por coordenadas redondeadas y selecciona
    los N puntos más frecuentes.

    Parámetros
    ----------
    df_encharcamientos : pd.DataFrame
        Salida de data_loader (debe contener lat_round, lon_round, colonia_catalogo).
    n_top : int
        Número de puntos críticos a seleccionar (= número de usuarios).

    Retorna
    -------
    pd.DataFrame
        Top N puntos con columnas: lat_round, lon_round, frecuencia, colonia_catalogo.
    """
    # Contar frecuencia por punto
    puntos = (
        df_encharcamientos.groupby(["lat_round", "lon_round"])
        .agg(frecuencia=("lat_round", "count"))
        .reset_index()
        .sort_values("frecuencia", ascending=False)
    )

    # Obtener la colonia más reportada en cada punto
    colonia_por_punto = (
        df_encharcamientos.groupby(["lat_round", "lon_round"])["colonia_catalogo"]
        .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else "Desconocida")
        .reset_index()
    )

    # Seleccionar top N y unir con nombres de colonia
    top_n = puntos.head(n_top).merge(
        colonia_por_punto, on=["lat_round", "lon_round"], how="left"
    )

    return top_n.reset_index(drop=True)


# ─── Función 2: Cálculo de scores ───────────────────────────────────────────


def compute_scores(
    critical_points: pd.DataFrame,
    rutas_waypoints: Dict[str, List[Tuple[float, float]]],
    rutas_nombres: Dict[str, str],
) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Calcula la matriz de scores (compatibilidad) basada en distancia
    de cada punto crítico a cada ruta.

    score = 1 - (dist - dist_min) / (dist_max - dist_min)

    Parámetros
    ----------
    critical_points : pd.DataFrame
        Salida de identify_critical_points.
    rutas_waypoints : dict
        Waypoints por ruta {id_ruta: [(lon, lat), ...]}.
    rutas_nombres : dict
        Nombres legibles por ruta {id_ruta: nombre}.

    Retorna
    -------
    score_df : pd.DataFrame
        CSV en formato largo (a_id, b_id, score, a_nombre, b_nombre).
    score_matrix : np.ndarray
        Matriz de scores shape (n_usuarios, n_rutas).
    """
    n_users = len(critical_points)
    rutas_ids = list(rutas_waypoints.keys())
    n_routes = len(rutas_ids)

    # Calcular matriz de distancias
    dist_matrix = np.zeros((n_users, n_routes))
    for i, (_, row) in enumerate(critical_points.iterrows()):
        punto = (row["lon_round"], row["lat_round"])
        for j, ruta_id in enumerate(rutas_ids):
            dist_matrix[i, j] = _distance_point_to_route(
                punto, rutas_waypoints[ruta_id]
            )

    # Normalizar: score = 1 - (dist - min) / (max - min)
    dist_min = dist_matrix.min()
    dist_max = dist_matrix.max()
    rango = dist_max - dist_min
    if rango == 0:
        rango = 1.0
    score_matrix = np.round(1.0 - (dist_matrix - dist_min) / rango, 2)

    # Construir DataFrame en formato largo
    usuarios_ids = [f"U{i+1}" for i in range(n_users)]
    usuarios_nombres = critical_points["colonia_catalogo"].values

    filas = []
    for i, u_id in enumerate(usuarios_ids):
        for j, r_id in enumerate(rutas_ids):
            filas.append(
                [u_id, r_id, score_matrix[i, j], usuarios_nombres[i], rutas_nombres[r_id]]
            )

    score_df = pd.DataFrame(
        filas, columns=["a_id", "b_id", "score", "a_nombre", "b_nombre"]
    )

    return score_df, score_matrix


# ─── Función pública (interfaz del módulo) ───────────────────────────────────


def generate_score_matrix(
    df_encharcamientos: pd.DataFrame,
    rutas_waypoints: Dict[str, List[Tuple[float, float]]],
    rutas_nombres: Dict[str, str],
    n_top: int,
) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Pipeline completo de scoring: identifica puntos críticos y calcula scores.

    Parámetros
    ----------
    df_encharcamientos : pd.DataFrame
        Salida de data_loader.
    rutas_waypoints : dict
        Waypoints por ruta.
    rutas_nombres : dict
        Nombres legibles por ruta.
    n_top : int
        Número de puntos críticos (usuarios).

    Retorna
    -------
    score_df : pd.DataFrame
        Formato largo compatible con el notebook QUBO.
    score_matrix : np.ndarray
        Matriz numérica shape (n_top, n_rutas).
    """
    critical_points = identify_critical_points(df_encharcamientos, n_top)
    score_df, score_matrix = compute_scores(
        critical_points, rutas_waypoints, rutas_nombres
    )
    return score_df, score_matrix
