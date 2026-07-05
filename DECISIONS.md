# DECISIONS.md

# Architecture Decision Records (ADR)

Este documento registra las decisiones importantes del proyecto.

Su objetivo es evitar reconsiderar continuamente decisiones ya tomadas y proporcionar contexto a cualquier persona o agente que trabaje en el proyecto.

---

# Estados posibles

- Proposed
- Approved
- Rejected
- Deprecated

---

# ADR-001

## Título

El proyecto se desarrollará de forma incremental.

**Estado**

Approved

**Fecha**

2026-07-05

### Contexto

El proyecto combina IA, optimización combinatoria y computación cuántica.

Intentar construir todo simultáneamente aumenta significativamente la complejidad.

### Decisión

El desarrollo se dividirá en fases pequeñas.

Cada fase deberá aprobarse antes de comenzar la siguiente.

### Consecuencias

Positivas

- Menor riesgo.
- Código más estable.
- Mejor documentación.

Negativas

- Desarrollo ligeramente más lento.

---

# ADR-002

## Título

Mantener el proyecto dentro del AWS Free Tier.

**Estado**

Approved

### Contexto

El proyecto es educativo y de investigación.

No debe generar costos inesperados.

### Decisión

Siempre deberá preferirse:

- ejecución local
- simuladores
- software open source
- Free Tier

Antes de utilizar un servicio que pueda generar costos, deberá solicitarse aprobación.

### Consecuencias

Positivas

- Riesgo financiero mínimo.

Negativas

- Algunas funcionalidades avanzadas podrían posponerse.

---

# ADR-003

## Título

El notebook QUBO/QAOA existente será reutilizado.

**Estado**

Approved

### Contexto

Ya existe una implementación funcional del algoritmo cuántico.

### Decisión

El notebook existente será el punto de partida del módulo cuántico.

No deberá reescribirse completamente.

Solo podrán realizarse modificaciones pequeñas y justificadas.

### Consecuencias

Positivas

- Aprovechamiento del trabajo existente.
- Menor riesgo.

Negativas

- Algunas decisiones del notebook deberán respetarse.

---

# ADR-004

## Título

No agregar servicios AWS sin aprobación.

**Estado**

Approved

### Contexto

Muchos asistentes agregan automáticamente servicios AWS que incrementan la complejidad y el costo.

### Decisión

Antes de incorporar cualquier servicio AWS deberán presentarse:

- motivo
- costo
- alternativas
- impacto

Después deberá esperarse aprobación.

### Consecuencias

Positivas

- Arquitectura controlada.
- Sin crecimiento innecesario.

---

# ADR-005

## Título

No instalar dependencias sin autorización.

**Estado**

Approved

### Contexto

Cada dependencia aumenta el mantenimiento del proyecto.

### Decisión

Antes de instalar una librería nueva deberá responderse:

- ¿Para qué sirve?
- ¿Existe alternativa con la librería estándar?
- ¿Tiene licencia compatible?
- ¿Tiene costo?

Después deberá esperarse aprobación.

### Consecuencias

Positivas

- Proyecto más limpio.
- Menor deuda técnica.

---

# ADR-006

## Título

Primero construir el MVP.

**Estado**

Approved

### Contexto

La visión del proyecto es mucho mayor que la primera versión.

### Decisión

El MVP solamente incluirá:

- carga de datos
- entrenamiento de IA
- matriz de riesgo
- QUBO
- QAOA
- comparación clásica
- visualización

No incluirá:

- aplicación web
- aplicación móvil
- usuarios
- autenticación
- despliegue

### Consecuencias

Positivas

- Objetivos claros.
- Menor complejidad.

---

# ADR-007

## Título

Priorizar datos abiertos.

**Estado**

Approved

### Contexto

El proyecto busca ser reproducible por cualquier persona.

### Decisión

Siempre se preferirán datasets públicos.

Antes de utilizar datos privados deberá justificarse.

### Consecuencias

Positivas

- Reproducibilidad.
- Transparencia.

---

# ADR-008

## Título

Comparar siempre con un algoritmo clásico.

**Estado**

Approved

### Contexto

El objetivo es evaluar el valor agregado de la optimización cuántica.

### Decisión

Toda mejora obtenida mediante QAOA deberá compararse contra un método clásico equivalente.

### Consecuencias

Positivas

- Resultados más sólidos.
- Mayor rigor científico.

---

# ADR-009

## Título

No modificar la arquitectura sin autorización.

**Estado**

Approved

### Contexto

La arquitectura evoluciona gradualmente.

### Decisión

Antes de cambiar módulos, flujo de datos o componentes deberá presentarse una propuesta técnica y esperar aprobación.

### Consecuencias

Positivas

- Arquitectura consistente.

---

# ADR-010

## Título

Toda propuesta debe incluir análisis de costo.

**Estado**

Approved

### Contexto

El costo es un criterio importante del proyecto.

### Decisión

Cada propuesta deberá incluir:

- Beneficios
- Riesgos
- Costo aproximado
- Impacto en Free Tier
- Alternativas gratuitas

Antes de implementarse.

### Consecuencias

Positivas

- Decisiones mejor fundamentadas.

---

# Plantilla para nuevas decisiones

---

# ADR-XXX

## Título

...

**Estado**

Proposed

**Fecha**

AAAA-MM-DD

### Contexto

...

### Alternativas consideradas

-

-

-

### Decisión

...

### Consecuencias positivas

-

-

### Consecuencias negativas

-

-

### Acciones derivadas

-

-
