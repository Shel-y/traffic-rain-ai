"""
Lambda: data_loader

Lee el CSV crudo de SACMEX desde S3, filtra encharcamientos
y escribe el resultado en S3.

Evento esperado:
{
    "bucket": "traffic-rain-ai-XXXX",
    "raw_key": "raw/reportes_agua_2024_01.csv",
    "output_key": "processed/encharcamientos_filtered.csv",
    "reporte_filter": "encharcamiento",
    "coordinate_decimals": 3
}
"""

import io
import json

import boto3
import pandas as pd


s3 = boto3.client("s3")


def load_and_filter(csv_body: bytes, reporte_filter: str, coordinate_decimals: int) -> pd.DataFrame:
    """Lógica de filtrado (equivalente a src/data_loader.py)."""
    df = pd.read_csv(io.BytesIO(csv_body))

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
        "latitud", "longitud", "lat_round", "lon_round",
        "colonia_catalogo", "alcaldia_catalogo", "fecha_reporte",
    ]
    return df_filtered[columns].reset_index(drop=True)


def lambda_handler(event, context):
    """Punto de entrada de Lambda."""
    bucket = event["bucket"]
    raw_key = event["raw_key"]
    output_key = event["output_key"]
    reporte_filter = event.get("reporte_filter", "encharcamiento")
    coordinate_decimals = event.get("coordinate_decimals", 3)

    # Leer CSV desde S3
    response = s3.get_object(Bucket=bucket, Key=raw_key)
    csv_body = response["Body"].read()

    # Procesar
    df_filtered = load_and_filter(csv_body, reporte_filter, coordinate_decimals)

    # Escribir resultado en S3
    csv_buffer = io.StringIO()
    df_filtered.to_csv(csv_buffer, index=False)

    s3.put_object(
        Bucket=bucket,
        Key=output_key,
        Body=csv_buffer.getvalue().encode("utf-8"),
        ContentType="text/csv",
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Filtrado completo. {len(df_filtered)} encharcamientos.",
            "output_key": output_key,
            "rows": len(df_filtered),
        }),
    }
