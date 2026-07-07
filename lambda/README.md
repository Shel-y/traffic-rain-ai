# Lambda Functions — Traffic Rain Risk Optimizer

Este directorio contiene las funciones AWS Lambda para la Fase 2.1 del proyecto.

## Estructura

```
lambda/
├── data_loader/          ← Lee CSV crudo de S3, filtra encharcamientos
├── qubo_builder/         ← Lee scores, construye matriz QUBO
├── classical_solver/     ← Resuelve por fuerza bruta + húngaro
└── evaluator/            ← Compara resultados, genera gráficas
```

## Flujo de datos en S3

```
s3://traffic-rain-ai-XXXX/
├── raw/                  ← Entrada: CSV SACMEX
├── processed/            ← data_loader → encharcamientos filtrados
├── scores/               ← risk_scoring → matriz de scores 4×4
├── qubo/                 ← qubo_builder → matriz QUBO (NPZ)
├── results/              ← classical_solver/qaoa → JSON de resultados
└── figures/              ← evaluator → gráficas PNG
```

## Evento de ejemplo (data_loader)

```json
{
    "bucket": "traffic-rain-ai-123456789012",
    "raw_key": "raw/reportes_agua_2024_01.csv",
    "output_key": "processed/encharcamientos_filtered.csv",
    "reporte_filter": "encharcamiento",
    "coordinate_decimals": 3
}
```

## Despliegue

Cada función se empaqueta con sus dependencias:

```bash
cd lambda/data_loader
pip install -r requirements.txt -t .
zip -r ../data_loader.zip .
```

## Costo

$0/mes dentro del AWS Free Tier (ver ADR-011 en DECISIONS.md).
