# 0001 — Consola staff cross-tenant: modelo de autorización

- **Estado:** proposed (diseño cerrado en E4; implementación en E5)
- **Fecha:** 2026-06-09
- **Decisores:** Vic
- **Origen:** decisión D7 de `product/plans/re-architecture/re-architecture.md` §8.1; riesgo vigilado en §8.2
  («definir el modelo de permisos cross-tenant antes de E5»); diseño detallado
  durante E4 y consolidado en este ADR.

## Contexto y problema

La revisión humana multinivel (`product/plans/re-architecture/re-architecture.md` §4.6) introduce stages
secuenciales: `review_l1` (pool de **analistas de Llamitai**, internos) →
`review_l2` (pool de analistas del tenant/cliente). Los analistas L1 necesitan
una **cola unificada** con las `HumanTask` internas de **todos** los tenants:
trabajar tenant por tenant no escala el tier de servicio interno (SLA estilo
Ocrolus) que motiva el Caso 3.

El modelo de autorización actual es **100 % tenant-scoped** y no tiene concepto
de staff de plataforma:

- Identidad: JWT por usuario (`src/auth/infrastructure/services/jwt_token_builder.py`)
  + header `X-Tenant` (slug) resuelto por `get_required_tenant` →
  `get_required_tenant_user` (`src/common/infrastructure/dependencies/tenant.py`).
  Toda request autenticada termina en un `TenantUser` de **un** tenant.
- Datos: `HumanTaskRepository` (`src/workflows/domain/repositories/human_task.py`)
  exige `tenant_id` en `find_by_id` / `resolve` / `list_open`. No existe ninguna
  query cross-tenant en el sistema.
- `HumanTask` ya distingue `assignee_mode` (`INTERNAL_QUEUE` | `EXTERNAL_CALLBACK`)
  y `kind` (`CLARIFICATION` | `APPROVAL`), con `audience` como string libre
  (`doxiq_analyst` / `bank_analyst`). En E5 gana `stage`
  (`review_l1` interno / `review_l2` cliente).

**Problema:** ¿cómo autorizamos a personal de Llamitai a leer y resolver tareas
L1 de cualquier tenant sin romper el aislamiento multi-tenant que protege al
resto del sistema?

## Drivers

- **Cola unificada real**: una sola vista de trabajo L1 de todos los tenants;
  cero context-switching por tenant.
- **Aislamiento intacto**: el camino tenant-scoped (`X-Tenant` + `TenantUser`)
  no debe relajarse ni un milímetro; el blast radius de un bug staff debe
  quedar acotado a lectura de tareas/casos.
- **Mínimo privilegio**: staff L1 ve y resuelve tareas internas; **nada** de
  administración del tenant ni escritura sobre su configuración.
- **Auditabilidad**: cada acceso staff a datos de un tenant debe quedar
  registrado por acción, atribuible a una persona, exportable al tenant.
- **Revocación inmediata**: offboarding de un analista interno corta el acceso
  a todos los tenants en un solo paso.
- **No bloquear E5/Caso 3**: el diseño debe ser implementable como módulo
  acotado, sin re-arquitecturar auth.

## Opciones consideradas

### (a) Rol de plataforma + superficie `/staff/v1/*` separada

Identidad staff propia (claim + tabla), router dedicado gateado por esa
identidad, repos de lectura cross-tenant **explícitos y acotados** a
`HumanTask` + `Case` read. `X-Tenant` no aplica en esa superficie.

- ✅ Aislamiento por construcción: el código tenant-scoped no cambia; lo
  cross-tenant vive en un módulo auditable de ~5 endpoints.
- ✅ Mínimo privilegio y revocación centralizada nativos.
- ✅ Audit log natural: un solo choke point (el router staff) escribe eventos.
- ❌ Es el ítem nuevo más grande del plan: tabla, dependencia, router, repos,
  consola frontend.

### (b) Invitar al staff como miembro de cada tenant (fallback actual)

Cada analista L1 recibe una invitación normal y existe como `TenantUser` en
cada tenant que atiende.

- ✅ Cero código nuevo; funciona hoy.
- ❌ No hay cola unificada: N tenants = N switches de `X-Tenant`.
- ❌ Sobre-privilegio: un miembro ve mucho más que la cola L1 (workflows,
  documentos, dashboard) según su rol de tenant.
- ❌ Offboarding O(N) y propenso a olvidos; los analistas aparecen como
  miembros visibles para el cliente; sin audit diferenciado staff/cliente.
- ❌ No escala con el Caso 3 (decenas de tenants).

### (c) Impersonación / token de tenant elevado

Un servicio emite al staff un token temporal "como si" fuera un usuario del
tenant (o un super-token que satisface `get_required_tenant_user`).

