"""
Script para lanzar un job de Batch Transform en SageMaker.

Lee el input de inferencia desde S3, ejecuta predicciones con el
modelo entrenado, y escribe el dataset final de scores en S3.

Flujo:
    s3://bucket/inference/input.csv (features sin header)
        → Batch Transform (modelo Random Forest)
    s3://bucket/inference/input.csv.out (predicciones)
        → Post-procesamiento
    s3://bucket/scores/dataset_real_4x4.csv (formato final)

Uso:
    export MODEL_ARTIFACT="s3://bucket/model/sklearn-XXXX/output/model.tar.gz"
    python -m sagemaker.launch_batch_transform

Costo: $0 (ml.t3.medium Free Tier, ~2 min por ejecución)
"""

import io
import os
import time
from pathlib import Path

import boto3
import pandas as pd
import sagemaker
from sagemaker.sklearn import SKLearnModel


# ─── Configuración ──────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent

BUCKET_NAME = os.environ.get("TRAFFIC_RAIN_BUCKET", "traffic-rain-ai-CHANGE-ME")
ROLE_ARN = os.environ.get("SAGEMAKER_ROLE_ARN", "arn:aws:iam::CHANGE-ME:role/SageMakerExecutionRole")
REGION = os.environ.get("AWS_REGION", "us-east-1")
MODEL_ARTIFACT = os.environ.get("MODEL_ARTIFACT", "")

# Prefijos S3
INFERENCE_INPUT_KEY = "inference/input.csv"
INFERENCE_OUTPUT_PREFIX = "inference"
METADATA_KEY = "inference/metadata.csv"
SCORES_OUTPUT_KEY = "scores/dataset_real_4x4.csv"


# ─── Script ──────────────────────────────────────────────────────────────────


def launch():
    """Lanza Batch Transform y post-procesa los resultados."""
    print("=" * 60)
    print("LANZANDO BATCH TRANSFORM EN SAGEMAKER")
    print("=" * 60)

    if not MODEL_ARTIFACT:
        print("\n  ERROR: Debes configurar MODEL_ARTIFACT")
        print("  export MODEL_ARTIFACT='s3://bucket/model/.../model.tar.gz'")
        return

    # Sesión
    session = sagemaker.Session(boto_session=boto3.Session(region_name=REGION))
    s3_client = boto3.client("s3", region_name=REGION)

    # Verificar que existe el input
    print(f"\n1. Verificando input en s3://{BUCKET_NAME}/{INFERENCE_INPUT_KEY}")
    try:
        s3_client.head_object(Bucket=BUCKET_NAME, Key=INFERENCE_INPUT_KEY)
        print("   ✓ Input encontrado")
    except Exception:
        print("   ✗ Input no encontrado. Ejecuta la Lambda feature_engineer primero.")
        return

    # Crear modelo
    print(f"\n2. Creando modelo desde: {MODEL_ARTIFACT}")
    model = SKLearnModel(
        model_data=MODEL_ARTIFACT,
        role=ROLE_ARN,
        entry_point="train.py",
        source_dir=str(PROJECT_ROOT / "sagemaker"),
        framework_version="1.2-1",
        py_version="py3",
        sagemaker_session=session,
    )

    # Lanzar Batch Transform
    print("\n3. Lanzando Batch Transform...")
    print("   Instancia: ml.t3.medium (Free Tier)")
    print("   Esto puede tomar 3-5 minutos (setup + procesamiento)...")

    transformer = model.transformer(
        instance_count=1,
        instance_type="ml.t3.medium",
        output_path=f"s3://{BUCKET_NAME}/{INFERENCE_OUTPUT_PREFIX}",
        accept="text/csv",
        strategy="SingleRecord",
    )

    transformer.transform(
        data=f"s3://{BUCKET_NAME}/{INFERENCE_INPUT_KEY}",
        content_type="text/csv",
        split_type="Line",
    )

    transformer.wait()
    print("   ✓ Batch Transform completo")

    # 4. Post-procesar: combinar predicciones con metadata
    print("\n4. Post-procesando resultados...")

    # Leer predicciones (input.csv.out)
    predictions_key = f"{INFERENCE_OUTPUT_PREFIX}/input.csv.out"
    response = s3_client.get_object(Bucket=BUCKET_NAME, Key=predictions_key)
    predictions_raw = response["Body"].read().decode("utf-8").strip()
    scores = [round(float(line), 2) for line in predictions_raw.split("\n")]

    # Leer metadata
    response = s3_client.get_object(Bucket=BUCKET_NAME, Key=METADATA_KEY)
    metadata_df = pd.read_csv(io.BytesIO(response["Body"].read()))

    # Combinar
    metadata_df["score"] = scores

    # Reordenar columnas al formato esperado
    final_df = metadata_df[["a_id", "b_id", "score", "a_nombre", "b_nombre"]]

    print(f"   Scores generados: {len(final_df)} pares")
    print(f"\n   Matriz de scores:")
    pivot = final_df.pivot(index="a_id", columns="b_id", values="score")
    print(pivot.to_string())

    # Escribir dataset final en S3
    csv_buffer = io.StringIO()
    final_df.to_csv(csv_buffer, index=False)

    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=SCORES_OUTPUT_KEY,
        Body=csv_buffer.getvalue().encode("utf-8"),
        ContentType="text/csv",
    )

    print(f"\n5. Dataset final guardado en: s3://{BUCKET_NAME}/{SCORES_OUTPUT_KEY}")

    print("\n" + "=" * 60)
    print("BATCH TRANSFORM EXITOSO")
    print("=" * 60)
    print(f"\n  El pipeline Lambda puede continuar desde:")
    print(f"  qubo_builder → scores_key: '{SCORES_OUTPUT_KEY}'")


if __name__ == "__main__":
    launch()
