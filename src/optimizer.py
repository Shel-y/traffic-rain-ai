"""
Módulo 4: Optimizador QAOA usando Amazon Braket Local Simulator.

Responsabilidad:
    Resolver el QUBO mediante el algoritmo QAOA ejecutado
    en el simulador local de Amazon Braket (cero costos).

Origen: Notebook 02 (secciones 11-16)
Implementación: Nueva (Amazon Braket SDK, equivalencia funcional)
"""

import time
from typing import Dict, Optional, Tuple

import numpy as np
from braket.circuits import Circuit
from braket.devices import LocalSimulator
from scipy.optimize import minimize


def _qubo_energy(bitstring: str, qubo_matrix: np.ndarray) -> float:
    """Calcula la energía E = x^T Q x para un bitstring."""
    x = np.array([int(b) for b in bitstring], dtype=float)
    return float(x @ qubo_matrix @ x)


def _build_qaoa_circuit(
    qubo_matrix: np.ndarray,
    gamma: float,
    beta: float,
    n_qubits: int,
    p: int = 1,
) -> Circuit:
    """
    Construye el circuito QAOA para p capas.

    Estructura por capa:
        1. U_C(gamma): fase de costo basada en el QUBO
        2. U_M(beta): mixer estándar (rotaciones RX)

    El operador de costo se implementa como:
        - Para términos diagonales Q[i,i]: rz(2*gamma*Q[i,i]) en qubit i
        - Para términos off-diagonal Q[i,j]: rzz(2*gamma*Q[i,j]) entre qubits i,j

    El mixer se implementa como:
        - rx(2*beta) en cada qubit

    Parámetros
    ----------
    qubo_matrix : np.ndarray
        Matriz QUBO (n_qubits x n_qubits), triangular superior.
    gamma : float
        Parámetro de la fase de costo.
    beta : float
        Parámetro del mixer.
    n_qubits : int
        Número de qubits (= n_a * n_b).
    p : int
        Profundidad (número de capas QAOA).
    """
    circuit = Circuit()

    # Estado inicial: superposición uniforme |+>^n
    for q in range(n_qubits):
        circuit.h(q)

    # Capas QAOA
    for _ in range(p):
        # ─── Operador de costo U_C(gamma) ────────────────────────────────
        # Términos diagonales: e^{-i * gamma * Q[i,i] * Z_i}
        # Dado que Z|0>=+1 y Z|1>=-1, y x_i = (1-Z_i)/2,
        # usamos la descomposición estándar QUBO → Ising.
        #
        # Para QUBO: E(x) = sum_i Q[i,i]*x_i + sum_{i<j} Q[i,j]*x_i*x_j
        # Mapeo x_i = (1-Z_i)/2:
        #   Q[i,i]*x_i -> Q[i,i]/2 * (I - Z_i)
        #   Q[i,j]*x_i*x_j -> Q[i,j]/4 * (I - Z_i - Z_j + Z_i*Z_j)
        #
        # Solo las partes con operadores Z contribuyen a la fase relativa.

        # Términos de un cuerpo (diagonal)
        for i in range(n_qubits):
            # Coeficiente del término Z_i en el Hamiltoniano Ising
            h_i = -qubo_matrix[i, i] / 2.0
            # Contribución de los términos off-diagonal a Z_i
            for j in range(n_qubits):
                if i != j:
                    q_ij = qubo_matrix[min(i, j), max(i, j)]
                    h_i -= q_ij / 4.0

            if abs(h_i) > 1e-12:
                circuit.rz(i, 2.0 * gamma * h_i)

        # Términos de dos cuerpos (off-diagonal): Z_i Z_j
        for i in range(n_qubits):
            for j in range(i + 1, n_qubits):
                j_ij = qubo_matrix[i, j] / 4.0
                if abs(j_ij) > 1e-12:
                    # RZZ(theta) = exp(-i * theta/2 * Z_i Z_j)
                    # Queremos exp(-i * gamma * j_ij * Z_i Z_j)
                    # Entonces theta = 2 * gamma * j_ij
                    circuit.zz(i, j, 2.0 * gamma * j_ij)

        # ─── Mixer U_M(beta) ────────────────────────────────────────────
        for q in range(n_qubits):
            circuit.rx(q, 2.0 * beta)

    return circuit


