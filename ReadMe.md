# Diseño de Software - Sistema de Gestión de Biblioteca Personal

**Versión:** 1.0

**Autor(es):** Equipo de Desarrollo

**Fecha:** 22 de Septiembre, 2025

**Historial de revisiones:**


| Versión | Fecha      | Autor(es) | Cambios Realizados              | Aprobado por      |
| -------- | ---------- | --------- | ------------------------------- | ----------------- |
| 0.1      | 2025-09-22 | Equipo    | Creación inicial del documento | Líder del equipo |
|          |            |           |                                 |                   |

## 1. Introducción (Caso de uso)

### Descripción general del sistema

El Sistema de Gestión de Biblioteca Personal es un Alexa Skill que permite a los usuarios gestionar de manera intuitiva su colección personal de libros mediante comandos de voz. El sistema facilita el control de inventario, préstamos y devoluciones de libros físicos.

### Objetivo del documento

Definir la arquitectura y diseño del sistema aplicando principios SOLID y los cuatro pilares de la POO, migrando desde una implementación monolítica hacia una estructura modular y mantenible.

### Alcance

**Incluye:**

* Gestión de inventario de libros (agregar, listar, buscar)
* Sistema de préstamos y devoluciones
* Persistencia de datos en S3
* Interfaz de voz natural con diálogos conversacionales
* Paginación de resultados
* Historial de transacciones
* Eliminación de libros (funcionalidad adicional)

**No incluye:**

* Gestión de usuarios múltiples
* Integración con servicios externos de libros
* Funciones de compra/venta

### Actores principales

* **Usuario primario:** Propietario de la biblioteca personal
* **Sistema Alexa:** Interfaz de interacción vocal
* **Amazon S3:** Servicio de persistencia de datos

### Casos de uso relevantes

1. Agregar libros mediante diálogo conversacional
2. Consultar inventario con paginación
3. Registrar préstamos con fechas límite
4. Procesar devoluciones
5. Consultar historial de movimientos
6. Eliminar libros de la colección

---

## 2. Problem Statement (Declaración del problema)

### Contexto

El código actual está implementado como un monolito en un único archivo `lambda_function.py` de más de 1000 líneas, donde toda la lógica de negocio, manejo de datos, y control de interfaz están mezclados sin separación de responsabilidades.

### Problemas específicos

* **Mantenibilidad:** Difícil de modificar y extender debido al acoplamiento alto
* **Testabilidad:** Imposible realizar pruebas unitarias efectivas
* **Escalabilidad:** Agregar nuevas funcionalidades requiere modificar múltiples secciones
* **Legibilidad:** Código complejo y difícil de entender
* **Reutilización:** Lógica duplicada en múltiples handlers

### Impacto de no resolverlos

* Tiempo de desarrollo incrementado exponencialmente
* Mayor probabilidad de bugs al hacer cambios
* Dificultad para onboarding de nuevos desarrolladores
* Imposibilidad de implementar CI/CD efectivo

### Restricciones del entorno

* Debe funcionar en AWS Lambda
* Compatibilidad con Alexa Skills Kit
* Límites de tiempo de ejecución de Lambda (15 minutos máx)
* Restricciones de memoria y almacenamiento temporal

---

## 3. Requerimientos funcionales


| ID    | Descripción                     | Actor   | Prioridad | Criterios de aceptación                                              |
| ----- | -------------------------------- | ------- | --------- | --------------------------------------------------------------------- |
| RF-01 | Agregar libros mediante diálogo | Usuario | Alta      | El sistema debe solicitar título, autor y tipo en pasos secuenciales |
| RF-02 | Listar libros con paginación    | Usuario | Alta      | Mostrar máximo 10 libros por página con navegación                 |
| RF-03 | Buscar libros por título/autor  | Usuario | Media     | Encontrar coincidencias parciales en títulos y autores               |
| RF-04 | Registrar préstamos             | Usuario | Alta      | Capturar libro, persona y fecha límite automática                   |
| RF-05 | Procesar devoluciones            | Usuario | Alta      | Actualizar estado y registrar en historial                            |
| RF-06 | Consultar préstamos activos     | Usuario | Media     | Mostrar libros prestados con fechas y personas                        |
| RF-07 | Ver historial completo           | Usuario | Baja      | Acceder a todas las transacciones pasadas                             |
| RF-08 | Eliminar libros                  | Usuario | Media     | Remover libros de la colección con confirmación                     |
| RF-09 | Sincronizar estados              | Sistema | Alta      | Mantener consistencia entre libros y préstamos                       |
| RF-10 | Persistir datos                  | Sistema | Alta      | Guardar/recuperar datos desde S3 automáticamente                     |

