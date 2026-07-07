"""
Módulo 3: Construcción de la formulación QUBO.

Responsabilidad:
    Transformar la matriz de scores S en una matriz QUBO Q
    que codifica el problema de asignación con restricciones de unicidad.

Origen: Notebook 02 (secciones 4-6)
Implementación: Nueva (código limpio, equivalencia funcional)
"""

from typing import Optional, Tuple

import numpy as np


def build_qubo(
    score_matrix: np.ndarray,
    n_a: int,
    n_b: int,
    lambda_penalty: Optional[float] = None,
) -> Tuple[np.ndarray, float]:
    """
    Construye la matriz QUBO para el problema de asignación.

    El QUBO minimiza:
        E(x) = -sum_{i,j} S_{ij} * x_{ij}
             + λ * sum_i (sum_j x_{ij} - 1)^2
             + λ * sum_j (sum_i x_{ij} - 1)^2

    Donde x_{ij} = 1 si usuario i es asignado a ruta j.

    Parámetros
    ----------
    score_matrix : np.ndarray
        Matriz S de shape (n_a, n_b) con scores de compatibilidad.
    n_a : int
        Número de usuarios.
    n_b : int
        Número de rutas.
    lambda_penalty : float o None
        Penalización para restricciones. Si None, se calcula como max(S) + 1.

    Retorna
    -------
    Q : np.ndarray
        Matriz QUBO de shape (n_a*n_b, n_a*n_b).
    lambda_value : float
        Valor de λ utilizado.
    """
    assert score_matrix.shape == (n_a, n_b), (
        f"score_matrix debe ser ({n_a}, {n_b}), recibido {score_matrix.shape}"
    )

    n_vars = n_a * n_b

    # Calcular λ
    if lambda_penalty is None:
        lambda_value = float(score_matrix.max()) + 1.0
    else:
        lambda_value = float(lambda_penalty)

    Q = np.zeros((n_vars, n_vars))

    # Función auxiliar: índice lineal de la variable x_{i,j}
    def idx(i: int, j: int) -> int:
        return i * n_b + j

    # ─── Término objetivo: -S_{ij} en la diagonal ────────────────────────────
    for i in range(n_a):
        for j in range(n_b):
            Q[idx(i, j), idx(i, j)] += -score_matrix[i, j]

    # ─── Restricción de filas: cada usuario asignado a exactamente 1 ruta ────
    # λ * sum_i (sum_j x_{ij} - 1)^2
    # Expandiendo: λ * (sum_j x_{ij})^2 - 2λ * sum_j x_{ij} + λ
    # = λ * sum_{j,k} x_{ij}*x_{ik} - 2λ * sum_j x_{ij} + λ (constante)
    for i in range(n_a):
        for j in range(n_b):
            # Término diagonal: λ * x_{ij}^2 - 2λ * x_{ij} = λ(1-2) * x_{ij} = -λ
            Q[idx(i, j), idx(i, j)] += -lambda_value
            for k in range(j + 1, n_b):
                # Término cruzado: 2λ * x_{ij} * x_{ik}
                Q[idx(i, j), idx(i, k)] += 2.0 * lambda_value

    # ─── Restricción de columnas: cada ruta asignada a exactamente 1 usuario ─
    # λ * sum_j (sum_i x_{ij} - 1)^2
    for j in range(n_b):
        for i in range(n_a):
            Q[idx(i, j), idx(i, j)] += -lambda_value
            for k in range(i + 1, n_a):
                Q[idx(i, j), idx(k, j)] += 2.0 * lambda_value

    return Q, lambda_value
