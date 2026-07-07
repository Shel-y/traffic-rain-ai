# PROJECT_PLAN.md

# Traffic Rain Risk Optimizer

## Estado del proyecto

**Versión:** 0.1 (MVP)

**Estado:** En desarrollo

**Objetivo principal:**
Construir un sistema inteligente que recomiende rutas con menor riesgo durante eventos de lluvia utilizando un modelo de Inteligencia Artificial para estimar riesgo y un algoritmo de Optimización Cuántica para seleccionar la mejor asignación de rutas.

---

# Visión

En muchas ciudades de Latinoamérica las aplicaciones de navegación optimizan principalmente tiempo o distancia.

Durante lluvias intensas esto deja de ser suficiente.

Una ruta aparentemente rápida puede atravesar calles inundadas, incrementar significativamente el tiempo de viaje o incluso representar un riesgo para conductores y peatones.

Este proyecto busca demostrar cómo combinar Inteligencia Artificial y Computación Cuántica para tomar decisiones más inteligentes considerando múltiples variables de riesgo.

Actualmente el proyecto es un prototipo de investigación, pero la arquitectura está pensada para escalar a escenarios reales.

---

# Problema

Dado un conjunto de usuarios que necesitan desplazarse durante una tormenta:

- existen múltiples rutas posibles
- cada ruta posee un nivel distinto de riesgo
- el riesgo depende de lluvia, historial de inundaciones y ubicación

El objetivo es minimizar el riesgo total de las asignaciones.

---

# Objetivos del MVP

El MVP debe ser completamente funcional utilizando únicamente herramientas gratuitas o dentro del AWS Free Tier.

Debe demostrar:

- carga de datos abiertos
- entrenamiento de un modelo sencillo de IA
- generación de una matriz de riesgo
- resolución mediante QUBO
- optimización mediante QAOA
- comparación contra algoritmo clásico
- visualización básica de resultados

No se busca construir todavía una aplicación comercial.

---

# Objetivos NO incluidos en el MVP

No desarrollar:

- aplicación móvil
- aplicación web
- autenticación
- cuentas de usuario
- tiempo real
- streaming
- mapas interactivos
- múltiples ciudades
- hardware cuántico real
- despliegue productivo

Todo esto podrá evaluarse posteriormente.

---

# Arquitectura objetivo

```
DDatos abiertos SACMEX
        │
        ▼
Pipeline de procesamiento de datos
        │
        ▼
Dataset de trabajo
        │
        ├─────────────► Modelo IA
        │                    │
        │                    ▼
        │             Predicción de riesgo
        │                    │
        └─────────────► Generación de matriz de riesgo
                             │
                             ▼
                        QUBO + QAOA
                             │
                             ▼
                    Amazon Braket Local Simulator
```

---

# Módulos

## Módulo 1

Obtención de datos

Responsabilidades:

- cargar datasets
- limpieza
- validación

Entrada:

Datos abiertos CDMX

Salida:

Dataset limpio

Estado:

Pendiente

---

## Módulo 2

Modelo IA

Responsabilidades:

- entrenamiento
- predicción de riesgo

Entrada:

Dataset limpio

Salida:

Probabilidad de riesgo

Tecnología:

Amazon SageMaker

Estado:

Pendiente

---

## Módulo 3

Generador de matriz de riesgo

Responsabilidades:

Transformar las probabilidades del modelo en una matriz de costos o compatibilidad.

Entrada:

Predicciones

Salida:

Matriz 4×4

Estado:

Pendiente

---

## Módulo 4

Optimización Cuántica

Responsabilidades:

Resolver el problema mediante:

- formulación QUBO
- algoritmo QAOA
- Amazon Braket Local Simulator

Tecnología:

Amazon Braket SDK

Amazon Braket Local Simulator

Estado actual:

Existe un notebook funcional desarrollado durante el proyecto QMexico Summer School.

Ese notebook representa la referencia matemática y funcional del proyecto.

Debe utilizarse para comprender:

- la formulación del problema
- la construcción del QUBO
- las restricciones
- la validación clásica
- los resultados esperados

La implementación final NO consistirá en reutilizar el notebook.

El objetivo es desarrollar una implementación limpia, modular y mantenible utilizando Amazon Braket Local Simulator, manteniendo equivalencia funcional con el notebook.
---

## Módulo 5

Evaluación

Comparar:

- solución clásica
- solución QAOA

Métricas:

- score
- energía
- factibilidad
- tiempo de ejecución

Estado:

Pendiente

---

# Roadmap

## Fase 1

Análisis del notebook existente

Objetivo:

Comprender completamente el proyecto QUBO/QAOA.

Entregable:

Documento técnico.

---

## Fase 2

Preparación de datos

Objetivo:

Construir pipeline de limpieza.

Entregable:

Dataset procesado.

---

## Fase 3

Modelo IA

Objetivo:

Entrenar un modelo sencillo que estime riesgo.

Entregable:

Modelo funcional.

---

## Fase 4

Integración IA + QUBO

Objetivo:

Generar automáticamente la matriz de riesgo.

Entregable:

Matriz compatible con el notebook cuántico.

---

## Fase 5

Integración con Amazon Braket

Objetivo:

Ejecutar el problema mediante Local Simulator.

Entregable:

Notebook actualizado.

---

## Fase 6

Comparación

Objetivo:

Comparar:

- clásico
- cuántico

Generar gráficas.

---

## Fase 7

Documentación

Actualizar:

- README
- arquitectura
- resultados
- diagramas

---

# Restricciones

Este proyecto debe mantenerse:

- reproducible
- modular
- fácil de entender
- con costo mínimo

No deben agregarse tecnologías nuevas sin aprobación.

---

# Restricciones AWS

Prioridad:

1. ejecución local

2. Free Tier

3. simuladores

4. servicios administrados únicamente cuando sean necesarios

No crear infraestructura automáticamente.

No desplegar recursos sin autorización.

---

# Criterios de aceptación

Cada fase debe cumplir:

- código documentado
- sin errores
- reproducible
- dependencias justificadas
- costo documentado
- instrucciones de ejecución

---

# Riesgos identificados

- crecimiento del alcance
- dependencia de servicios de pago
- datasets incompletos
- cambios de arquitectura sin aprobación
- sobreingeniería

Cada cambio debe justificar que reduce alguno de estos riesgos.

---

# Definición de éxito

El proyecto será exitoso cuando pueda:

1. Cargar datos abiertos.

2. Entrenar un modelo sencillo de riesgo.

3. Generar automáticamente la matriz de riesgo.

4. Ejecutar QAOA sobre dicha matriz.

5. Comparar contra un algoritmo clásico.

6. Mostrar claramente las diferencias entre ambos enfoques.

7. Poder reproducirse completamente siguiendo únicamente la documentación del repositorio.
