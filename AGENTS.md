# AGENTS.md

# Traffic Rain Risk Optimizer

## Objetivo del proyecto

Este proyecto busca desarrollar un sistema que recomiende rutas con menor riesgo durante lluvias utilizando Inteligencia Artificial y Optimización Cuántica.

La arquitectura general será:

Datos abiertos
→ Modelo de IA
→ Matriz de riesgo
→ Optimización QUBO
→ QAOA
→ Ruta recomendada

El proyecto se desarrolla de forma incremental.

No deben implementarse componentes que no hayan sido aprobados.

---

# Regla principal

Nunca agregues tecnologías, servicios o dependencias sin preguntarme primero.

Antes de implementar cualquier cambio debes explicar:

- qué deseas agregar
- por qué
- ventajas
- desventajas
- costo
- si entra en AWS Free Tier
- alternativas gratuitas

Después debes esperar mi aprobación.

No implementes nada automáticamente.

---

# Objetivo económico

Este proyecto debe mantenerse dentro del AWS Free Tier.

Objetivos:

- costo cero siempre que sea posible
- evitar facturación accidental
- evitar servicios administrados innecesarios

Si alguna propuesta puede generar costos debes avisarlo antes.

Nunca asumas que acepto pagar.

---

# Tecnologías aprobadas

Actualmente solamente están aprobadas:

- Python
- Jupyter Notebook
- Git
- GitHub
- pandas
- numpy
- scikit-learn
- matplotlib
- Amazon SageMaker
- Amazon Braket Local Simulator
- AWS Lambda (únicamente si más adelante se aprueba el despliegue)
- Datos Abiertos CDMX
- SACMEX

No agregues ninguna otra tecnología.

---

# Tecnologías que requieren aprobación

Antes de utilizarlas debes preguntar.

AWS

- API Gateway
- DynamoDB
- Aurora
- RDS
- S3
- EC2
- ECS
- EKS
- Bedrock
- OpenSearch
- Step Functions
- EventBridge
- SNS
- SQS
- Cognito
- CloudFormation
- CDK
- IAM adicional
- CloudWatch
- X-Ray

Infraestructura

- Docker
- Kubernetes
- Terraform
- Pulumi

Bases de datos

- PostgreSQL
- MongoDB
- Redis
- Elasticsearch
- Firebase
- Supabase

APIs

- Google Maps API
- OpenRouteService
- HERE
- TomTom
- Mapbox
- cualquier API comercial

Frameworks

- FastAPI
- Flask
- Django
- Streamlit
- React
- NextJS

Ninguna debe utilizarse sin aprobación.

---

# Arquitectura actual

Actualmente existen dos módulos.

## Módulo IA

Responsabilidad:

- analizar datos abiertos
- generar matriz de riesgo

Tecnología:

Amazon SageMaker

---

## Módulo Cuántico

Existe un notebook funcional basado en:

- QUBO
- QAOA

Este notebook NO debe reemplazarse.

Debe reutilizarse.

No modificar la formulación matemática sin autorización.

---

# Desarrollo incremental

Trabajaremos por fases.

Cada fase debe contener:

Objetivo

Archivos modificados

Archivos nuevos

Dependencias nuevas

Servicios AWS

Costo esperado

Riesgos

Al finalizar la explicación debes esperar aprobación.

---

# Código

Cuando escribas código:

No agregues funcionalidades adicionales.

No hagas refactorizaciones innecesarias.

No cambies nombres de archivos.

No cambies estructura del proyecto.

No cambies variables sin preguntar.

No elimines código existente.

Haz únicamente lo solicitado.

---

# Librerías

Antes de instalar una librería debes responder:

¿Por qué se necesita?

¿Existe alternativa usando la librería estándar?

¿Tiene costo?

¿Tiene licencia compatible?

Después espera aprobación.

---

# AWS

No crear automáticamente:

- recursos
- buckets
- endpoints
- funciones
- políticas IAM
- usuarios
- roles

Primero explicar.

Después esperar aprobación.

---

# Optimización

Siempre intenta utilizar primero:

1. herramientas locales

2. software open source

3. simuladores

4. Free Tier

Solo después propone servicios administrados.

---

# Respuestas

Cuando propongas una mejora utiliza siempre este formato.

## Sugerencia

Descripción

### Beneficios

...

### Riesgos

...

### Costo

...

### ¿Requiere AWS?

Sí / No

### ¿Entra en Free Tier?

Sí / No

### ¿Deseas implementarlo?

Esperaré tu aprobación.

---

# Estilo

Siempre explica antes de programar.

Siempre trabaja paso por paso.

Nunca avances a la siguiente fase automáticamente.

Nunca tomes decisiones arquitectónicas por tu cuenta.

El usuario decide la arquitectura final.

# Computación Cuántica

Existe un notebook previo que sirve como referencia matemática.

La implementación final deberá desarrollarse utilizando Amazon Braket SDK y Amazon Braket Local Simulator.

No reutilices el notebook como código de producción.

No copies código línea por línea.

Analiza la lógica, comprende el modelo matemático y construye una implementación limpia, modular y mantenible.

Si detectas diferencias entre la implementación actual y Amazon Braket, explícalas primero y espera aprobación antes de realizar cambios.