---
feature: usage-metering
type: spec
status: partial
coverage: 88
audited: 2026-06-16
---

# Spec: Vista de Uso — Doxiq

---

## Contexto del producto

Doxiq es un motor de procesamiento de documentos agnóstico al tipo de documento. A diferencia de Documente-WS (que opera sobre circulares legales), Doxiq opera sobre **workflows** que definen cómo se procesan archivos de cualquier tipo.

La unidad de trabajo en Doxiq es:

- **Workflow**: define las reglas de análisis
- **Document Set**: lote de documentos enviados a un workflow
- **Document**: un archivo; su resultado es una extracción según el workflow

Un mismo archivo puede pertenecer a varios document sets y procesarse varias veces. El tipo de documento no existe como concepto en Doxiq; lo que sí existe es el **workflow** al que fue sometido.

---

## Preguntas clave del producto

### 1. ¿Cómo se mide el procesamiento de páginas?

La unidad de cobro es la **página procesada**. Cuando un document es analizado exitosamente a través de un workflow, se cuentan las páginas del archivo en ese momento.

El conteo no depende del tipo de documento (no existe en Doxiq), sino del **workflow utilizado** y el **número de páginas del archivo**.

---

### 2. ¿En qué modelo se guardará el conteo de páginas procesadas?

Se crea un registro de procesamiento (`ProcessRecord`) cada vez que un documento es analizado exitosamente. Este registro almacena:

- El tenant al que pertenece
- El workflow que se utilizó (por su slug)
- El identificador único del documento procesado (digest)
- La cantidad de páginas procesadas en esa ocasión
- El momento exacto del procesamiento

Este modelo vive en el backend de Doxiq y es la fuente de verdad para métricas de uso y facturación.

---

### 3. ¿Qué es lo que detonará el conteo?

El conteo se registra cuando:

- El procesador interno finaliza exitosamente el análisis de un documento
- La solicitud llega como un evento del procesador (llamada server-to-server con API Key), no desde el browser del usuario

Solo los análisis **exitosos** generan un registro. Los intentos fallidos no cuentan.

**¿Qué implica "exitoso"?** El sistema evalúa el estado final del analysis run:

| Estado del analysis run | ¿Genera ProcessRecord? |
|---|---|
| `COMPLETED` | **Sí** — las reglas fueron evaluadas (aunque algunas fallen, el análisis llegó a término) |
| `FAILED` | No — el análisis terminó con error irrecuperable |
| `CANCELED` | No — el análisis fue interrumpido manualmente |
| `RUNNING` / `CANCELING` | No — el análisis aún no ha terminado |

Un run en estado `COMPLETED` representa que el pipeline de análisis completó su ejecución. El resultado individual de cada regla (SUCCESS, FAILED, SKIPPED) no afecta si se cuenta o no — lo que importa es que el run llegó a término.

---

### 4. ¿Hay un límite de cuántas páginas puede procesar?

Sí. Cada tenant tiene un plan activo que define una **cuota mensual de páginas**. El ciclo de facturación es mensual y se reinicia al inicio de cada mes calendario.

Los planes disponibles y sus cuotas son:

| Plan | Slug | Páginas/mes |
|---|---|---|
| Starter | `starter` | 500 |
| Pro | `pro` | 5,000 |
| Business | `business` | 25,000 |
| Enterprise | `enterprise` | Sin límite (o cuota personalizada) |

El plan por defecto al registrar un tenant es **Starter**. El campo `plan_slug` vive en la tabla `tenants`. Para Enterprise, existe un campo adicional `monthly_page_quota_override` (entero nullable) que, cuando está definido, reemplaza la cuota del plan — esto permite cuotas contractuales sin necesidad de un plan nuevo.

La cuota aplica a nivel de **tenant**, no de usuario individual.

---

### 5. ¿Qué pasa cuando un tenant supera sus límites?

Cuando el tenant ha consumido el 100% de su cuota mensual:

- El procesador recibe un error explícito al intentar registrar un nuevo procesamiento
- El análisis se rechaza — **no se procesa el documento**
- El tenant (con permisos de admin) recibe una notificación dentro de la plataforma indicando que alcanzó su límite
- Se le muestra una invitación a actualizar su plan

Adicionalmente, se envía una alerta preventiva cuando el tenant alcanza el **80% de su cuota** para que pueda tomar acción antes de ser bloqueado.

---

### 6. ¿Qué pasa cuando una página se procesa dos veces, se cuenta doble?

**Sí, se cuenta doble.** Cada invocación al análisis es un evento independiente. La re-extracción o re-análisis de un documento es una acción intencional del usuario o del sistema, y consume cuota igual que el procesamiento original.

Esto es consistente con el modelo de negocio: el costo real está en la inferencia que ocurre cada vez que el documento es analizado.