def _expected_energy_from_counts(
    counts: dict,
    qubo_matrix: np.ndarray,
    shots: int,
) -> float:
    """Calcula la energía esperada <E> a partir de los counts del muestreo."""
    energy = 0.0
    for bitstring, count in counts.items():
        energy += count * _qubo_energy(bitstring, qubo_matrix)
    return energy / shots


def solve_qaoa(
    qubo_matrix: np.ndarray,
    n_a: int,
    n_b: int,
    p: int = 1,
    shots: int = 2000,
    seed: int = 2026,
) -> Optional[Dict]:
    """
    Resuelve el QUBO mediante QAOA usando Amazon Braket Local Simulator.

    Parámetros
    ----------
    qubo_matrix : np.ndarray
        Matriz QUBO Q de shape (n_a*n_b, n_a*n_b).
    n_a : int
        Número de usuarios.
    n_b : int
        Número de rutas.
    p : int
        Profundidad del circuito QAOA.
    shots : int
        Número de mediciones.
    seed : int
        Semilla para reproducibilidad.

    Retorna
    -------
    dict con claves:
        - best_bitstring: str
        - best_energy: float
        - counts: dict {bitstring: count}
        - optimal_params: tuple (gamma*, beta*)
        - execution_time: float (segundos)
    """
    start_time = time.time()
    n_qubits = n_a * n_b
    rng = np.random.default_rng(seed)
    device = LocalSimulator()

    # ─── Función objetivo para el optimizador clásico ────────────────────────
    def objective(params: np.ndarray) -> float:
        gamma = params[0]
        beta = params[1]
        circuit = _build_qaoa_circuit(qubo_matrix, gamma, beta, n_qubits, p)
        task = device.run(circuit, shots=shots)
        result = task.result()
        counts = dict(result.measurement_counts)
        return _expected_energy_from_counts(counts, qubo_matrix, shots)

    # ─── Optimización con COBYLA (múltiples restarts) ────────────────────────
    n_restarts = 3
    best_result = None
    best_energy_opt = float("inf")

    for _ in range(n_restarts):
        # Parámetros iniciales aleatorios en [-π, π]
        x0 = rng.uniform(-np.pi, np.pi, size=2 * p)
        result = minimize(
            objective,
            x0,
            method="COBYLA",
            options={"maxiter": 50, "rhobeg": 0.5},
        )
        if result.fun < best_energy_opt:
            best_energy_opt = result.fun
            best_result = result

    # ─── Muestreo final con parámetros óptimos ──────────────────────────────
    optimal_params = best_result.x
    gamma_opt = optimal_params[0]
    beta_opt = optimal_params[1]

    final_circuit = _build_qaoa_circuit(
        qubo_matrix, gamma_opt, beta_opt, n_qubits, p
    )
    final_task = device.run(final_circuit, shots=shots)
    final_result = final_task.result()
    counts = dict(final_result.measurement_counts)

    # ─── Encontrar el mejor bitstring ────────────────────────────────────────
    best_bitstring = None
    best_energy = float("inf")

    for bitstring, count in counts.items():
        energy = _qubo_energy(bitstring, qubo_matrix)
        if energy < best_energy:
            best_energy = energy
            best_bitstring = bitstring

    execution_time = time.time() - start_time

    return {
        "best_bitstring": best_bitstring,
        "best_energy": best_energy,
        "counts": counts,
        "optimal_params": tuple(optimal_params),
        "execution_time": execution_time,
    }
