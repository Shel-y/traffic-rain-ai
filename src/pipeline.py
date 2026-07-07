"""
Orquestador principal del pipeline Traffic Rain Risk Optimizer.

Conecta los módulos en secuencia, pasando datos entre ellos.
No contiene lógica de negocio.

Uso:
    python -m src.pipeline
"""

from src import config


def run_pipeline():
    """Ejecuta el pipeline completo: datos → scoring → QUBO → solvers → evaluación."""

    # ─── Paso 1: Cargar y filtrar datos ──────────────────────────────────────
    from src.data_loader import load_and_filter

    df_encharcamientos = load_and_filter(
        csv_path=config.RAW_CSV_PATH,
        reporte_filter=config.REPORTE_FILTER,
        coordinate_decimals=config.COORDINATE_DECIMALS,
    )

    # ─── Paso 2: Generar matriz de scores ────────────────────────────────────
    from src.risk_scoring import generate_score_matrix

    score_df, score_matrix = generate_score_matrix(
        df_encharcamientos=df_encharcamientos,
        rutas_waypoints=config.RUTAS_WAYPOINTS,
        rutas_nombres=config.RUTAS_NOMBRES,
        n_top=config.N_TOP_CRITICAL_POINTS,
    )

    # ─── Paso 3: Construir QUBO ──────────────────────────────────────────────
    from src.qubo_builder import build_qubo

    qubo_matrix, lambda_value = build_qubo(
        score_matrix=score_matrix,
        n_a=config.N_A,
        n_b=config.N_B,
        lambda_penalty=config.LAMBDA_PENALTY,
    )

    # ─── Paso 4: Resolver clásicamente ───────────────────────────────────────
    from src.classical_solver import solve_classical

    classical_result = solve_classical(
        score_matrix=score_matrix,
        qubo_matrix=qubo_matrix,
        n_a=config.N_A,
        n_b=config.N_B,
    )

    # ─── Paso 5: Resolver con QAOA (Amazon Braket) ───────────────────────────
    from src.optimizer import solve_qaoa

    qaoa_result = solve_qaoa(
        qubo_matrix=qubo_matrix,
        n_a=config.N_A,
        n_b=config.N_B,
        p=config.QAOA_P,
        shots=config.QAOA_SHOTS,
        seed=config.QAOA_SEED,
    )

    # ─── Paso 6: Evaluar y comparar ─────────────────────────────────────────
    from src.evaluator import evaluate

    evaluate(
        classical_result=classical_result,
        qaoa_result=qaoa_result,
        score_matrix=score_matrix,
        score_df=score_df,
        figures_dir=config.FIGURES_DIR,
    )


if __name__ == "__main__":
    run_pipeline()
