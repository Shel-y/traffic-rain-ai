"""
Lambda: qubo_builder

Lee la matriz de scores desde S3, construye la formulación QUBO
y escribe la matriz Q serializada en S3.

Evento esperado:
{
    "bucket": "traffic-rain-ai-XXXX",
    "scores_key": "scores/dataset_real_4x4.csv",
    "output_key": "qubo/qubo_matrix.npz",
    "n_a": 4,
    "n_b": 4,
    "lambda_penalty": null
}
"""

import io
import json

import boto3
import numpy as np
import pandas as pd


s3 = boto3.client("s3")


def build_qubo(
    score_matrix: np.ndarray,
    n_a: int,
    n_b: int,
    lambda_penalty: float = None,
) -> tuple:
    """Lógica de construcción QUBO (equivalente a src/qubo_builder.py)."""
    assert score_matrix.shape == (n_a, n_b)

    n_vars = n_a * n_b

    if lambda_penalty is None:
        lambda_value = float(score_matrix.max()) + 1.0
    else:
        lambda_value = float(lambda_penalty)

    Q = np.zeros((n_vars, n_vars))

    def idx(i, j):
        return i * n_b + j

    # Término objetivo
    for i in range(n_a):
        for j in range(n_b):
            Q[idx(i, j), idx(i, j)] += -score_matrix[i, j]

    # Restricción de filas
    for i in range(n_a):
        for j in range(n_b):
            Q[idx(i, j), idx(i, j)] += -lambda_value
            for k in range(j + 1, n_b):
                Q[idx(i, j), idx(i, k)] += 2.0 * lambda_value

    # Restricción de columnas
    for j in range(n_b):
        for i in range(n_a):
            Q[idx(i, j), idx(i, j)] += -lambda_value
            for k in range(i + 1, n_a):
                Q[idx(i, j), idx(k, j)] += 2.0 * lambda_value

    return Q, lambda_value


def lambda_handler(event, context):
    """Punto de entrada de Lambda."""
    bucket = event["bucket"]
    scores_key = event["scores_key"]
    output_key = event["output_key"]
    n_a = event.get("n_a", 4)
    n_b = event.get("n_b", 4)
    lambda_penalty = event.get("lambda_penalty", None)

    # Leer scores CSV desde S3
    response = s3.get_object(Bucket=bucket, Key=scores_key)
    csv_body = response["Body"].read()
    score_df = pd.read_csv(io.BytesIO(csv_body))

    # Pivotear a matriz
    score_matrix = score_df.pivot(
        index="a_id", columns="b_id", values="score"
    ).values.astype(float)

    # Construir QUBO
    Q, lambda_value = build_qubo(score_matrix, n_a, n_b, lambda_penalty)

    # Serializar y escribir en S3
    npz_buffer = io.BytesIO()
    np.savez_compressed(
        npz_buffer,
        qubo_matrix=Q,
        score_matrix=score_matrix,
        lambda_value=np.array([lambda_value]),
    )
    npz_buffer.seek(0)

    s3.put_object(
        Bucket=bucket,
        Key=output_key,
        Body=npz_buffer.getvalue(),
        ContentType="application/octet-stream",
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "QUBO construido.",
            "output_key": output_key,
            "lambda_value": lambda_value,
            "qubo_shape": list(Q.shape),
        }),
    }