---

## 4. Requerimientos no funcionales


| ID     | Atributo       | Descripción                 | Métricas / criterios cuantitativos     |
| ------ | -------------- | ---------------------------- | --------------------------------------- |
| RNF-01 | Rendimiento    | Respuesta rápida en Lambda  | < 3 segundos por operación             |
| RNF-02 | Escalabilidad  | Soporte múltiples libros    | Hasta 1000 libros por usuario           |
| RNF-03 | Disponibilidad | Funcionamiento continuo      | 99.9% uptime                            |
| RNF-04 | Usabilidad     | Interacción natural por voz | Comprensión > 90% comandos válidos    |
| RNF-05 | Mantenibilidad | Código modular y testeable  | Cobertura de pruebas > 80%              |
| RNF-06 | Seguridad      | Datos de usuario protegidos  | Encriptación en S3, acceso por usuario |

---

## 5. Arquitectura / Diseño – C4 Diagrams

### Descripción general de la arquitectura

El sistema sigue una arquitectura por capas con separación clara de responsabilidades:

* **Capa de Presentación:** Handlers de Alexa
* **Capa de Lógica de Negocio:** Services y Controllers
* **Capa de Datos:** Repositories y Models
* **Capa de Infraestructura:** Adapters y Utilities

### Diagramas C4

#### Diagrama de Contexto (Level 1)

```mermaid
C4Context
title System Context diagram for Biblioteca Personal Skill

Person(user, "Usuario", "Usuario de la Biblioteca Personal Skill")
System_Boundary(alexa_boundary, "Amazon Alexa") {
  System(alexa, "Amazon Alexa", "Voice service platform")
  System(skill, "Biblioteca Personal Skill", "Alexa Skill for managing books")
}

SystemDb(s3, "Amazon S3", "Object Storage")
SystemDb(ddb, "DynamoDB Cache", "NoSQL Database")

Rel(user, alexa, "Comandos de voz")
Rel(alexa, user, "Respuestas de voz")
Rel(user, alexa, "Uses")
Rel(alexa, skill, "Invokes Skill")
Rel(skill, s3, "Uses")
Rel(skill, ddb, "Uses")
```

#### Diagrama de Contenedores (Level 2)

```mermaid
C4Container
title Container diagram for Alexa Biblioteca Skill

System_Ext(alexa_platform, "Amazon Alexa Platform", "Voice Assistant Platform")
Container(ask, "Alexa Skills Kit", "Cloud Service", "Receives and processes voice commands")

Container_Boundary(lambda, "AWS Lambda Container") {
    Container(skill_app, "Biblioteca Skill Application", "Node.js Lambda", "Skill logic executed on requests")
}

Container_Boundary(storage, "Storage Layer") {
    ContainerDb(s3db, "S3 Bucket", "S3", "Persistent Storage")
    Container(memcache, "Memory Cache", "In-memory Cache", "Temporary fast-access storage")
    ContainerDb(ddb_cache, "DynamoDB Cache", "DynamoDB", "Optional cache layer")
}

Rel(alexa_platform, ask, "Uses")
Rel(ask, skill_app, "Invokes on voice command intent")
Rel(skill_app, s3db, "Reads/Writes data")
Rel(skill_app, memcache, "Reads/Writes data")
Rel(skill_app, ddb_cache, "Reads/Writes data (optional)")
```

#### Diagrama de Componentes (Level 3)

