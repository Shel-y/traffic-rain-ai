"""
Módulo 5: Solver clásico para el problema de asignación.

Responsabilidad:
    Resolver el QUBO/asignación con métodos exactos clásicos
    para servir como benchmark de comparación contra QAOA.

Origen: Notebook 02 (secciones 9-10)
Implementación: Nueva (código limpio)
"""

import time
from itertools import permutations
from typing import Dict

import numpy as np
from scipy.optimize import linear_sum_assignment


def _bitstring_from_permutation(perm: tuple, n_a: int, n_b: int) -> str:
    """Convierte una permutación (asignación) en un bitstring de longitud n_a*n_b."""
    x = np.zeros(n_a * n_b, dtype=int)
    for i, j in enumerate(perm):
        x[i * n_b + j] = 1
    return "".join(map(str, x))


def _evaluate_bitstring(bitstring: str, qubo_matrix: np.ndarray) -> float:
    """Calcula la energía E = x^T Q x para un bitstring dado."""
    x = np.array([int(b) for b in bitstring], dtype=float)
    return float(x @ qubo_matrix @ x)


def _assignment_score(perm: tuple, score_matrix: np.ndarray) -> float:
    """Calcula el score total de una asignación (permutación)."""
    return sum(score_matrix[i, j] for i, j in enumerate(perm))


def solve_classical(
    score_matrix: np.ndarray,
    qubo_matrix: np.ndarray,
    n_a: int,
    n_b: int,
) -> Dict:
    """
    Resuelve el problema de asignación con métodos clásicos exactos.

    Métodos utilizados:
        1. Fuerza bruta sobre las 4! = 24 permutaciones factibles.
        2. Algoritmo húngaro (linear_sum_assignment) como verificación.

    Parámetros
    ----------
    score_matrix : np.ndarray
        Matriz S de shape (n_a, n_b).
    qubo_matrix : np.ndarray
        Matriz QUBO Q de shape (n_a*n_b, n_a*n_b).
    n_a : int
        Número de usuarios.
    n_b : int
        Número de rutas.

    Retorna
    -------
    dict con claves:
        - best_bitstring: str, bitstring óptimo
        - best_energy: float, energía mínima del QUBO
        - best_score: float, score máximo de la asignación
        - best_assignment: tuple, permutación óptima
        - all_permutations: list, todas las evaluaciones
        - hungarian_assignment: tuple, resultado del algoritmo húngaro
        - execution_time: float, tiempo en segundos
    """
    start_time = time.time()

    # ─── Método 1: Fuerza bruta sobre permutaciones factibles ────────────────
    all_results = []
    best_score = -float("inf")
    best_perm = None

    for perm in permutations(range(n_b)):
        bitstring = _bitstring_from_permutation(perm, n_a, n_b)
        energy = _evaluate_bitstring(bitstring, qubo_matrix)
        score = _assignment_score(perm, score_matrix)
        all_results.append({
            "permutation": perm,
            "bitstring": bitstring,
            "energy": energy,
            "score": score,
        })
        if score > best_score:
            best_score = score
            best_perm = perm

    best_bitstring = _bitstring_from_permutation(best_perm, n_a, n_b)
    best_energy = _evaluate_bitstring(best_bitstring, qubo_matrix)

    # ─── Método 2: Algoritmo húngaro (verificación) ──────────────────────────
    # linear_sum_assignment minimiza costos, así que pasamos -S
    row_ind, col_ind = linear_sum_assignment(-score_matrix)
    hungarian_assignment = tuple(col_ind)

    execution_time = time.time() - start_time

    return {
        "best_bitstring": best_bitstring,
        "best_energy": best_energy,
        "best_score": best_score,
        "best_assignment": best_perm,
        "all_permutations": all_results,
        "hungarian_assignment": hungarian_assignment,
        "execution_time": execution_time,
    }
