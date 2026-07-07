"""
Lambda: evaluator

Lee las matrices (NPZ), los resultados de solvers (JSON) desde S3,
genera métricas de comparación y una gráfica PNG que guarda en S3.

Evento esperado:
{
    "bucket": "traffic-rain-ai-XXXX",
    "qubo_key": "qubo/qubo_matrix.npz",
    "scores_key": "scores/dataset_real_4x4.csv",
    "classical_result_key": "results/classical_result.json",
    "qaoa_result_key": "results/qaoa_result.json",
    "figure_output_key": "figures/comparison_energies.png",
    "summary_output_key": "results/evaluation_summary.json",
    "n_a": 4,
    "n_b": 4
}

Nota: qaoa_result_key es opcional. Si no existe o es null,
la evaluación se realiza solo con el resultado clásico.
"""

import io
import json

import boto3
import matplotlib
matplotlib.use("Agg")  # Backend sin display para Lambda
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


s3 = boto3.client("s3")


def _is_feasible(bitstring: str, n_a: int, n_b: int) -> bool:
    """Verifica si un bitstring es una asignación factible."""
    x = np.array([int(b) for b in bitstring]).reshape(n_a, n_b)
    return bool(np.all(x.sum(axis=1) == 1) and np.all(x.sum(axis=0) == 1))


def _compute_score_from_bitstring(
    bitstring: str, score_matrix: np.ndarray, n_a: int, n_b: int
) -> float:
    """Calcula el score total de un bitstring."""
    total = 0.0
    for i in range(n_a):
        for j in range(n_b):
            if bitstring[i * n_b + j] == "1":
                total += score_matrix[i, j]
    return total


def _generate_comparison_figure(
    classical_result: dict,
    qaoa_result: dict,
) -> bytes:
    """Genera gráfica PNG como bytes en memoria."""
    all_perms = classical_result["all_permutations"]
    energies = [p["energy"] for p in all_perms]
    scores = [p["score"] for p in all_perms]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    indices = range(len(energies))

    # Gráfica 1: Energías QUBO
    ax1.bar(indices, energies, color="steelblue", alpha=0.7)
    ax1.axhline(
        y=classical_result["best_energy"],
        color="green",
        linestyle="--",
        label=f"Óptimo clásico: {classical_result['best_energy']:.2f}",
    )
    if qaoa_result is not None:
        ax1.axhline(
            y=qaoa_result["best_energy"],
            color="red",
            linestyle="--",
            label=f"QAOA: {qaoa_result['best_energy']:.2f}",
        )
    ax1.set_xlabel("Permutación")
    ax1.set_ylabel("Energía QUBO")
    ax1.set_title("Energías de asignaciones factibles")
    ax1.legend()

    # Gráfica 2: Scores
    ax2.bar(indices, scores, color="coral", alpha=0.7)
    ax2.axhline(
        y=classical_result["best_score"],
        color="green",
        linestyle="--",
        label=f"Óptimo clásico: {classical_result['best_score']:.2f}",
    )
    ax2.set_xlabel("Permutación")
    ax2.set_ylabel("Score total")
    ax2.set_title("Scores de asignaciones factibles")
    ax2.legend()

    plt.tight_layout()

    # Renderizar a bytes PNG
    png_buffer = io.BytesIO()
    plt.savefig(png_buffer, format="png", dpi=150, bbox_inches="tight")
    plt.close()
    png_buffer.seek(0)
    return png_buffer.getvalue()


