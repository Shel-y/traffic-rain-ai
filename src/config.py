"""
Configuración centralizada del proyecto Traffic Rain Risk Optimizer.

Todos los parámetros del pipeline se definen aquí.
Los módulos reciben estos valores como argumentos, no los importan directamente.
"""

from pathlib import Path

# ─── Rutas de archivos ───────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

RAW_CSV_FILENAME = "reportes_agua_2024_01(1).csv"
PROCESSED_CSV_FILENAME = "dataset_real_4x4(2).csv"

RAW_CSV_PATH = DATA_RAW_DIR / RAW_CSV_FILENAME
PROCESSED_CSV_PATH = DATA_PROCESSED_DIR / PROCESSED_CSV_FILENAME

# ─── Parámetros de data_loader ───────────────────────────────────────────────

REPORTE_FILTER = "encharcamiento"
COORDINATE_DECIMALS = 3  # redondeo de lat/lon (~111 metros de precisión)

# ─── Parámetros de risk_scoring ──────────────────────────────────────────────

N_TOP_CRITICAL_POINTS = 4  # número de usuarios (puntos más frecuentes)

RUTAS_WAYPOINTS = {
    "R1": [  # Viaducto + Av. Revolución
        (-99.180, 19.400),
        (-99.178, 19.398),
        (-99.175, 19.395),
        (-99.172, 19.402),
        (-99.170, 19.410),
    ],
    "R2": [  # Circuito Interior
        (-99.150, 19.450),
        (-99.145, 19.440),
        (-99.140, 19.430),
        (-99.137, 19.425),
        (-99.135, 19.420),
    ],
    "R3": [  # Periférico Sur + Eje 10
        (-99.200, 19.360),
        (-99.195, 19.355),
        (-99.190, 19.350),
        (-99.185, 19.345),
        (-99.180, 19.340),
    ],
    "R4": [  # Eje Central + Reforma
        (-99.140, 19.430),
        (-99.137, 19.428),
        (-99.135, 19.425),
        (-99.132, 19.420),
        (-99.130, 19.415),
    ],
}

RUTAS_NOMBRES = {
    "R1": "Viaducto+Revolución",
    "R2": "Circuito Interior",
    "R3": "Periférico Sur",
    "R4": "Eje Central",
}

# ─── Parámetros de QUBO ─────────────────────────────────────────────────────

N_A = 4  # número de usuarios
N_B = 4  # número de rutas
LAMBDA_PENALTY = None  # None = calcular automáticamente como max(S) + 1

# ─── Parámetros de QAOA ─────────────────────────────────────────────────────

QAOA_P = 1          # profundidad del circuito
QAOA_SHOTS = 2000   # número de mediciones
QAOA_SEED = 2026    # semilla para reproducibilidad

# ─── Parámetros de evaluación ────────────────────────────────────────────────

FIGURES_DIR = PROJECT_ROOT / "docs" / "figures"