```mermaid
C4Container
title Container diagram for Book Library System

Container_Boundary(presentation, "Presentation Layer") {
  Container(LH, "Launch Handler")
  Container(ALH, "Add Book Handler")
  Container(LLH, "List Books Handler")
  Container(PLH, "Loan Handler")
  Container(RH, "Return Handler")
  Container(FBH, "Fallback Handler")
}

Container_Boundary(business, "Business Layer") {
  Container(BS, "Book Service")
  Container(LS, "Loan Service")
  Container(US, "User Service")
  Container(VS, "Validation Service")
}

Container_Boundary(data, "Data Layer") {
  Container(BR, "Book Repository")
  Container(LR, "Loan Repository")
  Container(UR, "User Repository")
}

Container(s3a, "S3 Adapter", "Infrastructure", "Handles storage interactions")
Container(ca, "Cache Adapter", "Infrastructure", "Caches data for fast access")
Container(um, "Utils Manager", "Infrastructure", "Utility functions manager")

Container_Boundary(models, "Models") {
  Container(BM, "Book Model")
  Container(LM, "Loan Model")
  Container(U_M, "User Model")
}

Rel(LH, US, "Calls")
Rel(ALH, BS, "Calls")
Rel(LLH, BS, "Calls")
Rel(PLH, LS, "Calls")
Rel(RH, LS, "Calls")
Rel(BS, BR, "Uses")
Rel(LS, LR, "Uses")
Rel(US, UR, "Uses")
Rel(BR, s3a, "Uses")
Rel(LR, s3a, "Uses")
Rel(UR, s3a, "Uses")
Rel(BR, ca, "Uses")
Rel(LR, ca, "Uses")
Rel(UR, ca, "Uses")
```

**Enlaces a diagramas detallados:**

<!-- * [Repositorio GitHub - Diagramas C4](https://github.com/team/biblioteca-skill/docs/architecture) -->

---

## 6. Diseño VUI / Diagramas de flujo de voz

### Objetivo del diseño VUI

Crear una experiencia de voz natural e intuitiva que simule una conversación con un bibliotecario personal, minimizando la fricción y maximizando la comprensión.

### Estilo, tono y lenguaje de voz

* **Tono:** Amigable, servicial y profesional
* **Personalidad:** Bibliotecario experto pero accesible
* **Lenguaje:** Español mexicano, formal pero cercano
* **Respuestas:** Variadas para evitar repetición, confirmaciones claras

### Escenarios de uso por voz

* **Cuándo:** En casa, durante organización de libros, antes/después de préstamos
* **Dónde:** Biblioteca personal, estudio, sala de estar
* **Dispositivos:** Echo Dot, Echo Show, dispositivos móviles con Alexa
* **Entorno:** Silencioso a moderadamente ruidoso

### Diagramas de flujo de conversación DIAGRAMA

#### Flujo Principal - Agregar Libro DIAGRAMA

#### Flujo - Eliminar Libro (Nuevo) DIAGRAMA

#### Flujo - Manejo de Errores DIAGRAMA

### Consideraciones especiales

* **Latencia:** Respuestas en < 2 segundos para mantener fluidez
* **Reconocimiento:** Manejo de variaciones en pronunciación de títulos
* **Fallbacks:** Múltiples niveles de clarificación antes de cancelar
* **Context:** Mantener contexto durante diálogos multi-turno
* **Confirmaciones:** Siempre confirmar acciones destructivas

**Enlaces a diagramas detallados:**

* [Figma - Flujos VUI Completos](https://figma.com/file/biblioteca-vui-flows)

---

## 7. Secciones adicionales

---

## 8. Apéndices

---

## 9. Revisión y mantenimiento del documento

### Historial de Revisión / Mantenimiento


| Versión | Fecha    | Autor(es)               | Cambios Realizados                                      | Aprobado por           | Comentarios adicionales               |
| -------- | -------- | ----------------------- | ------------------------------------------------------- | ---------------------- | ------------------------------------- |
| 0.1      | xxxxxxxx | Equipo completo         | Creación inicial del documento; análisis del monolito | Líder del equipo      | Primer borrador con casos de uso      |
| 0.5      | xxxxxxxx | Desarrollador principal | Incorporación de diagramas C4 y arquitectura           | Arquitecto de software | Revisión de patrones aplicados       |
| 0.8      | xxxxxxxx | UX Designer             | Adición de flujos VUI y diagramas de voz               | Product Owner          | Validación de experiencia de usuario |
| 1.0      | xxxxxxxx | Equipo completo         | Documento aprobado con apéndice de refactorización    | Líder del equipo      | Versión final para implementación   |
