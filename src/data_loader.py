"""
Módulo 1: Carga y filtrado de datos crudos de SACMEX.

Responsabilidad:
    Leer el CSV de reportes de agua, filtrar encharcamientos
    y limpiar coordenadas geográficas.

Origen: Notebook 01 (celdas 1-4)
"""

from pathlib import Path

import pandas as pd


def load_and_filter(
    csv_path: Path,
    reporte_filter: str,
    coordinate_decimals: int,
) -> pd.DataFrame:
    """
    Carga el CSV crudo de SACMEX y retorna un DataFrame filtrado
    con encharcamientos georreferenciados.

    Parámetros
    ----------
    csv_path : Path
        Ruta al archivo CSV de reportes.
    reporte_filter : str
        Texto a buscar en la columna 'reporte' (case-insensitive).
    coordinate_decimals : int
        Decimales para redondear lat/lon.

    Retorna
    -------
    pd.DataFrame
        DataFrame con columnas: latitud, longitud, lat_round, lon_round,
        colonia_catalogo, fecha_reporte, alcaldia_catalogo.
    """
    df = pd.read_csv(csv_path)

    # Filtrar por tipo de reporte
    mask = df["reporte"].str.lower().str.contains(reporte_filter, na=False)
    df_filtered = df[mask].copy()

    # Eliminar filas sin coordenadas
    df_filtered = df_filtered.dropna(subset=["latitud", "longitud"])

    # Convertir a numérico
    df_filtered["latitud"] = pd.to_numeric(df_filtered["latitud"], errors="coerce")
    df_filtered["longitud"] = pd.to_numeric(df_filtered["longitud"], errors="coerce")
    df_filtered = df_filtered.dropna(subset=["latitud", "longitud"])

    # Redondear coordenadas
    df_filtered["lat_round"] = df_filtered["latitud"].round(coordinate_decimals)
    df_filtered["lon_round"] = df_filtered["longitud"].round(coordinate_decimals)

    # Retornar solo columnas relevantes
    columns = [
        "latitud",
        "longitud",
        "lat_round",
        "lon_round",
        "colonia_catalogo",
        "alcaldia_catalogo",
        "fecha_reporte",
    ]
    return df_filtered[columns].reset_index(drop=True)