- ✅ Reusa todos los endpoints tenant existentes; la consola sería un cliente más.
- ❌ Rompe la atribución: las acciones aparecen como del tenant/usuario
  impersonado; el audit requiere doble contabilidad frágil.
- ❌ Blast radius máximo: un token elevado abre **toda** la superficie del
  tenant, no solo la cola L1 — lo contrario de mínimo privilegio.
- ❌ Sigue sin resolver la cola unificada (el token es por tenant).
- ❌ Riesgo de compliance/confianza: "Llamitai puede actuar como tú" es
  difícil de vender y de auditar.

## Decisión

**Opción (a): rol de plataforma + superficie `/staff/v1/*` separada.**

Es la única opción que cumple los cinco drivers a la vez. (b) queda como
fallback explícito hasta E5 (ver abajo) y (c) se **prohíbe**: sin impersonación
en ninguna versión de la consola. El costo de (a) se acota porque el alcance
inicial es deliberadamente mínimo: leer cola L1, resolver tareas del stage
propio, ver el caso asociado en lectura. Nada más.

## Esbozo del modelo (contrato para E5)

### Identidad staff: tabla `staff_users` + claim `is_staff`

Ambas piezas, con responsabilidades distintas:

- **`staff_users`** (fuente de verdad, revocable): `uuid`, `user_id` (FK
  `users.uuid`, unique), `role` (`staff_analyst_l1` | `staff_admin`), `status`
  (`active` | `revoked`), `created_at`, `revoked_at`. Sin fila activa no hay
  acceso, sin importar qué diga el token.
- **Claim `is_staff: true`** en el access token (emitido en login si existe
  fila activa): gate barato de la superficie — permite rechazar en el router
  sin tocar DB cuando el claim falta, y deja el flag visible en logs/traces.

¿Por qué no solo el claim? Porque un JWT vive hasta su `exp`: revocar a un
analista exigiría blacklist de tokens. ¿Por qué no solo la tabla? Porque
entonces **toda** request (incluidas las tenant) pagaría un lookup para saber
si el caller es staff, y el flag no viajaría en el token para
observabilidad. La dependencia `StaffUserDep` (análoga a
`get_required_tenant_user`) verifica **claim presente Y fila activa**, y carga
el `role`.

### Alcance MÍNIMO de permisos

Staff L1 puede, sobre **cualquier** tenant:

1. **Leer la cola L1**: `HumanTask` con `assignee_mode = INTERNAL_QUEUE` y
   `stage = review_l1` (campo nuevo de E5), `status = pending`.
2. **Reclamar y resolver** tareas **de su stage** (lock pesimista por caso,
   §4.6); la resolución pasa por el mismo use case que dispara la señal
   `task_resolved` de Temporal, registrando el actor staff en `resolution`.
3. **Ver el caso asociado en modo lectura**: caso, documentos, extracción,
   resultados de reglas — solo lo necesario para resolver la tarea.

Staff L1 **NO** puede: administrar el tenant, listar/gestionar miembros,
tocar workflows/pipelines/policies, ver API keys o conexiones, leer tareas
`review_l2` ni `EXTERNAL_CALLBACK`, escribir nada fuera de
`claim/resolve`, ni usar endpoints tenant-scoped vía su identidad staff.

### Matriz rol × acción (mínima)

| Acción (`/staff/v1/*`) | `staff_analyst_l1` | `staff_admin` |
|---|---|---|
| Listar cola L1 cross-tenant | ✅ | ✅ |
| Reclamar tarea L1 (lock) | ✅ | ✅ |
| Resolver tarea L1 | ✅ | ✅ |
| Ver caso asociado (read-only) | ✅ | ✅ |
| Leer `staff_access_events` | ❌ | ✅ |
| Alta/revocación en `staff_users` | ❌ | ✅ |
| Cualquier otra cosa | ❌ | ❌ |

### Audit log: `staff_access_events`

Append-only, un evento por acción staff (incluidas las lecturas):
`uuid`, `staff_user_id` (FK), `action` (`list_tasks` | `view_case` |
`claim_task` | `resolve_task` | ...), `tenant_id`, `case_id?`, `task_id?`,
`request_id`, `ip`, `metadata` (JSONB), `created_at`. Lo escribe cada handler
de `/staff/v1/*` (o un middleware del router) — al ser la única puerta
cross-tenant, la cobertura es total por construcción. Sin UPDATE/DELETE;
índices por `tenant_id` y `staff_user_id` para export por tenant
(transparencia futura) y para el QA sampling por analista de §4.6.

### Aislamiento

- **Sin impersonación** (prohibida por este ADR). El staff nunca obtiene
  tokens, sesiones ni identidades de tenant.
- **`X-Tenant` no aplica** en `/staff/v1/*`: si llega, se ignora (o 400). El
  tenant de cada recurso viene del recurso mismo y queda en el audit.
