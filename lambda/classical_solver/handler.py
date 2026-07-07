"""
Lambda: classical_solver

Lee la matriz QUBO (NPZ) desde S3, resuelve el problema de asignación
con métodos clásicos exactos y escribe el resultado como JSON en S3.

Evento esperado:
{
    "bucket": "traffic-rain-ai-XXXX",
    "qubo_key": "qubo/qubo_matrix.npz",
    "output_key": "results/classical_result.json",
    "n_a": 4,
    "n_b": 4
}
"""

import io
import json
import time
from itertools import permutations

import boto3
import numpy as np
from scipy.optimize import linear_sum_assignment


s3 = boto3.client("s3")


def _bitstring_from_permutation(perm: tuple, n_a: int, n_b: int) -> str:
    """Convierte una permutación en un bitstring de longitud n_a*n_b."""
    x = np.zeros(n_a * n_b, dtype=int)
    for i, j in enumerate(perm):
        x[i * n_b + j] = 1
    return "".join(map(str, x))


def _evaluate_bitstring(bitstring: str, qubo_matrix: np.ndarray) -> float:
    """Calcula la energía E = x^T Q x para un bitstring."""
    x = np.array([int(b) for b in bitstring], dtype=float)
    return float(x @ qubo_matrix @ x)


def _assignment_score(perm: tuple, score_matrix: np.ndarray) -> float:
    """Calcula el score total de una asignación."""
    return sum(score_matrix[i, j] for i, j in enumerate(perm))


def solve_classical(
    score_matrix: np.ndarray,
    qubo_matrix: np.ndarray,
    n_a: int,
    n_b: int,
) -> dict:
    """Resuelve con fuerza bruta + algoritmo húngaro."""
    start_time = time.time()

    # Fuerza bruta sobre permutaciones factibles
    all_results = []
    best_score = -float("inf")
    best_perm = None

    for perm in permutations(range(n_b)):
        bitstring = _bitstring_from_permutation(perm, n_a, n_b)
        energy = _evaluate_bitstring(bitstring, qubo_matrix)
        score = _assignment_score(perm, score_matrix)
        all_results.append({
            "permutation": list(perm),
            "bitstring": bitstring,
            "energy": energy,
            "score": score,
        })
        if score > best_score:
            best_score = score
            best_perm = perm

    best_bitstring = _bitstring_from_permutation(best_perm, n_a, n_b)
    best_energy = _evaluate_bitstring(best_bitstring, qubo_matrix)

    # Algoritmo húngaro (verificación)
    row_ind, col_ind = linear_sum_assignment(-score_matrix)
    hungarian_assignment = list(col_ind)

    execution_time = time.time() - start_time

    return {
        "best_bitstring": best_bitstring,
        "best_energy": best_energy,
        "best_score": best_score,
        "best_assignment": list(best_perm),
        "all_permutations": all_results,
        "hungarian_assignment": hungarian_assignment,
        "execution_time": execution_time,
    }


def lambda_handler(event, context):
    """Punto de entrada de Lambda."""
    bucket = event["bucket"]
    qubo_key = event["qubo_key"]
    output_key = event["output_key"]
    n_a = event.get("n_a", 4)
    n_b = event.get("n_b", 4)

    # Leer NPZ desde S3
    response = s3.get_object(Bucket=bucket, Key=qubo_key)
    npz_body = response["Body"].read()
    npz_data = np.load(io.BytesIO(npz_body))

    qubo_matrix = npz_data["qubo_matrix"]
    score_matrix = npz_data["score_matrix"]

    # Resolver
    result = solve_classical(score_matrix, qubo_matrix, n_a, n_b)

    # Escribir JSON en S3
    s3.put_object(
        Bucket=bucket,
        Key=output_key,
        Body=json.dumps(result, indent=2).encode("utf-8"),
        ContentType="application/json",
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Solver clásico completo.",
            "output_key": output_key,
            "best_score": result["best_score"],
            "best_assignment": result["best_assignment"],
            "execution_time": result["execution_time"],
        }),
    }
