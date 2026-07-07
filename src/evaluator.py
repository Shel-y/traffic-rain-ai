"""
Módulo 6: Evaluación y comparación de resultados.

Responsabilidad:
    Comparar la solución clásica contra la solución QAOA,
    generar métricas y visualizaciones.

Origen: Notebook 02 (secciones 17-19)
Implementación: Nueva
"""

from pathlib import Path
from typing import Dict, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _decode_assignment(bitstring: str, n_a: int, n_b: int) -> list:
    """Decodifica un bitstring en una lista de asignaciones [(usuario, ruta), ...]."""
    assignments = []
    for i in range(n_a):
        for j in range(n_b):
            if bitstring[i * n_b + j] == "1":
                assignments.append((i, j))
    return assignments


def _is_feasible(bitstring: str, n_a: int, n_b: int) -> bool:
    """Verifica si un bitstring representa una asignación factible (permutación)."""
    x = np.array([int(b) for b in bitstring]).reshape(n_a, n_b)
    row_sums = x.sum(axis=1)
    col_sums = x.sum(axis=0)
    return bool(np.all(row_sums == 1) and np.all(col_sums == 1))


def _compute_score_from_bitstring(
    bitstring: str, score_matrix: np.ndarray, n_a: int, n_b: int
) -> float:
    """Calcula el score total de compatibilidad de un bitstring."""
    total = 0.0
    for i in range(n_a):
        for j in range(n_b):
            if bitstring[i * n_b + j] == "1":
                total += score_matrix[i, j]
    return total


def print_comparison(
    classical_result: Dict,
    qaoa_result: Optional[Dict],
    score_matrix: np.ndarray,
    score_df: pd.DataFrame,
    n_a: int = 4,
    n_b: int = 4,
) -> None:
    """Imprime una tabla comparativa de resultados clásico vs QAOA."""
    print("\n" + "=" * 60)
    print("COMPARACIÓN: CLÁSICO vs QAOA")
    print("=" * 60)

    # Resultados clásicos
    print("\n── Solución Clásica (exacta) ──")
    print(f"  Asignación óptima: {classical_result['best_assignment']}")
    print(f"  Bitstring:         {classical_result['best_bitstring']}")
    print(f"  Score total:       {classical_result['best_score']:.4f}")
    print(f"  Energía QUBO:      {classical_result['best_energy']:.4f}")
    print(f"  Tiempo:            {classical_result['execution_time']:.4f} s")
    print(f"  Húngaro coincide:  {classical_result['best_assignment'] == classical_result['hungarian_assignment']}")

    # Detalle de asignación
    assignments = _decode_assignment(classical_result["best_bitstring"], n_a, n_b)
    print("\n  Detalle:")
    for user_idx, route_idx in assignments:
        row = score_df[
            (score_df["a_id"] == f"U{user_idx+1}")
            & (score_df["b_id"] == f"R{route_idx+1}")
        ]
        if not row.empty:
            r = row.iloc[0]
            print(f"    {r['a_nombre']} → {r['b_nombre']} (score: {r['score']})")

    # Resultados QAOA (si disponibles)
    if qaoa_result is not None:
        print("\n── Solución QAOA ──")
        print(f"  Mejor bitstring:   {qaoa_result['best_bitstring']}")
        print(f"  Energía:           {qaoa_result['best_energy']:.4f}")
        print(f"  Factible:          {_is_feasible(qaoa_result['best_bitstring'], n_a, n_b)}")

        qaoa_score = _compute_score_from_bitstring(
            qaoa_result["best_bitstring"], score_matrix, n_a, n_b
        )
        print(f"  Score total:       {qaoa_score:.4f}")
        print(f"  Tiempo:            {qaoa_result['execution_time']:.4f} s")

        # Approximation ratio
        if classical_result["best_score"] > 0:
            approx_ratio = qaoa_score / classical_result["best_score"]
            print(f"  Approx. ratio:     {approx_ratio:.4f}")

        # ¿Coinciden?
        match = qaoa_result["best_bitstring"] == classical_result["best_bitstring"]
        print(f"\n  ¿Soluciones coinciden? {'Sí' if match else 'No'}")
    else:
        print("\n── Solución QAOA ──")
        print("  No disponible (módulo optimizer no ejecutado)")

    print("\n" + "=" * 60)


def plot_energy_comparison(
    classical_result: Dict,
    qaoa_result: Optional[Dict],
    figures_dir: Path,
    n_a: int = 4,
    n_b: int = 4,
) -> None:
    """
    Genera gráfica de barras comparando energías de todas las
    permutaciones factibles, marcando la solución clásica y QAOA.
    """
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Energías de todas las permutaciones factibles
    all_perms = classical_result["all_permutations"]
    energies = [p["energy"] for p in all_perms]
    scores = [p["score"] for p in all_perms]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Gráfica 1: Energías QUBO
    indices = range(len(energies))
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
    plt.savefig(figures_dir / "comparison_energies.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  Gráfica guardada: {figures_dir / 'comparison_energies.png'}")


def evaluate(
    classical_result: Dict,
    qaoa_result: Optional[Dict],
    score_matrix: np.ndarray,
    score_df: pd.DataFrame,
    figures_dir: Path,
    n_a: int = 4,
    n_b: int = 4,
) -> None:
    """
    Punto de entrada del evaluador.

    Parámetros
    ----------
    classical_result : dict
        Resultado de classical_solver.solve_classical().
    qaoa_result : dict o None
        Resultado de optimizer.solve_qaoa(). None si no se ejecutó.
    score_matrix : np.ndarray
        Matriz S de scores.
    score_df : pd.DataFrame
        DataFrame en formato largo con nombres.
    figures_dir : Path
        Directorio donde guardar gráficas.
    n_a : int
        Número de usuarios.
    n_b : int
        Número de rutas.
    """
    print_comparison(classical_result, qaoa_result, score_matrix, score_df, n_a, n_b)
    plot_energy_comparison(classical_result, qaoa_result, figures_dir, n_a, n_b)
