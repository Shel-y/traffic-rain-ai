"""
Evaluación local del modelo Random Forest antes de desplegar en SageMaker.

Entrena el modelo en la máquina local con la misma configuración
que usará SageMaker, evalúa contra el test set e imprime métricas
y ejemplos de predicción.

Uso:
    python -m sagemaker.local_evaluate

Prerequisito:
    python -m sagemaker.prepare_training_data
"""

from pathlib import Path

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

# Mismos hiperparámetros que train.py
HYPERPARAMS = {
    "n_estimators": 100,
    "max_depth": 10,
    "min_samples_split": 5,
    "min_samples_leaf": 2,
    "random_state": 2026,
    "n_jobs": -1,
}

# Criterios de éxito
R2_THRESHOLD = 0.85
MAE_THRESHOLD = 0.05


# ─── Evaluación ─────────────────────────────────────────────────────────────


def evaluate_locally():
    """Entrena y evalúa el modelo localmente."""
    print("=" * 60)
    print("EVALUACIÓN LOCAL — Random Forest Regressor")
    print("=" * 60)

    # Verificar datos
    if not TRAIN_PATH.exists() or not TEST_PATH.exists():
        print(f"\n  ERROR: No se encontraron los datos de training.")
        print(f"  Ejecuta primero: python -m sagemaker.prepare_training_data")
        return

    # Cargar datos
    print("\n1. Cargando datos...")
    df_train = pd.read_csv(TRAIN_PATH)
    df_test = pd.read_csv(TEST_PATH)

    X_train = df_train[FEATURE_COLS].values
    y_train = df_train[TARGET_COL].values
    X_test = df_test[FEATURE_COLS].values
    y_test = df_test[TARGET_COL].values

    print(f"   Train: {len(X_train)} filas")
    print(f"   Test:  {len(X_test)} filas")
    print(f"   Features: {len(FEATURE_COLS)}")

    # Entrenar
    print("\n2. Entrenando modelo...")
    print(f"   Hiperparámetros: {HYPERPARAMS}")
    model = RandomForestRegressor(**HYPERPARAMS)
    model.fit(X_train, y_train)
    print("   ✓ Modelo entrenado")

    # Cross-validation
    print("\n3. Validación cruzada (5-fold en train)...")
    cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring="r2")
    print(f"   R² CV: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # Métricas en test
    print("\n4. Métricas en TEST set...")
    y_pred = model.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    print(f"   R²:   {r2:.4f}")
    print(f"   MAE:  {mae:.4f}")
    print(f"   RMSE: {rmse:.4f}")

    # Criterios de éxito
    print("\n5. Criterios de éxito...")
    r2_pass = r2 >= R2_THRESHOLD
    mae_pass = mae <= MAE_THRESHOLD

    print(f"   R² ≥ {R2_THRESHOLD}:  {'✓ CUMPLE' if r2_pass else '✗ NO CUMPLE'} ({r2:.4f})")
    print(f"   MAE ≤ {MAE_THRESHOLD}: {'✓ CUMPLE' if mae_pass else '✗ NO CUMPLE'} ({mae:.4f})")

    if r2_pass and mae_pass:
        print("\n   ═══════════════════════════════════════")
        print("   ✓ MODELO APROBADO — Listo para SageMaker")
        print("   ═══════════════════════════════════════")
    else:
        print("\n   ═══════════════════════════════════════")
        print("   ✗ MODELO NO CUMPLE CRITERIOS")
        print("   Mantener heurística de distancia por ahora.")
        print("   ═══════════════════════════════════════")

    # Feature importances
    print("\n6. Feature importances...")
    importances = model.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    for idx in sorted_idx:
        bar = "█" * int(importances[idx] * 40)
        print(f"   {FEATURE_COLS[idx]:25s} {importances[idx]:.4f} {bar}")

    # Ejemplos de predicción
    print("\n7. Ejemplos de predicción (test set)...")
    print(f"   {'Real':>8s}  {'Predicho':>8s}  {'Error':>8s}  Colonia → Ruta")
    print(f"   {'─'*8}  {'─'*8}  {'─'*8}  {'─'*30}")

    # Seleccionar 10 ejemplos distribuidos
    n_examples = min(10, len(df_test))
    example_indices = np.linspace(0, len(df_test) - 1, n_examples, dtype=int)

    for idx in example_indices:
        real = y_test[idx]
        pred = y_pred[idx]
        error = abs(real - pred)
        row = df_test.iloc[idx]
        colonia = row.get("colonia", "?")
        ruta = row.get("ruta_nombre", row.get("ruta_id", "?"))
        print(f"   {real:8.4f}  {pred:8.4f}  {error:8.4f}  {colonia} → {ruta}")

    # Distribución de errores
    print("\n8. Distribución de errores absolutos...")
    errors = np.abs(y_test - y_pred)
    percentiles = [50, 75, 90, 95, 99]
    for p in percentiles:
        val = np.percentile(errors, p)
        print(f"   P{p:2d}: {val:.4f}")

    print("\n" + "=" * 60)
    print("EVALUACIÓN LOCAL COMPLETA")
    print("=" * 60)


if __name__ == "__main__":
    evaluate_locally()
