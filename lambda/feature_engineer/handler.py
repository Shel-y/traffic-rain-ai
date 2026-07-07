"""
Lambda: feature_engineer

Lee los encharcamientos filtrados desde S3, calcula las features
para cada par (punto_critico × ruta) y escribe el CSV de inferencia
en S3 listo para que SageMaker Batch Transform lo procese.

También genera un CSV de metadata (mapping punto→usuario) para
reconstruir el dataset final con a_id, b_id, a_nombre, b_nombre.

Evento esperado:
{
    "bucket": "traffic-rain-ai-XXXX",
    "processed_key": "processed/encharcamientos_filtered.csv",
    "inference_output_key": "inference/input.csv",
    "metadata_output_key": "inference/metadata.csv",
    "n_top": 4,
    "rutas_waypoints": {...},
    "rutas_nombres": {...}
}

Nota: Si rutas_waypoints/rutas_nombres no se pasan en el evento,
se usan los valores por defecto del proyecto.
"""

import io
import json

import boto3
import numpy as np
import pandas as pd


s3 = boto3.client("s3")

# ─── Valores por defecto (mismos que config.py) ─────────────────────────────

DEFAULT_RUTAS_WAYPOINTS = {
    "R1": [(-99.180, 19.400), (-99.178, 19.398), (-99.175, 19.395),
            (-99.172, 19.402), (-99.170, 19.410)],
    "R2": [(-99.150, 19.450), (-99.145, 19.440), (-99.140, 19.430),
            (-99.137, 19.425), (-99.135, 19.420)],
    "R3": [(-99.200, 19.360), (-99.195, 19.355), (-99.190, 19.350),
            (-99.185, 19.345), (-99.180, 19.340)],
    "R4": [(-99.140, 19.430), (-99.137, 19.428), (-99.135, 19.425),
            (-99.132, 19.420), (-99.130, 19.415)],
}

DEFAULT_RUTAS_NOMBRES = {
    "R1": "Viaducto+Revolución",
    "R2": "Circuito Interior",
    "R3": "Periférico Sur",
    "R4": "Eje Central",
}

FEATURE_COLS = [
    "frecuencia", "lat_punto", "lon_punto", "mes_pico",
    "lat_ruta_centroid", "lon_ruta_centroid", "ruta_length",
    "n_puntos_near_ruta", "dist_to_route",
]


# ─── Funciones auxiliares ────────────────────────────────────────────────────


def _haversine(lon1, lat1, lon2, lat2):
    """Distancia Haversine en metros."""
    R = 6_371_000
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return float(2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a)))


def _distance_point_to_route(point, route):
    """Distancia mínima de un punto a una polilínea."""
    min_dist = float("inf")
    p = np.array(point)
    for i in range(len(route) - 1):
        a = np.array(route[i])
        b = np.array(route[i + 1])
        ab = b - a
        dot_ab = np.dot(ab, ab)
        if dot_ab == 0:
            t = 0.0
        else:
            ap = p - a
            t = float(np.clip(np.dot(ap, ab) / dot_ab, 0.0, 1.0))
        closest = a + t * ab
        dist = _haversine(p[0], p[1], closest[0], closest[1])
        min_dist = min(min_dist, dist)
    return min_dist


def _route_centroid(waypoints):
    lons = [p[0] for p in waypoints]
    lats = [p[1] for p in waypoints]
    return (np.mean(lons), np.mean(lats))


def _route_length(waypoints):
    total = 0.0
    for i in range(len(waypoints) - 1):
        total += _haversine(waypoints[i][0], waypoints[i][1],
                            waypoints[i + 1][0], waypoints[i + 1][1])
    return total


def _count_points_near_route(puntos_df, waypoints, radius_m=5000.0):
    count = 0
    for _, row in puntos_df.iterrows():
        punto = (row["lon_round"], row["lat_round"])
        dist = _distance_point_to_route(punto, waypoints)
        if dist <= radius_m:
            count += int(row["frecuencia"])
    return count


# ─── Handler ─────────────────────────────────────────────────────────────────