El sistema **no deduplica** por document digest. Dos registros con el mismo digest en el mismo mes representan dos procesamientos distintos y ambos descuentan de la cuota.

---

### 7. ¿Cómo verá cuánto lleva procesado el usuario?

Desde la plataforma, los usuarios con el permiso `workflows.view_usage` acceden a la página `/usage`, donde verán:

**Panel de resumen (período actual):**
- Páginas procesadas en el mes en curso
- Cuota total del plan activo
- Porcentaje de uso con barra visual (verde → amarillo → rojo)
- Días restantes en el período actual

**Historial de procesamiento:**
- Tabla con cada documento procesado: workflow utilizado, páginas, fecha
- El usuario puede filtrar por rango de fechas
- El historial no se limita al mes actual; puede consultar meses anteriores

---

### 8. ¿Quiénes pueden ver cuánto queda y cuánto se lleva?

El acceso está controlado por el permiso existente `workflows.view_usage`.

| Rol | Acceso |
|---|---|
| **Owner** del tenant | Ve todo, siempre (bypasa permisos) |
| **Admin** (tiene `workflows.view_usage`) | Ve resumen y historial completo del tenant |
| **Miembro** con `workflows.view_usage` asignado | Ve resumen y historial completo del tenant |
| **Miembro** sin ese permiso | No ve la página de uso; es redirigido a `/forbidden` |

No existe visibilidad por usuario individual dentro de la plataforma en esta versión. El conteo es siempre a nivel de **tenant**.

---

### 9. ¿Cómo un usuario puede ver cuántas páginas procesó desde la fecha Y hasta la fecha Z?

Desde la página `/usage`, el usuario puede:

1. Seleccionar un rango de fechas de inicio y fin en un filtro de fecha
2. El sistema calcula y muestra el total de páginas procesadas en ese rango
3. La tabla de historial se filtra para mostrar únicamente los registros en ese período
4. Los registros pueden descargarse o exportarse (a considerar en iteraciones futuras)

El backend soporta este filtro con parámetros de fecha en el endpoint de listado. No hay límite en el rango de fechas consultable, pero el rendimiento de consultas muy amplias será gestionado con paginación.

---

## Decisiones de producto abiertas

Estas preguntas deben resolverse antes de iniciar la implementación:

| Pregunta | Estado |
|---|---|
| ¿La alerta del 80% es in-app, por email, o ambas? | Pendiente |
| ¿Se muestra el uso en el dashboard principal además de `/usage`? | Pendiente |
| ¿Los registros de historial tienen una retención máxima (ej. 12 meses)? | Pendiente |
| ¿El bloqueo por límite aplica inmediatamente o al inicio del siguiente día? | Pendiente — recomendado: inmediato |
| ¿Hay página de confirmación o aviso antes de re-analizar para que el usuario sepa que consume cuota? | Pendiente |

---

## Alcance de esta versión

### Incluido

- Registro de cada procesamiento exitoso con su conteo de páginas
- Validación de cuota al momento del procesamiento (bloqueo si se supera)
- Alerta preventiva al 80% de uso
- Página `/usage` con resumen del período actual e historial filtrable por fechas
- Control de acceso por permiso `workflows.view_usage`

### No incluido (iteración futura)

- Exportación de historial a CSV/Excel
- Notificaciones por email al alcanzar límites
- Visibilidad de uso por usuario individual
- Dashboard de uso embebido en la página principal
- Overage billing (cargo por excedente)
- Historial de cambios de plan

---

## Componentes a construir

### Backend

| Componente | Qué hace |
|---|---|
| Registro de procesamiento | Modelo que guarda cada evento de análisis exitoso |
| Validador de cuota | Verifica antes de registrar si el tenant tiene cuota disponible |
| Agregador de uso | Calcula totales de páginas por tenant y por período |
| Caché de resumen | Almacena temporalmente el resumen para evitar queries frecuentes |
| Endpoint de creación | Recibe el evento del procesador (server API key) |
| Endpoint de listado | Lista el historial paginado con filtro de fechas |
| Endpoint de resumen | Devuelve el consolidado del período con caché |

### Frontend

| Componente | Qué hace |
|---|---|
| Página `/usage` | Contenedor principal, protegida por `PermissionGuard` |
| Cards de resumen | Muestra páginas usadas, cuota total, porcentaje con barra visual |
| Selector de fechas | Permite definir el rango del historial |
| Tabla de historial | Lista paginada de documentos procesados con sus páginas y workflow |

---

## Notas de diseño de datos

- El registro de procesamiento está ligado al **workflow slug**, no al tipo de documento (que no existe en Doxiq)
- La cuota mensual es un atributo del **plan del tenant**, no del tenant directamente
- Los registros son inmutables — no se editan ni eliminan, solo se acumulan
- El período de facturación es el mes calendario (del día 1 al último día del mes)
