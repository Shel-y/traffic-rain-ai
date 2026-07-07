"""
Script maestro: ejecuta el pipeline completo (ML + QAOA) y exporta resultados JSON.

Flujo:
    1. Ejecuta el pipeline: datos → scoring → QUBO → clásico → QAOA → evaluación
    2. Serializa resultados a data/inference/final_results.json
    3. Valida que el JSON generado tenga el formato esperado por la app Streamlit

Uso:
    python run_all.py

    Con sincronización a S3:
    python run_all.py --sync-s3
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src import config


# ─── Constantes ──────────────────────────────────────────────────────────────

OUTPUT_DIR = config.PROJECT_ROOT / "data" / "inference"
OUTPUT_FILE = OUTPUT_DIR / "final_results.json"

# Campos obligatorios que la app de Streamlit espera
REQUIRED_FIELDS = [
    "metadata",
    "score_matrix",
    "score_df",
    "classical_result",
    "qaoa_result",
    "optimal_assignment",
]


# ─── Pipeline ────────────────────────────────────────────────────────────────


def run_pipeline():
    """
    Ejecuta el pipeline completo y retorna todos los resultados intermedios.

    Retorna
    -------
    dict con claves: score_df, score_matrix, classical_result, qaoa_result
    """
    print("=" * 60)
    print("TRAFFIC RAIN RISK OPTIMIZER — Pipeline completo")
    print("=" * 60)
    pipeline_start = time.time()

    # Paso 1: Cargar y filtrar datos
    print("\n[1/6] Cargando datos SACMEX...")
    from src.data_loader import load_and_filter

    df_encharcamientos = load_and_filter(
        csv_path=config.RAW_CSV_PATH,
        reporte_filter=config.REPORTE_FILTER,
        coordinate_decimals=config.COORDINATE_DECIMALS,
    )
    print(f"       {len(df_encharcamientos)} registros de encharcamientos")

    # Paso 2: Generar matriz de scores
    print("\n[2/6] Generando matriz de scores 4×4...")
    from src.risk_scoring import generate_score_matrix

    score_df, score_matrix = generate_score_matrix(
        df_encharcamientos=df_encharcamientos,
        rutas_waypoints=config.RUTAS_WAYPOINTS,
        rutas_nombres=config.RUTAS_NOMBRES,
        n_top=config.N_TOP_CRITICAL_POINTS,
    )
    print(f"       Matriz: {score_matrix.shape}")

    # Paso 3: Construir QUBO
    print("\n[3/6] Construyendo formulación QUBO...")
    from src.qubo_builder import build_qubo

    qubo_matrix, lambda_value = build_qubo(
        score_matrix=score_matrix,
        n_a=config.N_A,
        n_b=config.N_B,
        lambda_penalty=config.LAMBDA_PENALTY,
    )
    print(f"       QUBO: {qubo_matrix.shape}, λ={lambda_value}")

    # Paso 4: Resolver clásicamente
    print("\n[4/6] Resolviendo con solver clásico (fuerza bruta + húngaro)...")
    from src.classical_solver import solve_classical

    classical_result = solve_classical(
        score_matrix=score_matrix,
        qubo_matrix=qubo_matrix,
        n_a=config.N_A,
        n_b=config.N_B,
    )
    print(f"       Mejor score: {classical_result['best_score']:.4f}")
    print(f"       Bitstring:   {classical_result['best_bitstring']}")

    # Paso 5: Resolver con QAOA
    print("\n[5/6] Resolviendo con QAOA (Amazon Braket Local Simulator)...")
    print(f"       p={config.QAOA_P}, shots={config.QAOA_SHOTS}, seed={config.QAOA_SEED}")
    from src.optimizer import solve_qaoa

    qaoa_result = solve_qaoa(
        qubo_matrix=qubo_matrix,
        n_a=config.N_A,
        n_b=config.N_B,
        p=config.QAOA_P,
        shots=config.QAOA_SHOTS,
        seed=config.QAOA_SEED,
    )
    print(f"       Mejor energía: {qaoa_result['best_energy']:.4f}")
    print(f"       Bitstring:     {qaoa_result['best_bitstring']}")

    # Paso 6: Evaluar
    print("\n[6/6] Evaluando y generando gráficas...")
    from src.evaluator import evaluate

    evaluate(
        classical_result=classical_result,
        qaoa_result=qaoa_result,
        score_matrix=score_matrix,
        score_df=score_df,
        figures_dir=config.FIGURES_DIR,
    )

    pipeline_time = time.time() - pipeline_start
    print(f"\n  Pipeline total: {pipeline_time:.2f} s")

    return {
        "score_df": score_df,
        "score_matrix": score_matrix,
        "classical_result": classical_result,
        "qaoa_result": qaoa_result,
        "pipeline_time": pipeline_time,
    }


# ─── Serialización a JSON ────────────────────────────────────────────────────


def _decode_assignment(bitstring, n_a, n_b, score_df):
    """Decodifica bitstring en asignaciones legibles (usuario → ruta + score)."""
    assignments = []
    for i in range(n_a):
        for j in range(n_b):
            if bitstring[i * n_b + j] == "1":
                row = score_df[
                    (score_df["a_id"] == f"U{i+1}")
                    & (score_df["b_id"] == f"R{j+1}")
                ]
                if not row.empty:
                    r = row.iloc[0]
                    assignments.append({
                        "user_id": r["a_id"],
                        "user_name": r["a_nombre"],
                        "route_id": r["b_id"],
                        "route_name": r["b_nombre"],
                        "score": round(float(r["score"]), 4),
                    })
    return assignments


def build_json_output(results):
    """
    Construye el dict final para exportar como JSON.

    Estructura:
    {
        "metadata": { timestamp, pipeline_time, config... },
        "score_matrix": [[...], ...],
        "score_df": [ {a_id, b_id, score, a_nombre, b_nombre}, ... ],
        "classical_result": { bitstring, energy, score, assignment, time },
        "qaoa_result": { bitstring, energy, score, params, time, approx_ratio },
        "optimal_assignment": [ {user, route, score}, ... ]
    }
    """
    score_df = results["score_df"]
    score_matrix = results["score_matrix"]
    classical = results["classical_result"]
    qaoa = results["qaoa_result"]

    # Calcular score QAOA
    qaoa_score = 0.0
    n_a, n_b = config.N_A, config.N_B
    for i in range(n_a):
        for j in range(n_b):
            if qaoa["best_bitstring"][i * n_b + j] == "1":
                qaoa_score += score_matrix[i, j]

    # Approximation ratio
    approx_ratio = qaoa_score / classical["best_score"] if classical["best_score"] > 0 else 0.0

    # Verificar factibilidad QAOA
    x = np.array([int(b) for b in qaoa["best_bitstring"]]).reshape(n_a, n_b)
    qaoa_feasible = bool(np.all(x.sum(axis=1) == 1) and np.all(x.sum(axis=0) == 1))

    output = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pipeline_version": "1.0.0",
            "pipeline_time_seconds": round(results["pipeline_time"], 3),
            "config": {
                "n_users": config.N_A,
                "n_routes": config.N_B,
                "qaoa_p": config.QAOA_P,
                "qaoa_shots": config.QAOA_SHOTS,
                "qaoa_seed": config.QAOA_SEED,
                "lambda_penalty": config.LAMBDA_PENALTY,
            },
        },
        "score_matrix": score_matrix.tolist(),
        "score_df": score_df.to_dict(orient="records"),
        "classical_result": {
            "best_bitstring": classical["best_bitstring"],
            "best_energy": round(float(classical["best_energy"]), 4),
            "best_score": round(float(classical["best_score"]), 4),
            "best_assignment": list(classical["best_assignment"]),
            "hungarian_assignment": list(classical["hungarian_assignment"]),
            "execution_time_seconds": round(float(classical["execution_time"]), 4),
            "n_permutations_evaluated": len(classical["all_permutations"]),
        },
        "qaoa_result": {
            "best_bitstring": qaoa["best_bitstring"],
            "best_energy": round(float(qaoa["best_energy"]), 4),
            "best_score": round(float(qaoa_score), 4),
            "optimal_params": {
                "gamma": round(float(qaoa["optimal_params"][0]), 6),
                "beta": round(float(qaoa["optimal_params"][1]), 6),
            },
            "execution_time_seconds": round(float(qaoa["execution_time"]), 4),
            "approx_ratio": round(float(approx_ratio), 4),
            "is_feasible": qaoa_feasible,
            "solutions_match": qaoa["best_bitstring"] == classical["best_bitstring"],
            "top_counts": dict(
                sorted(qaoa["counts"].items(), key=lambda x: x[1], reverse=True)[:10]
            ),
        },
        "optimal_assignment": _decode_assignment(
            classical["best_bitstring"], n_a, n_b, score_df
        ),
    }

    return output


# ─── Validación ──────────────────────────────────────────────────────────────


def validate_json(output):
    """
    Valida que el JSON generado sea compatible con el formato esperado.

    Verifica:
    - Presencia de todos los campos requeridos
    - Tipos correctos de los valores
    - Integridad de la matriz de scores (dimensiones correctas)
    - Integridad del score_df (columnas esperadas)
    - Consistencia de asignación óptima
    """
    errors = []

    # 1. Campos requeridos
    for field in REQUIRED_FIELDS:
        if field not in output:
            errors.append(f"Campo requerido faltante: '{field}'")

    if errors:
        return False, errors

    # 2. Metadata
    meta = output["metadata"]
    if "generated_at" not in meta:
        errors.append("metadata.generated_at faltante")
    if "config" not in meta:
        errors.append("metadata.config faltante")
    else:
        for key in ["n_users", "n_routes", "qaoa_p", "qaoa_shots"]:
            if key not in meta["config"]:
                errors.append(f"metadata.config.{key} faltante")

    # 3. Score matrix (n_a × n_b)
    matrix = output["score_matrix"]
    n_a = meta.get("config", {}).get("n_users", 4)
    n_b = meta.get("config", {}).get("n_routes", 4)
    if len(matrix) != n_a:
        errors.append(f"score_matrix tiene {len(matrix)} filas, esperado {n_a}")
    elif any(len(row) != n_b for row in matrix):
        errors.append(f"score_matrix filas no tienen {n_b} columnas")

    # 4. Score DataFrame (columnas requeridas)
    required_cols = {"a_id", "b_id", "score", "a_nombre", "b_nombre"}
    if output["score_df"]:
        actual_cols = set(output["score_df"][0].keys())
        missing_cols = required_cols - actual_cols
        if missing_cols:
            errors.append(f"score_df columnas faltantes: {missing_cols}")
        if len(output["score_df"]) != n_a * n_b:
            errors.append(
                f"score_df tiene {len(output['score_df'])} registros, "
                f"esperado {n_a * n_b}"
            )

    # 5. Resultados clásicos
    classical = output["classical_result"]
    if len(classical.get("best_bitstring", "")) != n_a * n_b:
        errors.append(
            f"classical_result.best_bitstring longitud incorrecta "
            f"({len(classical.get('best_bitstring', ''))} vs {n_a * n_b})"
        )

    # 6. Resultados QAOA
    qaoa = output["qaoa_result"]
    if len(qaoa.get("best_bitstring", "")) != n_a * n_b:
        errors.append(
            f"qaoa_result.best_bitstring longitud incorrecta "
            f"({len(qaoa.get('best_bitstring', ''))} vs {n_a * n_b})"
        )
    if not (0.0 <= qaoa.get("approx_ratio", 0) <= 1.5):
        errors.append(
            f"qaoa_result.approx_ratio fuera de rango: {qaoa.get('approx_ratio')}"
        )

    # 7. Asignación óptima
    assignment = output["optimal_assignment"]
    if len(assignment) != n_a:
        errors.append(
            f"optimal_assignment tiene {len(assignment)} entradas, esperado {n_a}"
        )
    else:
        for entry in assignment:
            for key in ["user_id", "user_name", "route_id", "route_name", "score"]:
                if key not in entry:
                    errors.append(f"optimal_assignment entrada sin '{key}'")
                    break

    if errors:
        return False, errors
    return True, []


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    """Punto de entrada: ejecuta pipeline, exporta JSON, valida."""
    sync_s3 = "--sync-s3" in sys.argv

    # 1. Ejecutar pipeline
    results = run_pipeline()

    # 2. Construir JSON
    print("\n" + "─" * 60)
    print("EXPORTANDO RESULTADOS")
    print("─" * 60)

    output = build_json_output(results)

    # 3. Validar formato
    print("\n  Validando formato JSON...")
    is_valid, errors = validate_json(output)

    if not is_valid:
        print("  ✗ VALIDACIÓN FALLIDA:")
        for err in errors:
            print(f"    - {err}")
        sys.exit(1)

    print("  ✓ Formato válido")

    # 4. Guardar archivo
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    class NumpyEncoder(json.JSONEncoder):
        """Serializa tipos numpy a tipos nativos de Python."""

        def default(self, obj):
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)

    file_size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"  ✓ Guardado en: {OUTPUT_FILE}")
    print(f"    Tamaño: {file_size_kb:.1f} KB")

    # 5. Resumen
    print("\n" + "─" * 60)
    print("RESUMEN")
    print("─" * 60)
    print(f"  Pipeline:        {results['pipeline_time']:.2f} s")
    print(f"  Clásico:         score={output['classical_result']['best_score']}")
    print(f"  QAOA:            score={output['qaoa_result']['best_score']}")
    print(f"  Approx. ratio:   {output['qaoa_result']['approx_ratio']}")
    print(f"  Coinciden:       {'Sí' if output['qaoa_result']['solutions_match'] else 'No'}")
    print(f"\n  Asignación óptima:")
    for a in output["optimal_assignment"]:
        print(f"    {a['user_name']} → {a['route_name']} (score: {a['score']})")

    # 6. Sync a S3 (opcional)
    if sync_s3:
        print("\n" + "─" * 60)
        print("SINCRONIZANDO CON S3")
        print("─" * 60)
        import subprocess

        bucket = "traffic-rain-ai-646715757812"
        s3_key = "inference/final_results.json"
        cmd = [
            "aws", "s3", "cp",
            str(OUTPUT_FILE),
            f"s3://{bucket}/{s3_key}",
            "--region", "us-east-1",
        ]
        print(f"  $ {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✓ Sincronizado a s3://{bucket}/{s3_key}")
        else:
            print(f"  ✗ Error: {result.stderr.strip()}")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("COMPLETADO")
    print("=" * 60)


if __name__ == "__main__":
    main()
