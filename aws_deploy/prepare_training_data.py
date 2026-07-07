"""
Script de preparación del dataset de training para el modelo ML.

Genera ~7,976 pares (punto_critico × ruta) con features calculadas
a partir de los datos de SACMEX, usando la heurística de distancia
como ground truth para el score.

Uso:
    python -m sagemaker.prepare_training_data

Salida:
    data/training/train.csv
    data/training/test.csv
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    RAW_CSV_PATH,
    RUTAS_WAYPOINTS,
    RUTAS_NOMBRES,
    COORDINATE_DECIMALS,
    REPORTE_FILTER,
)
from src.risk_scoring import _haversine, _distance_point_to_route


# ─── Configuración ──────────────────────────────────────────────────────────

TRAINING_DIR = PROJECT_ROOT / "data" / "training"
TRAIN_OUTPUT = TRAINING_DIR / "train.csv"
TEST_OUTPUT = TRAINING_DIR / "test.csv"
TEST_FRACTION = 0.2
RANDOM_SEED = 2026


# ─── Funciones auxiliares ────────────────────────────────────────────────────


def _route_centroid(waypoints: list) -> tuple:
    """Calcula el centroide (lon, lat) de una ruta."""
    lons = [p[0] for p in waypoints]
    lats = [p[1] for p in waypoints]
    return (np.mean(lons), np.mean(lats))


def _route_length(waypoints: list) -> float:
    """Calcula la longitud total de una ruta en metros."""
    total = 0.0
    for i in range(len(waypoints) - 1):
        total += _haversine(
            waypoints[i][0], waypoints[i][1],
            waypoints[i + 1][0], waypoints[i + 1][1],
        )
    return total


def _count_points_near_route(
    all_points: pd.DataFrame, waypoints: list, radius_m: float = 5000.0
) -> int:
    """Cuenta cuántos puntos de encharcamiento están dentro de radius_m de la ruta."""
    count = 0
    for _, row in all_points.iterrows():
        punto = (row["lon_round"], row["lat_round"])
        dist = _distance_point_to_route(punto, waypoints)
        if dist <= radius_m:
            count += int(row["frecuencia"])
    return count


# ─── Pipeline principal ──────────────────────────────────────────────────────


def prepare_dataset():
    """Genera el dataset de training completo."""
    print("=" * 60)
    print("PREPARACIÓN DEL DATASET DE TRAINING")
    print("=" * 60)

    # 1. Cargar y filtrar datos
    print("\n1. Cargando datos crudos de SACMEX...")
    df = pd.read_csv(RAW_CSV_PATH)
    mask = df["reporte"].str.lower().str.contains(REPORTE_FILTER, na=False)
    df_ench = df[mask].copy()
    df_ench = df_ench.dropna(subset=["latitud", "longitud"])
    df_ench["latitud"] = pd.to_numeric(df_ench["latitud"], errors="coerce")
    df_ench["longitud"] = pd.to_numeric(df_ench["longitud"], errors="coerce")
    df_ench = df_ench.dropna(subset=["latitud", "longitud"])
    df_ench["lat_round"] = df_ench["latitud"].round(COORDINATE_DECIMALS)
    df_ench["lon_round"] = df_ench["longitud"].round(COORDINATE_DECIMALS)
    print(f"   Encharcamientos filtrados: {len(df_ench)}")

    # 2. Agrupar puntos críticos
    print("\n2. Agrupando puntos críticos...")
    puntos = (
        df_ench.groupby(["lat_round", "lon_round"])
        .agg(frecuencia=("lat_round", "count"))
        .reset_index()
        .sort_values("frecuencia", ascending=False)
    )

    # Obtener colonia más frecuente por punto
    colonia_por_punto = (
        df_ench.groupby(["lat_round", "lon_round"])["colonia_catalogo"]
        .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else "Desconocida")
        .reset_index()
    )
    puntos = puntos.merge(colonia_por_punto, on=["lat_round", "lon_round"], how="left")

    # Obtener mes pico por punto
    df_ench["mes"] = pd.to_datetime(df_ench["fecha_reporte"], errors="coerce").dt.month
    mes_pico = (
        df_ench.groupby(["lat_round", "lon_round"])["mes"]
        .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else 6)
        .reset_index()
        .rename(columns={"mes": "mes_pico"})
    )
    puntos = puntos.merge(mes_pico, on=["lat_round", "lon_round"], how="left")
    puntos["mes_pico"] = puntos["mes_pico"].fillna(6).astype(int)

    print(f"   Puntos críticos únicos: {len(puntos)}")

    # 3. Calcular features de rutas (estáticas)
    print("\n3. Calculando features de rutas...")
    rutas_meta = {}
    for ruta_id, waypoints in RUTAS_WAYPOINTS.items():
        centroid = _route_centroid(waypoints)
        length = _route_length(waypoints)
        n_near = _count_points_near_route(puntos, waypoints, radius_m=5000.0)
        rutas_meta[ruta_id] = {
            "lat_ruta_centroid": centroid[1],
            "lon_ruta_centroid": centroid[0],
            "ruta_length": length,
            "n_puntos_near_ruta": n_near,
        }
        print(f"   {ruta_id} ({RUTAS_NOMBRES[ruta_id]}): "
              f"length={length:.0f}m, puntos_cerca={n_near}")

    # 4. Generar todos los pares (punto × ruta) con features
    print("\n4. Generando pares punto×ruta...")
    rutas_ids = list(RUTAS_WAYPOINTS.keys())
    filas = []

    for _, punto_row in puntos.iterrows():
        punto = (punto_row["lon_round"], punto_row["lat_round"])

        for ruta_id in rutas_ids:
            waypoints = RUTAS_WAYPOINTS[ruta_id]
            dist = _distance_point_to_route(punto, waypoints)
            meta = rutas_meta[ruta_id]

            filas.append({
                # Features del punto
                "frecuencia": punto_row["frecuencia"],
                "lat_punto": punto_row["lat_round"],
                "lon_punto": punto_row["lon_round"],
                "mes_pico": punto_row["mes_pico"],
                # Features de la ruta
                "lat_ruta_centroid": meta["lat_ruta_centroid"],
                "lon_ruta_centroid": meta["lon_ruta_centroid"],
                "ruta_length": meta["ruta_length"],
                "n_puntos_near_ruta": meta["n_puntos_near_ruta"],
                # Feature de interacción
                "dist_to_route": dist,
                # Metadata (no se usa como feature)
                "colonia": punto_row["colonia_catalogo"],
                "ruta_id": ruta_id,
                "ruta_nombre": RUTAS_NOMBRES[ruta_id],
            })

    df_training = pd.DataFrame(filas)
    print(f"   Pares generados: {len(df_training)}")

    # 5. Calcular el score (target) usando la heurística de distancia
    print("\n5. Calculando scores (target)...")
    dist_min = df_training["dist_to_route"].min()
    dist_max = df_training["dist_to_route"].max()
    rango = dist_max - dist_min
    if rango == 0:
        rango = 1.0
    df_training["score"] = np.round(
        1.0 - (df_training["dist_to_route"] - dist_min) / rango, 4
    )

    print(f"   Score min: {df_training['score'].min():.4f}")
    print(f"   Score max: {df_training['score'].max():.4f}")
    print(f"   Score mean: {df_training['score'].mean():.4f}")

    # 6. Separar features y guardar
    print("\n6. Separando train/test y guardando...")
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)

    # Columnas de features (lo que el modelo recibe)
    feature_cols = [
        "frecuencia", "lat_punto", "lon_punto", "mes_pico",
        "lat_ruta_centroid", "lon_ruta_centroid", "ruta_length",
        "n_puntos_near_ruta", "dist_to_route",
    ]
    # Target
    target_col = "score"
    # Metadata (para reconstruir el CSV de scores después)
    meta_cols = ["colonia", "ruta_id", "ruta_nombre"]

    # Shuffle y split
    rng = np.random.default_rng(RANDOM_SEED)
    indices = rng.permutation(len(df_training))
    split_idx = int(len(indices) * (1 - TEST_FRACTION))

    train_idx = indices[:split_idx]
    test_idx = indices[split_idx:]

    # SageMaker SKLearn espera: target como primera columna, luego features
    train_df = df_training.iloc[train_idx][[target_col] + feature_cols + meta_cols]
    test_df = df_training.iloc[test_idx][[target_col] + feature_cols + meta_cols]

    train_df.to_csv(TRAIN_OUTPUT, index=False)
    test_df.to_csv(TEST_OUTPUT, index=False)

    print(f"   Train: {len(train_df)} filas → {TRAIN_OUTPUT}")
    print(f"   Test:  {len(test_df)} filas → {TEST_OUTPUT}")

    # 7. Resumen
    print("\n" + "=" * 60)
    print("DATASET LISTO PARA TRAINING")
    print("=" * 60)
    print(f"\n  Features ({len(feature_cols)}):")
    for f in feature_cols:
        print(f"    - {f}")
    print(f"\n  Target: {target_col}")
    print(f"  Total pares: {len(df_training)}")
    print(f"  Train: {len(train_df)} ({100*(1-TEST_FRACTION):.0f}%)")
    print(f"  Test:  {len(test_df)} ({100*TEST_FRACTION:.0f}%)")


if __name__ == "__main__":
    prepare_dataset()