- **Queries cross-tenant explícitas y acotadas**: repos staff dedicados (p. ej.
  `StaffHumanTaskRepository.list_open_l1()`, lectura de caso) en su propio
  módulo. Los repos tenant-scoped existentes (`HumanTaskRepository` y resto)
  **no se relajan**: siguen exigiendo `tenant_id`. Superficie cross-tenant
  total = `HumanTask` (read/claim/resolve) + `Case` y sus artefactos (read).
- **Doble muro**: la identidad staff no satisface `get_required_tenant_user`
  (no hay `TenantUser`), y la identidad tenant no satisface `StaffUserDep`
  (no hay claim/fila). Tests de aislamiento en ambos sentidos son entregable
  obligatorio de E5.

### Superficie API: `/staff/v1/*`

Router propio registrado en `config/router.py`, **todo** él gateado por
`StaffUserDep` (mismo patrón `add_api_route` del resto):

```
GET  /staff/v1/tasks                       # cola L1 unificada; filtros: tenant, kind, status
POST /staff/v1/tasks/{task_id}/claim       # lock pesimista
POST /staff/v1/tasks/{task_id}/resolve     # → señal task_resolved
GET  /staff/v1/cases/{case_id}             # caso asociado, read-only
GET  /staff/v1/audit                       # solo staff_admin
```

La consola frontend (vista de la cola, detalle de tarea/caso) consume solo
esta superficie; su diseño UI queda fuera de este ADR.

## Consecuencias

### Positivas

- Cola L1 unificada real → el tier interno del Caso 3 escala con el equipo,
  no con el número de tenants.
- El aislamiento multi-tenant existente queda **intacto**; lo cross-tenant es
  un módulo pequeño, enumerable y testeable.
- Audit por acción con atribución persona-real desde el día uno; base del QA
  sampling y del SLA de §4.6.
- Offboarding = una revocación en `staff_users`.
- Desbloquea E5 sin re-litigar: este documento es el contrato.

### Negativas

- Módulo nuevo completo (tabla, claim, dependencia, router, repos, consola):
  el ítem más grande del plan E5.
- Dos superficies API a mantener; algunos presenters de caso se duplican en
  variante read-only staff.
- El claim `is_staff` añade un paso al login y exige cuidar la emisión del
  token (no emitirlo a usuarios normales).

### Riesgos y mitigaciones

- **Fuga de alcance** («ya que estamos, que staff también edite X») →
  cualquier ampliación requiere un ADR que reemplace a este.
- **Bug en una query cross-tenant** expone datos entre tenants → repos staff
  separados + tests de aislamiento bidireccionales + audit append-only para
  forense.
- **Claim válido tras revocación** durante la vida del access token →
  `StaffUserDep` consulta la fila en cada request; el claim solo gatea, nunca
  autoriza por sí solo.
- **Audit incompleto** si un endpoint olvida registrar → preferir middleware
  a nivel de router staff sobre llamadas manuales por handler.

## Fallback vigente hasta E5

Mientras la consola no exista, se mantiene la **opción (b)**: los analistas
internos se invitan como miembros (`TenantUser`) de cada tenant que atienden,
con el rol de tenant más restrictivo disponible. Es deuda asumida y conocida:
sin cola unificada, offboarding manual por tenant, analistas visibles como
miembros, sin audit diferenciado. Ningún desarrollo nuevo debe construirse
sobre este fallback.

## Criterios de salida (activar la consola y retirar el fallback)

1. `HumanTask.stage` (`review_l1` / `review_l2`) migrado y poblado (E5).
2. `staff_users` + claim `is_staff` + `StaffUserDep` operativos; revocación
   inmediata verificada (fila revocada ⇒ 403 con token aún vigente).
3. Router `/staff/v1/*` desplegado con los 5 endpoints mínimos, gateado por
   el claim + fila.
4. `staff_access_events` escribiéndose en el 100 % de las acciones staff
   (verificado por test de cobertura del router).
5. Tests de aislamiento en ambos sentidos en verde: staff → endpoints tenant
   = 401/403; usuario tenant → `/staff/v1/*` = 403.
6. Enforce de roles por workflow activado (prerequisito del stage L2, §8.2) —
   no bloquea la cola L1 pero sí el flujo multinivel completo.
7. Membresías fallback de analistas internos revocadas en todos los tenants.

## Referencias

- `product/plans/re-architecture/re-architecture.md` §4.6 (revisión multinivel), §8.1 (D7), §8.2 (riesgos)
- `backend/src/workflows/domain/models/human_task.py` · `.../repositories/human_task.py`
- `backend/src/common/infrastructure/dependencies/tenant.py` (camino tenant-scoped actual)
- `backend/src/auth/infrastructure/services/jwt_token_builder.py` (emisión JWT)