def lambda_handler(event, context):
    """Punto de entrada de Lambda."""
    bucket = event["bucket"]
    processed_key = event["processed_key"]
    inference_output_key = event["inference_output_key"]
    metadata_output_key = event["metadata_output_key"]
    n_top = event.get("n_top", 4)
    rutas_waypoints = event.get("rutas_waypoints", DEFAULT_RUTAS_WAYPOINTS)
    rutas_nombres = event.get("rutas_nombres", DEFAULT_RUTAS_NOMBRES)

    # Convertir waypoints de listas a tuples si vienen de JSON
    for ruta_id in rutas_waypoints:
        rutas_waypoints[ruta_id] = [tuple(p) for p in rutas_waypoints[ruta_id]]

    # Leer encharcamientos filtrados desde S3
    response = s3.get_object(Bucket=bucket, Key=processed_key)
    df_ench = pd.read_csv(io.BytesIO(response["Body"].read()))

    # Agrupar puntos críticos
    puntos = (
        df_ench.groupby(["lat_round", "lon_round"])
        .agg(frecuencia=("lat_round", "count"))
        .reset_index()
        .sort_values("frecuencia", ascending=False)
    )

    # Colonia más frecuente
    colonia_por_punto = (
        df_ench.groupby(["lat_round", "lon_round"])["colonia_catalogo"]
        .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else "Desconocida")
        .reset_index()
    )
    puntos = puntos.merge(colonia_por_punto, on=["lat_round", "lon_round"], how="left")

    # Mes pico
    if "fecha_reporte" in df_ench.columns:
        df_ench["mes"] = pd.to_datetime(df_ench["fecha_reporte"], errors="coerce").dt.month
        mes_pico = (
            df_ench.groupby(["lat_round", "lon_round"])["mes"]
            .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else 6)
            .reset_index()
            .rename(columns={"mes": "mes_pico"})
        )
        puntos = puntos.merge(mes_pico, on=["lat_round", "lon_round"], how="left")
    else:
        puntos["mes_pico"] = 6

    puntos["mes_pico"] = puntos["mes_pico"].fillna(6).astype(int)

    # Seleccionar top N
    top_n = puntos.head(n_top).reset_index(drop=True)

    # Calcular features de rutas
    rutas_meta = {}
    for ruta_id, waypoints in rutas_waypoints.items():
        centroid = _route_centroid(waypoints)
        length = _route_length(waypoints)
        n_near = _count_points_near_route(puntos, waypoints, radius_m=5000.0)
        rutas_meta[ruta_id] = {
            "lat_ruta_centroid": centroid[1],
            "lon_ruta_centroid": centroid[0],
            "ruta_length": length,
            "n_puntos_near_ruta": n_near,
        }

    # Generar pares con features
    rutas_ids = list(rutas_waypoints.keys())
    feature_rows = []
    metadata_rows = []

    for i, (_, punto_row) in enumerate(top_n.iterrows()):
        punto = (punto_row["lon_round"], punto_row["lat_round"])
        u_id = f"U{i+1}"
        u_nombre = punto_row["colonia_catalogo"]

        for ruta_id in rutas_ids:
            waypoints = rutas_waypoints[ruta_id]
            dist = _distance_point_to_route(punto, waypoints)
            meta = rutas_meta[ruta_id]

            feature_rows.append([
                punto_row["frecuencia"],
                punto_row["lat_round"],
                punto_row["lon_round"],
                punto_row["mes_pico"],
                meta["lat_ruta_centroid"],
                meta["lon_ruta_centroid"],
                meta["ruta_length"],
                meta["n_puntos_near_ruta"],
                dist,
            ])

            metadata_rows.append({
                "a_id": u_id,
                "b_id": ruta_id,
                "a_nombre": u_nombre,
                "b_nombre": rutas_nombres[ruta_id],
            })

    # CSV de features (sin header, solo valores — formato para Batch Transform)
    inference_df = pd.DataFrame(feature_rows, columns=FEATURE_COLS)
    csv_buffer = io.StringIO()
    inference_df.to_csv(csv_buffer, index=False, header=False)

    s3.put_object(
        Bucket=bucket,
        Key=inference_output_key,
        Body=csv_buffer.getvalue().encode("utf-8"),
        ContentType="text/csv",
    )

    # CSV de metadata (para reconstruir el dataset final)
    metadata_df = pd.DataFrame(metadata_rows)
    meta_buffer = io.StringIO()
    metadata_df.to_csv(meta_buffer, index=False)

    s3.put_object(
        Bucket=bucket,
        Key=metadata_output_key,
        Body=meta_buffer.getvalue().encode("utf-8"),
        ContentType="text/csv",
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Features generadas para {len(feature_rows)} pares.",
            "inference_key": inference_output_key,
            "metadata_key": metadata_output_key,
            "n_pairs": len(feature_rows),
        }),
    }
