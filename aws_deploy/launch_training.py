"""
Script para lanzar el job de entrenamiento en SageMaker.

Sube los datos de training a S3, configura el estimador SKLearn
y lanza el training job.

Uso:
    python -m sagemaker.launch_training

Requisitos:
    - AWS CLI configurado (aws configure)
    - Rol de SageMaker con permisos de S3
    - Datos de training generados (data/training/train.csv, test.csv)

Costo: $0 (ml.m5.large incluido en Free Tier, 250 hrs/2 meses)
"""

import os
from pathlib import Path

import boto3
import sagemaker

# Compatibilidad con múltiples versiones del SDK de SageMaker.
# En v2.200+ el módulo sklearn se movió a un paquete separado.
try:
    from sagemaker.sklearn.estimator import SKLearn
except ModuleNotFoundError:
    from sagemaker.sklearn import SKLearn


# ─── Configuración ──────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAINING_DIR = PROJECT_ROOT / "data" / "training"

# Estos valores deben configurarse para tu cuenta
BUCKET_NAME = os.environ.get("TRAFFIC_RAIN_BUCKET", "traffic-rain-ai-646715757812")
ROLE_ARN = os.environ.get("SAGEMAKER_ROLE_ARN", "arn:aws:iam::646715757812:role/SageMakerExecutionRole")
REGION = os.environ.get("AWS_REGION", "us-east-1")

# Prefijos en S3
S3_TRAINING_PREFIX = "training"
S3_MODEL_PREFIX = "model"


# ─── Script ──────────────────────────────────────────────────────────────────


def launch():
    """Sube datos y lanza el training job."""
    print("=" * 60)
    print("LANZANDO TRAINING JOB EN SAGEMAKER")
    print("=" * 60)

    # Verificar que existen los datos de training
    train_path = TRAINING_DIR / "train.csv"
    test_path = TRAINING_DIR / "test.csv"

    if not train_path.exists():
        print(f"\n  ERROR: No se encontró {train_path}")
        print("  Ejecuta primero: python -m sagemaker.prepare_training_data")
        return

    # Sesión de SageMaker
    session = sagemaker.Session(boto_session=boto3.Session(region_name=REGION))

    # Subir datos a S3
    print(f"\n1. Subiendo datos a s3://{BUCKET_NAME}/{S3_TRAINING_PREFIX}/")
    train_s3 = session.upload_data(
        path=str(train_path),
        bucket=BUCKET_NAME,
        key_prefix=f"{S3_TRAINING_PREFIX}/train",
    )
    test_s3 = session.upload_data(
        path=str(test_path),
        bucket=BUCKET_NAME,
        key_prefix=f"{S3_TRAINING_PREFIX}/test",
    )
    print(f"   Train: {train_s3}")
    print(f"   Test:  {test_s3}")

    # Configurar estimador
    print("\n2. Configurando estimador SKLearn...")
    sklearn_estimator = SKLearn(
        entry_point="train.py",
        source_dir=str(PROJECT_ROOT / "aws_deploy"),
        role=ROLE_ARN,
        instance_type="ml.m5.large",  # Free Tier (250 hrs/2 meses)
        instance_count=1,
        framework_version="1.2-1",
        py_version="py3",
        sagemaker_session=session,
        output_path=f"s3://{BUCKET_NAME}/{S3_MODEL_PREFIX}",
        hyperparameters={
            "n-estimators": 100,
            "max-depth": 10,
            "min-samples-split": 5,
            "min-samples-leaf": 2,
        },
    )

    # Lanzar training
    print("\n3. Lanzando training job...")
    print("   Instancia: ml.m5.large (Free Tier)")
    print("   Tiempo estimado: <5 minutos")

    sklearn_estimator.fit({
        "train": train_s3,
        "test": test_s3,
    })

    # Resultado
    model_artifact = sklearn_estimator.model_data
    print(f"\n4. Training completo.")
    print(f"   Modelo guardado en: {model_artifact}")

    print("\n" + "=" * 60)
    print("TRAINING JOB EXITOSO")
    print("=" * 60)
    print(f"\n  Para lanzar Batch Transform, usa:")
    print(f"  MODEL_ARTIFACT={model_artifact}")
    print(f"  python -m sagemaker.launch_batch_transform")


if __name__ == "__main__":
    launch()
