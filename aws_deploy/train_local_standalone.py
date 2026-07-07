"""
Entrenamiento LOCAL standalone del modelo Random Forest.

Este script NO importa nada de src/, lambda/, braket, ni sagemaker.
Solo usa pandas, numpy y scikit-learn.

Genera: data/model/model.joblib (listo para subir a S3)

Uso:
    python aws_deploy/train_local_standalone.py

Requisitos mínimos:
    pip install pandas numpy scikit-learn joblib
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score


# ─── Configuración ──────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAINING_DIR = PROJECT_ROOT / "data" / "training"
TRAIN_PATH = TRAINING_DIR / "train.csv"
TEST_PATH = TRAINING_DIR / "test.csv"
MODEL_OUTPUT_DIR = PROJECT_ROOT / "data" / "model"
MODEL_OUTPUT_PATH = MODEL_OUTPUT_DIR / "model.joblib"

FEATURE_COLS = [
    "frecuencia",
    "lat_punto",
    "lon_punto",
    "mes_pico",
    "lat_ruta_centroid",
    "lon_ruta_centroid",
    "ruta_length",
    "n_puntos_near_ruta",
    "dist_to_route",
]

TARGET_COL = "score"

HYPERPARAMS = {
    "n_estimators": 100,
    "max_depth": 10,
    "min_samples_split": 5,
    "min_samples_leaf": 2,
    "random_state": 2026,
    "n_jobs": -1,
}

R2_THRESHOLD = 0.85
MAE_THRESHOLD = 0.05


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    print("=" * 60)
    print("ENTRENAMIENTO LOCAL STANDALONE")
    print("(Sin dependencias de Braket, SageMaker ni src/)")
    print("=" * 60)

    # Verificar datos
    if not TRAIN_PATH.exists():
        print(f"\n  ERROR: No se encontró {TRAIN_PATH}")
        print("  Ejecuta primero: python aws_deploy/prepare_training_data.py")
        print("  (o genera los CSV manualmente)")
        return

    # Cargar datos
    print("\n1. Cargando datos...")
    df_train = pd.read_csv(TRAIN_PATH)
    df_test = pd.read_csv(TEST_PATH) if TEST_PATH.exists() else None

    X_train = df_train[FEATURE_COLS].values
    y_train = df_train[TARGET_COL].values
    print(f"   Train: {len(X_train)} filas, {len(FEATURE_COLS)} features")

    X_test, y_test = None, None
    if df_test is not None:
        X_test = df_test[FEATURE_COLS].values
        y_test = df_test[TARGET_COL].values
        print(f"   Test:  {len(X_test)} filas")

    # Entrenar
    print(f"\n2. Entrenando Random Forest...")
    print(f"   {HYPERPARAMS}")
    model = RandomForestRegressor(**HYPERPARAMS)
    model.fit(X_train, y_train)
    print("   ✓ Modelo entrenado")

    # Cross-validation
    print("\n3. Validación cruzada (5-fold)...")
    cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring="r2")
    print(f"   R² CV: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # Métricas en test
    if X_test is not None:
        print("\n4. Métricas en TEST set...")
        y_pred = model.predict(X_test)
        r2 = r2_score(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))

        print(f"   R²:   {r2:.4f}")
        print(f"   MAE:  {mae:.4f}")
        print(f"   RMSE: {rmse:.4f}")

        # Criterios de éxito
        print(f"\n5. Criterios de éxito...")
        r2_pass = r2 >= R2_THRESHOLD
        mae_pass = mae <= MAE_THRESHOLD
        print(f"   R² ≥ {R2_THRESHOLD}:  {'✓ CUMPLE' if r2_pass else '✗ NO CUMPLE'} ({r2:.4f})")
        print(f"   MAE ≤ {MAE_THRESHOLD}: {'✓ CUMPLE' if mae_pass else '✗ NO CUMPLE'} ({mae:.4f})")

    # Feature importances
    print(f"\n6. Feature importances...")
    importances = model.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    for idx in sorted_idx:
        bar = "█" * int(importances[idx] * 40)
        print(f"   {FEATURE_COLS[idx]:25s} {importances[idx]:.4f} {bar}")

    # Guardar modelo
    print(f"\n7. Guardando modelo...")
    MODEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_OUTPUT_PATH)
    print(f"   ✓ Guardado en: {MODEL_OUTPUT_PATH}")
    print(f"   Tamaño: {MODEL_OUTPUT_PATH.stat().st_size / 1024:.0f} KB")

    # Instrucciones
    print("\n" + "=" * 60)
    print("✓ ENTRENAMIENTO COMPLETO")
    print("=" * 60)
    print(f"\n  Modelo: {MODEL_OUTPUT_PATH}")
    print(f"\n  Para subir a S3:")
    print(f"  aws s3 cp {MODEL_OUTPUT_PATH} s3://$TRAFFIC_RAIN_BUCKET/model/model.joblib")
    print(f"\n  Para usar en el pipeline local:")
    print(f"  import joblib")
    print(f"  model = joblib.load('{MODEL_OUTPUT_PATH}')")
    print(f"  scores = model.predict(X_features)")


if __name__ == "__main__":
    main()
