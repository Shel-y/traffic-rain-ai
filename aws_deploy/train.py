"""
Script de entrenamiento para SageMaker SKLearn Container.

Este script es ejecutado automáticamente por SageMaker dentro del
contenedor de scikit-learn. Recibe los datos desde S3 (copiados
automáticamente a /opt/ml/input/data/train/) y guarda el modelo
en /opt/ml/model/ (empaquetado automáticamente como model.tar.gz).

Algoritmo: Random Forest Regressor
Target: score (compatibilidad [0,1])
Features: 9 features geográficas y temporales
"""

import argparse
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score


# ─── Columnas ────────────────────────────────────────────────────────────────

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


# ─── Entrenamiento ──────────────────────────────────────────────────────────


def train(args):
    """Entrena el modelo Random Forest."""
    print("=" * 60)
    print("ENTRENAMIENTO: Random Forest Regressor")
    print("=" * 60)

    # Cargar datos
    train_path = os.path.join(args.train, "train.csv")
    print(f"\nCargando datos desde: {train_path}")
    df_train = pd.read_csv(train_path)

    # Separar features y target
    X_train = df_train[FEATURE_COLS].values
    y_train = df_train[TARGET_COL].values

    print(f"  Filas de training: {len(X_train)}")
    print(f"  Features: {len(FEATURE_COLS)}")

    # Cargar test si existe
    test_path = os.path.join(args.test, "test.csv") if args.test else None
    X_test, y_test = None, None
    if test_path and os.path.exists(test_path):
        df_test = pd.read_csv(test_path)
        X_test = df_test[FEATURE_COLS].values
        y_test = df_test[TARGET_COL].values
        print(f"  Filas de test: {len(X_test)}")

    # Configurar modelo
    model = RandomForestRegressor(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        min_samples_split=args.min_samples_split,
        min_samples_leaf=args.min_samples_leaf,
        random_state=2026,
        n_jobs=-1,
    )

    print(f"\nHiperparámetros:")
    print(f"  n_estimators: {args.n_estimators}")
    print(f"  max_depth: {args.max_depth}")
    print(f"  min_samples_split: {args.min_samples_split}")
    print(f"  min_samples_leaf: {args.min_samples_leaf}")

    # Cross-validation en training
    print("\nValidación cruzada (5-fold)...")
    cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring="r2")
    print(f"  R² CV: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # Entrenar modelo final
    print("\nEntrenando modelo final...")
    model.fit(X_train, y_train)

    # Métricas en training
    y_pred_train = model.predict(X_train)
    r2_train = r2_score(y_train, y_pred_train)
    mae_train = mean_absolute_error(y_train, y_pred_train)
    rmse_train = np.sqrt(mean_squared_error(y_train, y_pred_train))

    print(f"\nMétricas en TRAIN:")
    print(f"  R²:   {r2_train:.4f}")
    print(f"  MAE:  {mae_train:.4f}")
    print(f"  RMSE: {rmse_train:.4f}")

    # Métricas en test (si disponible)
    if X_test is not None:
        y_pred_test = model.predict(X_test)
        r2_test = r2_score(y_test, y_pred_test)
        mae_test = mean_absolute_error(y_test, y_pred_test)
        rmse_test = np.sqrt(mean_squared_error(y_test, y_pred_test))

        print(f"\nMétricas en TEST:")
        print(f"  R²:   {r2_test:.4f}")
        print(f"  MAE:  {mae_test:.4f}")
        print(f"  RMSE: {rmse_test:.4f}")

        # Criterios de éxito
        print(f"\n── CRITERIOS DE ÉXITO ──")
        print(f"  R² ≥ 0.85: {'✓ CUMPLE' if r2_test >= 0.85 else '✗ NO CUMPLE'} ({r2_test:.4f})")
        print(f"  MAE ≤ 0.05: {'✓ CUMPLE' if mae_test <= 0.05 else '✗ NO CUMPLE'} ({mae_test:.4f})")

    # Feature importances
    print(f"\nFeature importances:")
    importances = model.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    for idx in sorted_idx:
        print(f"  {FEATURE_COLS[idx]:25s} {importances[idx]:.4f}")

    # Guardar modelo
    model_path = os.path.join(args.model_dir, "model.joblib")
    joblib.dump(model, model_path)
    print(f"\nModelo guardado en: {model_path}")

    # Guardar metadata
    metadata = {
        "feature_cols": FEATURE_COLS,
        "target_col": TARGET_COL,
        "n_estimators": args.n_estimators,
        "max_depth": args.max_depth,
        "r2_cv": float(cv_scores.mean()),
        "r2_test": float(r2_test) if X_test is not None else None,
        "mae_test": float(mae_test) if X_test is not None else None,
    }
    metadata_path = os.path.join(args.model_dir, "metadata.json")
    import json
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata guardada en: {metadata_path}")

    print("\n" + "=" * 60)
    print("ENTRENAMIENTO COMPLETO")
    print("=" * 60)


# ─── Funciones requeridas por SageMaker para inferencia ──────────────────────


def model_fn(model_dir):
    """Carga el modelo (requerido por SageMaker SKLearn container)."""
    model_path = os.path.join(model_dir, "model.joblib")
    return joblib.load(model_path)


def input_fn(request_body, request_content_type):
    """Parsea el input de inferencia (CSV)."""
    if request_content_type == "text/csv":
        df = pd.read_csv(pd.io.common.StringIO(request_body), header=None)
        return df.values
    raise ValueError(f"Content type no soportado: {request_content_type}")


def predict_fn(input_data, model):
    """Ejecuta la predicción."""
    return model.predict(input_data)


def output_fn(prediction, accept):
    """Formatea la salida (CSV)."""
    return "\n".join(str(p) for p in prediction), "text/csv"


# ─── Entry point ─────────────────────────────────────────────────────────────


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    # Hiperparámetros
    parser.add_argument("--n-estimators", type=int, default=100)
    parser.add_argument("--max-depth", type=int, default=10)
    parser.add_argument("--min-samples-split", type=int, default=5)
    parser.add_argument("--min-samples-leaf", type=int, default=2)

    # Rutas de SageMaker (inyectadas automáticamente)
    parser.add_argument("--model-dir", type=str, default=os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    parser.add_argument("--train", type=str, default=os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train"))
    parser.add_argument("--test", type=str, default=os.environ.get("SM_CHANNEL_TEST", "/opt/ml/input/data/test"))

    args = parser.parse_args()
    train(args)