def _build_summary(
    classical_result: dict,
    qaoa_result: dict,
    score_matrix: np.ndarray,
    score_df: pd.DataFrame,
    n_a: int,
    n_b: int,
) -> dict:
    """Construye un resumen JSON con todas las métricas."""
    summary = {
        "classical": {
            "best_bitstring": classical_result["best_bitstring"],
            "best_energy": classical_result["best_energy"],
            "best_score": classical_result["best_score"],
            "best_assignment": classical_result["best_assignment"],
            "hungarian_matches": classical_result["best_assignment"] == classical_result["hungarian_assignment"],
            "execution_time_s": classical_result["execution_time"],
        },
        "qaoa": None,
        "comparison": None,
    }

    # Detalle de asignación legible
    assignment_detail = []
    bitstring = classical_result["best_bitstring"]
    for i in range(n_a):
        for j in range(n_b):
            if bitstring[i * n_b + j] == "1":
                row = score_df[
                    (score_df["a_id"] == f"U{i+1}")
                    & (score_df["b_id"] == f"R{j+1}")
                ]
                if not row.empty:
                    r = row.iloc[0]
                    assignment_detail.append({
                        "usuario": r["a_nombre"],
                        "ruta": r["b_nombre"],
                        "score": float(r["score"]),
                    })
    summary["classical"]["assignment_detail"] = assignment_detail

    # QAOA (si disponible)
    if qaoa_result is not None:
        qaoa_score = _compute_score_from_bitstring(
            qaoa_result["best_bitstring"], score_matrix, n_a, n_b
        )
        feasible = _is_feasible(qaoa_result["best_bitstring"], n_a, n_b)
        approx_ratio = qaoa_score / classical_result["best_score"] if classical_result["best_score"] > 0 else 0.0
        match = qaoa_result["best_bitstring"] == classical_result["best_bitstring"]

        summary["qaoa"] = {
            "best_bitstring": qaoa_result["best_bitstring"],
            "best_energy": qaoa_result["best_energy"],
            "score": qaoa_score,
            "feasible": feasible,
            "execution_time_s": qaoa_result["execution_time"],
        }
        summary["comparison"] = {
            "solutions_match": match,
            "approximation_ratio": approx_ratio,
            "energy_gap": qaoa_result["best_energy"] - classical_result["best_energy"],
        }

    return summary


def _safe_get_json(bucket: str, key: str) -> dict:
    """Lee un JSON desde S3. Retorna None si no existe."""
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        return json.loads(response["Body"].read())
    except s3.exceptions.NoSuchKey:
        return None
    except Exception:
        return None


def lambda_handler(event, context):
    """Punto de entrada de Lambda."""
    bucket = event["bucket"]
    qubo_key = event["qubo_key"]
    scores_key = event["scores_key"]
    classical_result_key = event["classical_result_key"]
    qaoa_result_key = event.get("qaoa_result_key")
    figure_output_key = event["figure_output_key"]
    summary_output_key = event["summary_output_key"]
    n_a = event.get("n_a", 4)
    n_b = event.get("n_b", 4)

    # Leer matrices desde S3
    response = s3.get_object(Bucket=bucket, Key=qubo_key)
    npz_data = np.load(io.BytesIO(response["Body"].read()))
    score_matrix = npz_data["score_matrix"]

    # Leer scores CSV para nombres legibles
    response = s3.get_object(Bucket=bucket, Key=scores_key)
    score_df = pd.read_csv(io.BytesIO(response["Body"].read()))

    # Leer resultado clásico
    classical_result = _safe_get_json(bucket, classical_result_key)
    if classical_result is None:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "classical_result no encontrado en S3."}),
        }

    # Leer resultado QAOA (opcional)
    qaoa_result = None
    if qaoa_result_key:
        qaoa_result = _safe_get_json(bucket, qaoa_result_key)

    # Generar gráfica
    png_bytes = _generate_comparison_figure(classical_result, qaoa_result)
    s3.put_object(
        Bucket=bucket,
        Key=figure_output_key,
        Body=png_bytes,
        ContentType="image/png",
    )

    # Generar resumen
    summary = _build_summary(
        classical_result, qaoa_result, score_matrix, score_df, n_a, n_b
    )
    s3.put_object(
        Bucket=bucket,
        Key=summary_output_key,
        Body=json.dumps(summary, indent=2, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Evaluación completa.",
            "figure_key": figure_output_key,
            "summary_key": summary_output_key,
            "solutions_match": summary.get("comparison", {}).get("solutions_match") if summary.get("comparison") else None,
        }),
    }
