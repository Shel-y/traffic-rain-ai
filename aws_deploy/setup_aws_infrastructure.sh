#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# Traffic Rain Risk Optimizer — Setup de infraestructura AWS
#
# Este script crea:
#   1. Bucket S3 para datos y modelos
#   2. Rol IAM para SageMaker con permisos de S3
#
# Requisitos:
#   - AWS CLI instalado y configurado (aws configure)
#   - Permisos de IAM para crear roles, políticas y buckets
#
# Uso:
#   chmod +x sagemaker/setup_aws_infrastructure.sh
#   ./sagemaker/setup_aws_infrastructure.sh
#
# Costo: $0 (S3 Free Tier: 5 GB, IAM: sin costo)
# ══════════════════════════════════════════════════════════════════════════════

set -e  # Detener en cualquier error

# ─── Obtener Account ID automáticamente ──────────────────────────────────────
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region || echo "us-east-1")

echo "══════════════════════════════════════════════════════════"
echo "SETUP DE INFRAESTRUCTURA AWS"
echo "══════════════════════════════════════════════════════════"
echo ""
echo "  Account ID: $ACCOUNT_ID"
echo "  Región:     $REGION"
echo ""

# ─── Variables ───────────────────────────────────────────────────────────────
BUCKET_NAME="traffic-rain-ai-${ACCOUNT_ID}"
ROLE_NAME="TrafficRainSageMakerRole"
POLICY_NAME="TrafficRainS3Policy"

# ══════════════════════════════════════════════════════════════════════════════
# PASO 1: Crear bucket S3
# ══════════════════════════════════════════════════════════════════════════════
echo "─── Paso 1: Creando bucket S3 ───"
echo "  Bucket: $BUCKET_NAME"

if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
    echo "  ✓ Bucket ya existe, saltando creación."
else
    if [ "$REGION" = "us-east-1" ]; then
        aws s3api create-bucket \
            --bucket "$BUCKET_NAME" \
            --region "$REGION"
    else
        aws s3api create-bucket \
            --bucket "$BUCKET_NAME" \
            --region "$REGION" \
            --create-bucket-configuration LocationConstraint="$REGION"
    fi
    echo "  ✓ Bucket creado."
fi

# Bloquear acceso público (seguridad)
aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
echo "  ✓ Acceso público bloqueado."
echo ""

# ══════════════════════════════════════════════════════════════════════════════
# PASO 2: Crear rol IAM para SageMaker
# ══════════════════════════════════════════════════════════════════════════════
echo "─── Paso 2: Creando rol IAM ───"
echo "  Rol: $ROLE_NAME"

# Trust policy (permite que SageMaker asuma el rol)
TRUST_POLICY='{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "sagemaker.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}'

# Verificar si el rol ya existe
if aws iam get-role --role-name "$ROLE_NAME" 2>/dev/null; then
    echo "  ✓ Rol ya existe, saltando creación."
else
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document "$TRUST_POLICY" \
        --description "Rol para SageMaker - Traffic Rain Risk Optimizer"
    echo "  ✓ Rol creado."
fi

# ══════════════════════════════════════════════════════════════════════════════
# PASO 3: Crear y adjuntar política de S3
# ══════════════════════════════════════════════════════════════════════════════
echo ""
echo "─── Paso 3: Configurando permisos ───"

# Política de S3 (acceso solo a nuestro bucket)
S3_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "S3FullAccessOurBucket",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::${BUCKET_NAME}",
                "arn:aws:s3:::${BUCKET_NAME}/*"
            ]
        },
        {
            "Sid": "CloudWatchLogs",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        }
    ]
}
EOF
)

# Crear o actualizar la política inline
aws iam put-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name "$POLICY_NAME" \
    --policy-document "$S3_POLICY"
echo "  ✓ Política S3 adjuntada."

# Adjuntar la política administrada de SageMaker (necesaria para training jobs)
aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess" 2>/dev/null || true
echo "  ✓ AmazonSageMakerFullAccess adjuntada."

# ══════════════════════════════════════════════════════════════════════════════
# PASO 4: Subir datos crudos a S3
# ══════════════════════════════════════════════════════════════════════════════
echo ""
echo "─── Paso 4: Subiendo datos a S3 ───"

RAW_FILE="data/raw/reportes_agua_2024_01(1).csv"
PROCESSED_FILE="data/processed/dataset_real_4x4(2).csv"

if [ -f "$RAW_FILE" ]; then
    aws s3 cp "$RAW_FILE" "s3://${BUCKET_NAME}/raw/reportes_agua_2024_01.csv"
    echo "  ✓ Datos crudos subidos a raw/"
else
    echo "  ⚠ Archivo raw no encontrado (${RAW_FILE}). Súbelo manualmente."
fi

if [ -f "$PROCESSED_FILE" ]; then
    aws s3 cp "$PROCESSED_FILE" "s3://${BUCKET_NAME}/scores/dataset_real_4x4.csv"
    echo "  ✓ Dataset procesado subido a scores/"
else
    echo "  ⚠ Archivo procesado no encontrado."
fi

# ══════════════════════════════════════════════════════════════════════════════
# RESUMEN
# ══════════════════════════════════════════════════════════════════════════════
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

echo ""
echo "══════════════════════════════════════════════════════════"
echo "✓ INFRAESTRUCTURA LISTA"
echo "══════════════════════════════════════════════════════════"
echo ""
echo "  Bucket:   $BUCKET_NAME"
echo "  Rol ARN:  $ROLE_ARN"
echo "  Región:   $REGION"
echo ""
echo "─── Configura tus variables de entorno ───"
echo ""
echo "  export TRAFFIC_RAIN_BUCKET=\"$BUCKET_NAME\""
echo "  export SAGEMAKER_ROLE_ARN=\"$ROLE_ARN\""
echo "  export AWS_REGION=\"$REGION\""
echo ""
echo "─── Siguientes pasos ───"
echo ""
echo "  1. Preparar datos de training (local):"
echo "     python -m sagemaker.prepare_training_data"
echo ""
echo "  2. Lanzar training en SageMaker:"
echo "     python -m sagemaker.launch_training"
echo ""
echo "  3. Lanzar Batch Transform:"
echo "     export MODEL_ARTIFACT=\"<URI del modelo que imprime launch_training>\""
echo "     python -m sagemaker.launch_batch_transform"
echo ""
echo "══════════════════════════════════════════════════════════"
