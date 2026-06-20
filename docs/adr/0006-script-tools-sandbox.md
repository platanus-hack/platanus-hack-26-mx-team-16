# 0006 — Script tools (Python/JS) en sandbox aislado in-cluster

- **Estado:** accepted (transporte + interfaz + fail-closed); **ejecutor real: BLOQUEADO hasta revisión de seguridad + provisión ops** (ver §Gate de seguridad)
- **Fecha:** 2026-06-14
- **Decisores:** Vic (decisión D-D zanjada 2026-06-14)
- **Origen:** `product/plans/pipeline/phases-config.md` §6.4 + D-D. `enrich` corre tools
  firmadas vía el connector determinista, hoy **solo HTTP**. El negocio pide tools
  de **script** (Python/JS) para enriquecimiento que no es una API REST.

## Contexto y problema

Ejecutar **código no confiable** (escrito por tenants/operadores) es el mayor
riesgo de seguridad de toda la propuesta. Necesita aislamiento fuerte, no la
ejecución in-process ni un `eval`. D-D descartó «una Lambda por lenguaje» (cold
starts, superficie IAM, difícil de acotar la red) a favor de un **runner sandbox
in-cluster** efímero por invocación.

## Drivers

- **Aislamiento fuerte** de código no confiable (kernel-level).
- **Determinismo Temporal:** la ejecución va en una activity (vía el connector),
  nunca en el workflow.
- **Fail-closed:** sin sandbox provisionado, NUNCA se ejecuta — se degrada (B1).
- **Paridad con HTTP:** mismo render de args (`@slug.path`/`{{token}}`), mismo
  `on_failure`, misma forma `ToolResult`.

## Opciones consideradas

- **A — in-process (`exec`/subprocess sin aislar).** Inaceptable: RCE trivial. Rechazada.
- **B — una Lambda por lenguaje.** Cold starts, superficie IAM amplia, red difícil
  de acotar. Rechazada (D-D).
- **C — runner sandbox in-cluster (gVisor/Firecracker), efímero por invocación.**
  Aislamiento kernel-level, red por allowlist, límites de recursos. **Elegida (D-D).**

## Decisión

1. **Transporte:** `ToolTransport` gana `PYTHON` y `JS`. El código vive en
   `tool_definitions.config` (`{runtime, entrypoint, code | code_ref, limits}`);
   `code_ref` apunta a object storage para scripts grandes.
2. **Dispatch en el connector:** `DeterministicToolConnector.call` rutea
   `PYTHON`/`JS` a un `ScriptRunner` inyectado (la ruta HTTP queda **intacta**,
   byte-idéntica). Un fallo del runner degrada (igual que HTTP).
3. **Interfaz + fail-closed:** `ScriptRunner` (Protocol) + `UnconfiguredScriptRunner`
   (default que **rechaza toda ejecución** — `ScriptSandboxNotConfiguredError`).
   Sin runner real inyectado, las script tools **degradan** (`script_sandbox_not_configured`):
   jamás se ejecuta código sin sandbox.
4. **Runner dev local** (`LocalSubprocessScriptRunner`, **default-off**): subproceso
   con rlimits (CPU/memoria/fsize best-effort), timeout, env scrubbed (sin
   secretos), cwd temporal efímero y output capeado a 1 MiB. Se activa SOLO con
   `TOOLS_SCRIPT_RUNNER=local_subprocess` (loggea un warning «DEV ONLY»). **NO
   aísla red ni kernel** — sirve para probar el contrato en local/CI, no para prod.
5. **El ejecutor de PRODUCCIÓN (gVisor/Firecracker) NO se implementa en este corte**:
   es trabajo de ops + debe pasar el gate de seguridad de abajo. La interfaz
   (`ScriptRunner`) queda lista para enchufarlo sin tocar el connector ni `enrich`;
   `TOOLS_SCRIPT_RUNNER` seleccionará el runner sandboxed cuando exista.

## Gate de seguridad (revisión dedicada — bloqueante antes de habilitar el ejecutor)

- [ ] **Aislamiento:** gVisor o Firecracker; un microVM/sandbox **efímero por
      invocación**; sin reutilización de estado entre invocaciones.
- [ ] **Red:** **denegada por defecto**; solo el host-allowlist de la
      ConnectionAccount (mismas reglas SSRF que HTTP: https, no IPs privadas/loopback).
- [ ] **Recursos:** límites duros de CPU, wall-clock (timeout), memoria, PIDs,
      tamaño de fs; sin disco persistente.
- [ ] **Secretos:** sin acceso a env/secretos del host; solo los inyectados
      explícitamente para esa tool; nunca credenciales de plataforma.
- [ ] **Entradas/salidas:** args renderizados fuera del sandbox; salida limitada
      en tamaño y validada contra `output_schema` antes de persistir.
- [ ] **Supply chain:** runtime pinneado por digest; sin `pip/npm install`
      arbitrario en tiempo de ejecución (deps pre-bakeadas o vendoreadas).
- [ ] **Abuso/DoS:** rate-limit + circuit breaker (reutilizar el del connector);
      cuotas por tenant; kill de sandboxes colgados.
- [ ] **Auditoría:** snapshot por invocación (code_ref, args, límites, salida)
      en el trail B1; logs de denegaciones de red.

## Consecuencias

- **+** Transporte y dispatch listos; `enrich` (eager, ya pasa por el connector)
  los hereda sin cambios cuando el runner real exista.
- **+** Fail-closed por diseño: imposible ejecutar sin sandbox.
- **+** Ruta HTTP byte-idéntica (cero regresión).
- **−** Hasta cerrar el gate de seguridad + provisión ops, las script tools son
  declarables/publicables pero **degradan** en runtime (no ejecutan).
- **−** El ejecutor sandbox es infra nueva (gVisor/Firecracker) con coste
  operativo y de mantenimiento propio.
