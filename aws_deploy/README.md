# SageMaker — Traffic Rain Risk Optimizer

Scripts para entrenamiento y despliegue del modelo ML en Amazon SageMaker.

## Estructura

```
sagemaker/
├── prepare_training_data.py   ← Genera dataset de training (~7,900 pares)
├── train.py                   ← Script de entrenamiento (Random Forest)
├── launch_training.py         ← Lanza training job en SageMaker
├── launch_batch_transform.py  ← Lanza inferencia bajo demanda
└── README.md
```

## Flujo de uso

### 1. Preparar datos de training (local)

```bash
python -m sagemaker.prepare_training_data
```

Genera: `data/training/train.csv` y `data/training/test.csv`

### 2. Lanzar entrenamiento (SageMaker)

```bash
export TRAFFIC_RAIN_BUCKET="traffic-rain-ai-XXXX"
export SAGEMAKER_ROLE_ARN="arn:aws:iam::XXXX:role/SageMakerExecutionRole"
export AWS_REGION="us-east-1"

python -m sagemaker.launch_training
```

Resultado: modelo en `s3://bucket/model/.../model.tar.gz`

### 3. Ejecutar inferencia (Batch Transform)

```bash
export MODEL_ARTIFACT="s3://bucket/model/.../model.tar.gz"
python -m sagemaker.launch_batch_transform
```

Resultado: `s3://bucket/scores/dataset_real_4x4.csv`

## Costo

- Training: ml.t3.medium → Free Tier (250 hrs / 2 meses)
- Batch Transform: ml.t3.medium → Free Tier
- Total: **$0**

## Post-Free Tier

Si se agotan las 250 horas:
1. Entrenar localmente: `python sagemaker/train.py --train data/training`
2. Subir `model.tar.gz` manualmente a S3
3. O ejecutar inferencia localmente con joblib
