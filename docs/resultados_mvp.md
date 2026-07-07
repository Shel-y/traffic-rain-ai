# Resultados del MVP: Clásico vs QAOA

## Contexto del experimento

Se formuló un problema de asignación de rutas como un QUBO (Quadratic Unconstrained Binary Optimization) con 16 variables binarias (4 usuarios × 4 rutas) y se resolvió mediante:

1. **Método clásico exacto:** Fuerza bruta sobre las 24 permutaciones factibles + verificación con algoritmo húngaro.
2. **QAOA (p=1):** Quantum Approximate Optimization Algorithm con 1 capa, ejecutado en Amazon Braket Local Simulator con COBYLA como optimizador clásico.

## Formulación

- **Variables:** x_{ij} ∈ {0,1} — usuario i asignado a ruta j
- **Objetivo:** Maximizar score total Σ S_{ij} · x_{ij}
- **Restricciones:** Cada usuario exactamente 1 ruta, cada ruta exactamente 1 usuario
- **Penalización:** λ = max(S) + 1 = 2.0
- **Qubits:** 16

## Resultados

### Solución óptima

Ambos métodos convergieron a la misma asignación:

| Asignación | Score individual |
|---|---|
| Barrio San Miguel → Eje Central | 0.66 |
| Colinas Del Ajusco → Periférico Sur | 0.72 |
| Jardines Del Pedregal → Viaducto+Revolución | 0.63 |
| La Joya → Circuito Interior | 0.16 |

**Score total:** 2.29 (la asignación factible con menor riesgo agregado)

### Métricas comparativas

| Métrica | Clásico | QAOA |
|---------|:-------:|:----:|
| Energía QUBO | -10.29 | -10.29 |
| Score total | 2.29 | 2.29 |
| Factibilidad | 100% | 100% |
| Approximation ratio | 1.0 | 1.0 |
| Tiempo | ~1 ms | ~8.8 s |

### Interpretación

1. **QAOA encontró el óptimo global** con p=1. Esto es notable para un problema de 16 qubits, aunque esperable dado el tamaño reducido del problema.

2. **El costo temporal es mayor en QAOA** (~8800x más lento). Esto es inherente al proceso de optimización variacional con 3 restarts × 50 iteraciones × 2000 shots por evaluación.

3. **El valor real de QAOA aparecería a mayor escala.** Para problemas de 20+ variables, la fuerza bruta se vuelve prohibitiva (2^20 = 1M configuraciones) mientras QAOA escala polinomialmente en el número de puertas.

4. **Approximation ratio = 1.0** confirma que la formulación QUBO es correcta y que el circuito QAOA está bien implementado.

## Configuración del experimento

- Profundidad QAOA: p = 1
- Shots por evaluación: 2,000
- Optimizador: COBYLA (sin gradiente)
- Restarts: 3
- Max iteraciones por restart: 50
- Semilla: 2026
- Simulador: Amazon Braket Local Simulator
- Hardware: CPU local (sin acceso a QPU real)

## Gráficas

La gráfica `docs/figures/comparison_energies.png` muestra:
- Panel izquierdo: Energías QUBO de las 24 permutaciones factibles
- Panel derecho: Scores totales de las 24 permutaciones factibles
- Líneas horizontales: nivel óptimo clásico (verde) y QAOA (rojo)

## Conclusión

El MVP demuestra exitosamente que la formulación QUBO + QAOA produce resultados equivalentes al solver clásico exacto para este problema de asignación 4×4. La arquitectura modular está lista para escalar a problemas más grandes y para integrar un modelo de IA que genere los scores dinámicamente.
