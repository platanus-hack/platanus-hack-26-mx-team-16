---
feature: attack-levels
type: plan
status: pending
coverage: 0
audited: 2026-06-20
spec: ../02-attack-levels/spec.md
sources:
  - ../02-attack-levels/spec.md §3, §4, §5, §6, §7, §8
  - ../01-legal-ethics/spec.md §1, §2.2, §2.4, §3 (piso legal del pasivo, gate, scheduler, UA, rate-limit)
  - ../03-agentic-surface/spec.md §1, §3 (batería agéntica paralela — cross-ref)
  - ../04-scanning-engine/spec.md §4.1, §4.2, §10 (mecánica de ejecución, timeouts, watchdog, hexstrike healthcheck)
  - ../05-agent-team/spec.md §1.1, §5 (Team Agno, construcción de owasp_agent, flujo del worker)
  - ../06-data-model/spec.md (entidad scans, ScanLevel ENUM, sites.is_gov, Finding)
---

# Niveles de ataque y subagente OWASP (web) — plan de implementación (CÓMO)

Este documento es el **CÓMO** del subspec [02-attack-levels](spec.md). La fuente de
verdad del **QUÉ** (qué corre cada nivel, la whitelist `(is_gov, level)`, `robots.txt`,
alcance del avanzado, perfil demo) es el `spec.md`. Aquí se fija la **estructura de
código concreta**: el resolver puro `resolve_toolset`, la whitelist declarativa
congelada, el punto exacto del flujo del worker donde se imponen las tools, y los
tests que garantizan el contrato.

La pieza normativa es deliberadamente pequeña: **un mapping congelado + una función
pura**. El resto es andamiaje mínimo (un value object y un enum de ids de tool) para
que esa función sea auditable y testeable contra el piso legal pasivo gov/básico,
cuyo set de tags Nuclei es ya el **canónico unificado** en 01 §3 y 02 §4
(`exposures,misconfiguration,ssl,tech,dns`; ver §3.2).

---

## 1. Alcance del plan y qué delega

Este plan **es dueño** de, y construye:

- El enum `ToolId` (ids estables de cada tool web) y el value object `ToolInvocation`.
- La **política / definición** de la whitelist `(is_gov, level)`: **qué** tools+flags
  corre cada nivel (el contenido de las baterías por celda), expresada aquí como el
  mapping declarativo `TOOLSET_WHITELIST` y el perfil demo `DEMO_PROFILE`.

  > **Ownership (split resuelto 02 ↔ 04):** la **política/definición** —el contenido de
  > cada celda `(is_gov, level)` y el **contrato lógico** del resolver— es de **02**.
  > La **estructura de datos concreta** de la whitelist y su **enforcement en el
  > worker** (la máquina runtime que materializa el mapping y el drop point donde se
  > descartan las tools no permitidas antes de que `owasp_agent` las reciba, más la
  > ejecución de tools) son de **[04-scanning-engine](../04-scanning-engine/spec.md)**;
  > [01-legal-ethics](../01-legal-ethics/spec.md) §3 ya cross-refiere a 02 para la
  > definición y a 04 para la estructura+enforcement. El `TOOLSET_WHITELIST` de abajo
  > es la **expresión declarativa de la política de 02**; su materialización runtime
  > (forma de datos congelada, drop point) la honra 04 (cross-ref, no se redefine aquí).
- El resolver puro `resolve_toolset(is_gov, level, *, demo, hexstrike_ok)` — su
  **contrato lógico** es propiedad de 02 y es la **única** fuente que consumen tanto la
  garantía pasiva del scheduler (01) como la construcción de `owasp_agent` (05).
- El servicio `RobotsPolicy` (interfaz + impl `urllib.robotparser`) y el UA de scanner.
- Las claves de `Settings` que este feature posee: `ENABLE_HEXSTRIKE`,
  `SCAN_GLOBAL_BUDGET_SECONDS`, `DEMO_PROFILE_TIMEOUT_SECONDS`, `SCANNER_USER_AGENT`.

Lo que **delega** (cross-ref de una línea, no se redefine aquí):

- **[01-legal-ethics](../01-legal-ethics/spec.md):** gate de atestación persistido, el
  scheduler/seed-cron que **no puede** emitir `level != basico`, política de UA y
  rate-limit, y el contrato **legal** del piso pasivo gov/básico (§3). La celda
  `(True, BASICO)` de nuestra whitelist es **byte-equivalente** a ese piso: 01 §3 y 02
  §4 fijan **el mismo** set de tags Nuclei canónico
  (`exposures,misconfiguration,ssl,tech,dns`), idéntico al básico general (§3.1); los
  dos specs están **unificados**.
- **[03-agentic-surface](../03-agentic-surface/spec.md):** la batería agéntica paralela
  (sondas, caps 8/20, prohibición garak/promptfoo en `.gob.mx`, `agentic_status`). Nuestra
  whitelist es **solo web**; no se añaden filas agénticas.
- **[04-scanning-engine](../04-scanning-engine/spec.md):** la **estructura de datos
  concreta** de la whitelist y su **enforcement en el worker** (materialización runtime
  del mapping y el drop point donde se descartan las tools no permitidas antes de
  `owasp_agent`), más la mecánica de ejecución (`subprocess.run` / `run_tool` DooD),
  tabla de timeouts por tool (§4.2), watchdog del budget ~8 min, concurrencia
  intra-scan, red de egress, parsers → `Finding[]`. Nosotros definimos **qué** tools+flags
  corre cada celda (la política) y el contrato lógico del resolver; 04 los materializa,
  impone y ejecuta.
- **[05-agent-team](../05-agent-team/spec.md):** el Team Agno (Opus + 2 Sonnet), la firma
  de `orchestrator.run(url, level)` y las tool-functions `run_*`. Aquí solo se nombra el
  **seam** donde `resolve_toolset` alimenta el argumento `tools=` de `owasp_agent`.
- **[06-data-model](../06-data-model/spec.md):** la entidad `scans`, el ENUM Postgres
  `scans.level`, la derivación `sites.is_gov` y el contrato `Finding`. Importamos
  `ScanLevel`; no lo redefinimos.

---

## 2. Modelo de datos tocado

Este feature **no crea tablas ni migraciones**. Solo **lee** dos campos que posee
[06-data-model](../06-data-model/spec.md):

- `scans.level` — ENUM Postgres `(basico, intermedio, avanzado)`. El enum Python
  `ScanLevel` (valores `"basico" | "intermedio" | "avanzado"`, alineados con el DDL)
  es **propiedad de 06-data-model**, que lo define en
  `src/common/domain/enums/scans.py` como subclase de `BaseEnum`
  (ver [06-data-model](../06-data-model/plan.md) §2.1, junto al resto de enums del
  SCAN). Este feature lo **importa** desde `src.common.domain.enums.scans` para
  indexar la whitelist; nunca lo redefine, no lo reubica bajo `src/scans/…` ni añade
  un miembro `demo`.

- `sites.is_gov` — `bool` **derivado server-side** en el insert del sitio como
  `hostname.endswith(".gob.mx")` (06). Nunca lo aceptamos del cliente ni lo computamos
  aquí. El `ScanHandler` lo lee de la fila persistida del sitio para construir la clave
  `(is_gov, level)`. Por [01](../01-legal-ethics/spec.md) §2.4 es **no bloqueante**: solo
  afecta copy de advertencia (13-frontend) y visibilidad de ranking (08).

Lo **único** que este feature define como tipo propio son el `ToolId` enum y el
`ToolInvocation` value object (ver §3) — ninguno se persiste; son artefactos de
configuración en memoria.

---

## 3. La whitelist `(is_gov, level)`

### 3.1 Tipos de soporte

`ToolId` enumera todas las tools web (ids estables que 05 mapea a sus `run_*` y 04 a su
tabla de timeouts §4.2):

```python
# backend/src/scans/domain/enums/tool_id.py
from enum import StrEnum


class ToolId(StrEnum):
    TESTSSL = "testssl"
    SECURITY_HEADERS = "security_headers"   # security-headers / Observatory
    WHATWEB = "whatweb"
    NUCLEI = "nuclei"
    ZAP_BASELINE = "zap_baseline"
    ZAP_FULL_ACTIVE = "zap_full_active"
    NIKTO = "nikto"
    KATANA = "katana"
    FFUF = "ffuf"
    SQLMAP = "sqlmap"
    SUBFINDER = "subfinder"
    DNSX = "dnsx"
    HEXSTRIKE = "hexstrike"
```

`ToolInvocation` es un value object congelado: tool + flags inmutables. **No** lleva
timeout (eso es de 04 §4.2); como mucho referencia conceptual a esa tabla por el `ToolId`.

```python
# backend/src/scans/domain/value_objects/tool_invocation.py
from dataclasses import dataclass

from src.scans.domain.enums.tool_id import ToolId


@dataclass(frozen=True, slots=True)
class ToolInvocation:
    """Una invocación concreta tool+flags que el worker puede entregar al agente.

    Congelado/hashable -> comparable por igualdad en tests (guard byte-identity del
    piso gov/básico contra el set canónico unificado de 01 §3 / 02 §4; ver §10.1).
    Los timeouts y la mecánica de ejecución son de 04-scanning-engine (§4.2); aquí
    solo se nombra la tool y sus flags.
    """

    tool: ToolId
    flags: tuple[str, ...] = ()
```

### 3.2 El mapping declarativo congelado

La whitelist es un mapping de módulo, inmutable en runtime vía `MappingProxyType` sobre
tuplas congeladas. **Allow-list por construcción:** lo que no está en la tupla de una
celda literalmente nunca llega al agente.

> **Flags LÓGICOS, no literales (02 = política, 04 = ejecutor):** los flags congelados
> en estas tuplas (p. ej. los de `_BASIC_GOV`) son **declarativos** — definen *qué*
> significa el toolset por `(is_gov, level)` —, **no** el argv literal que se ejecuta en
> runtime. La mecánica de ejecución de [04](../04-scanning-engine/spec.md) añade flags
> operativos en cada corrida (p. ej. `-duc`, disable update check; ver 04 §7). Por tanto
> los flags congelados aquí en 02 **≠** los flags exactos que ejecuta 04: consúmase 02
> como la **política** y 04 como el **ejecutor**.

```python
# backend/src/scans/application/whitelist/toolset_whitelist.py
from types import MappingProxyType

from src.common.domain.enums.scans import ScanLevel  # propiedad de 06
from src.scans.domain.enums.tool_id import ToolId
from src.scans.domain.value_objects.tool_invocation import ToolInvocation

TI = ToolInvocation

# --- Capa BÁSICO general (no-gov), pasiva sobre la raíz (spec §3.1) ---
_BASIC_NON_GOV: tuple[ToolInvocation, ...] = (
    TI(ToolId.WHATWEB, ("--root",)),
    TI(ToolId.TESTSSL, ("--root",)),
    TI(ToolId.SECURITY_HEADERS, ("--root",)),
    TI(ToolId.NUCLEI, ("-tags", "exposures,misconfiguration,ssl,tech,dns",
                       "-etags", "intrusive,dos,fuzzing,network", "-no-spider")),
    TI(ToolId.SUBFINDER, ("-passive",)),
    TI(ToolId.DNSX, ("-passive",)),
)

# --- Celda GOV/BÁSICO: PISO LEGAL. ---
# Set de tags Nuclei CANÓNICO UNIFICADO en 01 §3 y 02 §4:
#   -tags exposures,misconfiguration,ssl,tech,dns  (idéntico al básico general, §3.1)
# Esta celda es byte-equivalente al piso legal de 01 §3 (los dos specs concuerdan;
# el inválido http-misconfig quedó eliminado). El test §10.1 asserta exactamente
# este set.
# Diferencias vs no-gov: sin subfinder/dnsx recon, sin spider; ZAP spider + katana
# AUSENTES por construcción (no respetan robots.txt -> ilegales para gov pasivo).
_BASIC_GOV: tuple[ToolInvocation, ...] = (
    TI(ToolId.TESTSSL, ("--root",)),
    TI(ToolId.SECURITY_HEADERS, ("--root",)),
    TI(ToolId.WHATWEB, ("--root",)),
    # set canónico unificado (01 §3 == 02 §4 == básico general §3.1)
    TI(ToolId.NUCLEI, ("-tags", "exposures,misconfiguration,ssl,tech,dns",
                       "-etags", "intrusive,dos,fuzzing,network", "-no-spider")),
)

# --- Delta INTERMEDIO (activo suave, rate-limited; spec §3.2) ---
# Cobertura de items del spec §3.2 que NO llevan ToolId propio:
#   - "Checks CORS / cookie / clickjacking" -> los entrega ZAP_BASELINE (reglas
#     pasivas de ZAP) + los tags de misconfig de Nuclei; NO necesitan invocación
#     aparte (no se omiten, quedan subsumidos — confirmar contra 04 al parsear).
#   - "ffuf / gobuster" (dir enum): el spec ofrece AMBAS como alternativas; se elige
#     FFUF como la herramienta canónica del dir-enum ligero. gobuster NO se añade
#     (una sola tool cubre el item; reintroducible vía 04 si hiciera falta).
_INTERMEDIATE_DELTA: tuple[ToolInvocation, ...] = (
    TI(ToolId.ZAP_BASELINE, ()),                          # spider + scan pasivo de ZAP (cubre CORS/cookie/clickjacking)
    TI(ToolId.NUCLEI, ("-tags", "cve,default-logins")),  # full, bajo riesgo
    TI(ToolId.NIKTO, ()),
    TI(ToolId.KATANA, ()),                                # crawl
    TI(ToolId.FFUF, ()),                                  # dir enum ligero (alternativa a gobuster, spec §3.2)
)

# --- Delta AVANZADO (explotación acotada; spec §3.3 / §6). hexstrike NO va aquí. ---
# Reconciliación §3.3 vs §6: el spec §3.3 / la tabla §3 listan también "pruebas de
# auth", PERO el spec §6 acota la batería GARANTIZADA del avanzado a exactamente
# tres tools (ZAP full active + Nuclei fuzzing + sqlmap). Se honra §6 (el alcance
# vinculante): "pruebas de auth" se considera CUBIERTA por las reglas de
# autenticación/sesión del ZAP full active scan y NO recibe ToolId propio. Es un
# recorte deliberado de reconciliación, no un olvido (ver §7 y §11).
_ADVANCED_DELTA: tuple[ToolInvocation, ...] = (
    TI(ToolId.ZAP_FULL_ACTIVE, ()),         # incl. checks de auth/sesión (spec §3.3 "pruebas de auth")
    TI(ToolId.NUCLEI, ("-fuzzing-templates",)),
    TI(ToolId.SQLMAP, ("--single-param",)),  # sobre 1 param conocido (spec §6)
)

# Acumulación cumulativa: básico ⊂ intermedio ⊂ avanzado. El `+` del spec §3 es DATA.
_INTERMEDIATE_NON_GOV = _BASIC_NON_GOV + _INTERMEDIATE_DELTA
_ADVANCED_NON_GOV = _INTERMEDIATE_NON_GOV + _ADVANCED_DELTA
_INTERMEDIATE_GOV = _BASIC_GOV + _INTERMEDIATE_DELTA
_ADVANCED_GOV = _INTERMEDIATE_GOV + _ADVANCED_DELTA

TOOLSET_WHITELIST: "MappingProxyType[tuple[bool, ScanLevel], tuple[ToolInvocation, ...]]" = (
    MappingProxyType({
        (False, ScanLevel.BASICO): _BASIC_NON_GOV,
        (False, ScanLevel.INTERMEDIO): _INTERMEDIATE_NON_GOV,
        (False, ScanLevel.AVANZADO): _ADVANCED_NON_GOV,
        (True, ScanLevel.BASICO): _BASIC_GOV,
        (True, ScanLevel.INTERMEDIO): _INTERMEDIATE_GOV,
        (True, ScanLevel.AVANZADO): _ADVANCED_GOV,
    })
)

# hexstrike: solo se AÑADE en el resolver tras pasar flag+healthcheck (§7). Default ausente.
HEXSTRIKE_INVOCATION = TI(ToolId.HEXSTRIKE, ())

# Perfil demo: NO es una clave del mapping indexado por nivel (no es un 4º nivel). Ver §8.
DEMO_PROFILE: tuple[ToolInvocation, ...] = (
    TI(ToolId.NUCLEI, ("-tags", "ssl,tech,exposures", "-no-spider")),  # subset rápido
    TI(ToolId.TESTSSL, ("--fast",)),
    # La sonda agéntica "1 probe contra el bot propio" es de 03-agentic-surface (cross-ref).
)
```

> **Cross-ref crítico:** la celda `_BASIC_GOV` es el **piso legal** de
> [01-legal-ethics](../01-legal-ethics/spec.md) §3 y es **byte-equivalente** a él: 01
> §3 y 02 §4 fijan **el mismo** set de tags Nuclei canónico
> (`exposures,misconfiguration,ssl,tech,dns`, idéntico al básico general §3.1); los dos
> specs están **unificados** (el inválido `http-misconfig` quedó eliminado). El test de
> §10.1 asserta contra ese set único. Nota de ownership: este `_BASIC_GOV` es la
> **expresión declarativa** de la política de 02; la **estructura de datos congelada**
> que el worker materializa y el drop point del enforcement son de
> [04-scanning-engine](../04-scanning-engine/spec.md) (cross-ref, no se redefine aquí).

### 3.3 El resolver puro

Una sola función pura, sin I/O, es el **único** seam consumido por 01 (scheduler) y 05
(construcción de `owasp_agent`). El estado del healthcheck de hexstrike se **pasa como
argumento** (no se hace I/O dentro) para mantenerla pura y testeable.

```python
# backend/src/scans/application/whitelist/resolve_toolset.py
from src.scans.application.whitelist.toolset_whitelist import (
    DEMO_PROFILE,
    HEXSTRIKE_INVOCATION,
    TOOLSET_WHITELIST,
)
from src.common.domain.enums.scans import ScanLevel  # propiedad de 06
from src.scans.domain.value_objects.tool_invocation import ToolInvocation


def resolve_toolset(
    is_gov: bool,
    level: ScanLevel,
    *,
    demo: bool = False,
    hexstrike_ok: bool = False,
) -> tuple[ToolInvocation, ...]:
    """Única fuente de verdad de qué tools web puede recibir owasp_agent.

    - demo=True corta-circuito y devuelve DEMO_PROFILE, IGNORANDO el nivel
      (demo es ortogonal al nivel; ver §8). is_gov tampoco aplica (demo = localhost).
    - hexstrike solo se añade en avanzado si ENABLE_HEXSTRIKE && healthcheck OK
      (hexstrike_ok). Por defecto cae al fallback ZAP full + Nuclei fuzzing + sqlmap.
    - Allow-list por construcción: lo no presente en la celda no se ejecuta.
    """
    if demo:
        return DEMO_PROFILE

    toolset = TOOLSET_WHITELIST[(is_gov, level)]

    if level is ScanLevel.AVANZADO and hexstrike_ok:
        toolset = toolset + (HEXSTRIKE_INVOCATION,)

    return toolset
```

`hexstrike_ok` lo calcula el `ScanHandler` como `settings.ENABLE_HEXSTRIKE and
<healthcheck cacheado>`. **Importante:** el `ctx` del worker (`config/tasks.py`) **no
llega al handler** — `CommandHandler.execute(self, command)`
(`src/common/domain/buses/commands.py`) recibe **solo** el command, sin `ctx`. Por
tanto el estado del healthcheck **no** se lee de `ctx` dentro del handler; se le
**inyecta por constructor** en `scans_wiring` desde una caché de módulo poblada en el
`startup` del worker (ver §5 y §9 paso 9). La definición del flag `ENABLE_HEXSTRIKE`,
el healthcheck al arrancar y la semántica de fallback son **propiedad de
[04](../04-scanning-engine/spec.md) §10**; 02 solo consume el booleano resultante.

---

## 4. Niveles acumulativos (básico ⊂ intermedio ⊂ avanzado)

La escalera del spec §3 se modela como **concatenación de tuplas**, no como ramas: el
`+` de la tabla del spec es literalmente data (§3.2 arriba). Cada nivel es el anterior
**más** su delta:

| Nivel | Composición | Notas de budget |
|---|---|---|
| **básico** | `_BASIC_*` (pasivo: TLS, headers, fingerprint, Nuclei pasivo, recon DNS passive) | cierra **<90s/sitio** (presupuesto operativo que protege el seed gov; concurrencia es de [04](../04-scanning-engine/spec.md) §4.1) |
| **intermedio** | básico `+` `_INTERMEDIATE_DELTA` (ZAP baseline, Nuclei CVE/default-logins, Nikto, katana, ffuf) | activo suave, rate-limited (límites en 01 / 04) |
| **avanzado** | intermedio `+` `_ADVANCED_DELTA` (ZAP full active, Nuclei fuzzing, sqlmap 1 param) | budget global **~8 min** (watchdog en [04](../04-scanning-engine/spec.md)) |

El resolver devuelve una tupla **ordenada**; 04 puede paralelizarla con `asyncio.gather`.
El `<90s` del básico y el `~8 min` del avanzado son números **propios de 02** que
alimentan el watchdog de 04 (no se redefine la mecánica del watchdog aquí).

---

## 5. Enforcement defense-in-depth

Tres puertas independientes hacen que un activo automático sea **estructuralmente
imposible**, sin que el LLM sea nunca el punto de enforcement:

1. **Scheduler (01, upstream):** el seed/cron gov registrado en
   `worker_settings["cron_jobs"]` (`backend/config/tasks.py`, hoy `[]`) **hard-codea**
   `level=ScanLevel.BASICO` al encolar el `ScanCommand`. No puede emitir otro nivel.
   (Propiedad de [01](../01-legal-ethics/spec.md) §2.2; aquí solo se cross-refiere el seam.)

2. **Construcción del agente (este feature, seam de 05):** dentro del `ScanHandler`,
   **antes** de llamar `orchestrator.run(url, level)` ([05](../05-agent-team/spec.md) §5
   paso 2), el worker:
   - deriva `is_gov` de la fila del sitio (06),
   - llama `resolve_toolset(is_gov, scan.level, demo=..., hexstrike_ok=...)`,
   - construye `owasp_agent` con `tools=` poblado **solo** desde la tupla resuelta
     (mapeando cada `ToolId` a su `run_*` de 05).

   En el camino automático gov/básico el agente literalmente **no recibe tools activas**;
   no puede elegir lo que no tiene. Aquí 02 aporta el **contrato lógico** (la llamada a
   `resolve_toolset` + el filtro `tools=`); el **drop point** runtime donde se descartan
   las tools no permitidas antes de que `owasp_agent` las reciba es el **enforcement de
   [04](../04-scanning-engine/spec.md)** (cross-ref). hexstrike se cae en este seam si el
   flag está off o el healthcheck falló.

   ```python
   # backend/src/scans/application/command/scan_handler.py  (cuerpo compartido con 05)
   # CommandHandler de application (convención del repo: tenants/users/messaging
   # ponen sus handlers en application/command(s)/, NUNCA en infrastructure).
   # self.hexstrike_healthy y self.site_repository se inyectan por constructor en
   # scans_wiring (NO hay `ctx` aquí: execute(self, command) solo recibe el command).
   site = await self.site_repository.get(command.site_id)   # lee is_gov de la fila (06)
   resolved = resolve_toolset(
       is_gov=site.is_gov,
       level=command.level,
       demo=command.demo,
       hexstrike_ok=settings.ENABLE_HEXSTRIKE and self.hexstrike_healthy,
   )
   owasp_agent = build_owasp_agent(tools=[TOOL_FUNCTIONS[ti.tool] for ti in resolved])
   # ... orchestrator.run(url, command.level)  <-- firma y Team son de 05 (cross-ref)
   ```

3. **Frontera de ejecución (04):** opcionalmente, `run_tool`/`subprocess` de 04 puede
   re-verificar la pertenencia a `resolved` antes de invocar (guard de cinturón-y-tirantes).
   La mecánica es de 04; 02 solo expone `resolved` como contrato.

> Ownership del cuerpo del `ScanHandler`: la **orquestación Agno** (Team, paso de tools,
> manejo de fallos parciales) es de [05](../05-agent-team/spec.md). Este feature contribuye
> **solo** la llamada a `resolve_toolset` y el filtro `tools=`. El registro SAQ
> (`ScanCommand`/`ScanHandler`) se cablea como `ExampleJobCommand`/`ExampleJobHandler`
> (detalle exacto de archivos, contrato `Command(ABC)` y wiring en §9 paso 7).
>
> **`ScanCommand` — contrato obligatorio** (mirror de `ExampleJobCommand` en
> `src/common/application/commands/common.py`): es un `@dataclass` que subclasa
> `Command(ABC)` (`src/common/domain/buses/commands.py`) e **implementa
> obligatoriamente** la `@property to_dict` (vía `asdict(self)`) y el classmethod
> `from_dict(cls, kwargs)` — sin ellos `AsyncTaskResolver` no puede serializar /
> rehidratar el command a través de la frontera SAQ. Campos mínimos: `site_id`
> (para que el handler lea `is_gov`), `level: ScanLevel`, `demo: bool = False`
> (más lo que 05/06 requieran). `ScanLevel` es `BaseEnum` con valor `str`, así que
> serializa directo; si se añadiera algún campo no primitivo necesitaría `to_dict`
> custom (cf. `PublishStreamEventCommand`).
>
> **Productor / entry point de `ScanCommand`:** quién construye y encola el command
> (`POST /scans`: de dónde salen `level` y `demo` de la request, gate de atestación)
> es de [12-api](../12-api/spec.md) sobre el modelo de [06](../06-data-model/spec.md);
> el patrón de enqueue a imitar es
> `src/admin/presentation/endpoints/enqueue_example_job.py`
> (`command_bus.dispatch(cmd, run_async=True)`). 02 **no** define ese endpoint; solo
> consume el `ScanCommand` ya encolado dentro del handler.

---

## 6. Manejo de `robots.txt`

Antes de **cualquier** request web del subagente OWASP se parsea y honra `robots.txt`
del host, con el UA identificable `Owliver-Scanner/1.0 (+contacto)`
(`settings.SCANNER_USER_AGENT`; política de UA y rate-limit son de
[01](../01-legal-ethics/spec.md)). Obligatorio en el camino gov/pasivo (parte de la
definición legal de "pasivo") y default del recon ligero del básico.

```python
# backend/src/scans/domain/services/robots_policy.py
from abc import ABC, abstractmethod


class RobotsPolicy(ABC):
    @abstractmethod
    async def is_allowed(self, url: str) -> bool:
        """True si robots.txt del host permite a Owliver-Scanner/1.0 acceder a url."""
```

```python
# backend/src/scans/infrastructure/services/urllib_robots_policy.py
import urllib.robotparser
from urllib.parse import urljoin, urlparse

from src.common.settings import settings
from src.scans.domain.services.robots_policy import RobotsPolicy


class UrllibRobotsPolicy(RobotsPolicy):
    async def is_allowed(self, url: str) -> bool:
        base = urlparse(url)
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(urljoin(f"{base.scheme}://{base.netloc}", "/robots.txt"))
        rp.read()  # la mecánica de fetch/egress final la gobierna 04 (cross-ref)
        return rp.can_fetch(settings.SCANNER_USER_AGENT, url)
```

> **DI obligatoria (sin esto la interfaz es código muerto):** como cualquier servicio
> de dominio del repo (cf. `TokenService` → `JwtTokenService` en
> `src/common/infrastructure/domain_builder.py` / `DomainContext`), la impl
> `UrllibRobotsPolicy` debe **construirse y exponerse** para que el handler la obtenga.
> Dos opciones consistentes con el codebase: (a) añadir `robots_policy: RobotsPolicy`
> a `DomainContext` y construirla en `build_async_domain`, o (b) inyectarla por
> constructor del `ScanHandler` en `scans_wiring` (igual que se inyecta el
> healthcheck de hexstrike). El plan usa (b) por mantener `RobotsPolicy` dentro del
> módulo `scans`; en cualquier caso **debe** quedar cableada explícitamente en §9.

> **Decisión abierta (no resuelta unilateralmente aquí):** ni 01 ni 02 fijan si el
> camino **activo** no-gov (intermedio/avanzado tras el gate) debe honrar `robots.txt`
> en sus crawlers (ZAP/katana/ffuf). Esta plan **honra robots para la subcapa pasiva
> básica** (siempre presente por acumulación) y **marca como pregunta abierta** el
> comportamiento de los crawlers activos, a resolver entre 01/02/03 — no se decide dentro
> de 02. ZAP spider + katana ya están **ausentes por construcción** en toda celda gov.

---

## 7. Alcance avanzado (sin hexstrike)

La batería garantizada del avanzado (spec §6) es **ZAP full active + Nuclei fuzzing +
sqlmap sobre 1 param**, dentro del budget ~8 min (watchdog y timeouts por tool en
[04](../04-scanning-engine/spec.md) §4.2/§10). Está modelada en `_ADVANCED_DELTA` (§3.2).

**hexstrike está recortado a CERO desde el inicio** y **ausente de toda celda por
defecto**. El flag `ENABLE_HEXSTRIKE`, el **healthcheck al arrancar el worker** y la
**semántica de fallback** son **propiedad de [04](../04-scanning-engine/spec.md)
§10** (no se redefinen aquí). El **único seam que 02 posee** es: `resolve_toolset`
añade `HEXSTRIKE_INVOCATION` **si y solo si** recibe `hexstrike_ok=True`. Ese booleano
lo calcula el `ScanHandler` como `settings.ENABLE_HEXSTRIKE and <healthcheck cacheado>`
(el healthcheck se le **inyecta por constructor**, no vive en `ctx`; ver §3.3 y §9
paso 9). Si `hexstrike_ok=False`, el resolver **no** añade la tool: `owasp_agent`
nunca la recibe y el avanzado cae al fallback de 3 tools. El avanzado **jamás** depende
de hexstrike para producir findings.

---

## 8. Perfil demo vs. budget global

Son **dos presupuestos distintos** que el código mantiene separados:

- **Budget global ~8 min** (`SCAN_GLOBAL_BUDGET_SECONDS=480`) — comportamiento real del
  avanzado. Enforcement (watchdog) en 04.
- **Perfil demo <90s** (`DEMO_PROFILE_TIMEOUT_SECONDS`, ~60–90s) — perfil **curado y
  ortogonal al nivel**, NO un 4º nivel (06 confirma que no hay columna `demo`).

Representación: un parámetro booleano `demo` en `ScanCommand` (no un valor de
`ScanLevel`), y la constante separada `DEMO_PROFILE` que **no es clave** del mapping
indexado por nivel. `resolve_toolset(..., demo=True)` corta-circuito y devuelve
`DEMO_PROFILE` **ignorando el nivel** (asserción explícita en tests, §10). Su batería:
Nuclei subset + testssl + (la sonda "1 probe contra el bot propio" es de
[03](../03-agentic-surface/spec.md)).

Lo pesado (ZAP full active, garak) se **pre-hornea desde fixtures** vía el patrón de seed
existente (`backend/scripts/seed_*.py`, overview en `product/spec.md` §17), nunca en vivo,
y solo contra **targets localhost** (OWASP Juice Shop / DVWA / bot propio), **nunca**
`.gob.mx` en vivo.

---

## 9. Pasos de implementación (orden de construcción)

> **Bloqueante upstream:** [06-data-model](../06-data-model/plan.md) debe crear primero
> `src/common/domain/enums/scans.py` (`ScanLevel`, `BaseEnum`; ver 06 §2.1), los módulos
> `src/sites/` y `src/scans/` (entidades `sites`/`scans`, contrato `Finding`) y la
> migración. Este feature **importa** `ScanLevel` desde `src.common.domain.enums.scans`
> y **lee** `sites.is_gov` vía el `SiteRepository` de 06.

1. **Settings** — añadir en `backend/src/common/settings.py` (UPPER_SNAKE, tipados):
   ```python
   ENABLE_HEXSTRIKE: bool = False
   SCAN_GLOBAL_BUDGET_SECONDS: int = 480
   DEMO_PROFILE_TIMEOUT_SECONDS: int = 90
   SCANNER_USER_AGENT: str = "Owliver-Scanner/1.0 (+contacto)"
   ```
   (Los timeouts por tool son de 04; budget/demo/UA son de 02.)
2. **`backend/src/scans/domain/enums/tool_id.py`** — `ToolId(StrEnum)`.
3. **`backend/src/scans/domain/value_objects/tool_invocation.py`** — `ToolInvocation`
   (`@dataclass(frozen=True, slots=True)`).
4. **`backend/src/scans/application/whitelist/toolset_whitelist.py`** — `TOOLSET_WHITELIST`
   (`MappingProxyType`), deltas cumulativos, `HEXSTRIKE_INVOCATION`, `DEMO_PROFILE`.
5. **`backend/src/scans/application/whitelist/resolve_toolset.py`** — el resolver puro.
6. **`backend/src/scans/domain/services/robots_policy.py`** + impl en
   **`backend/src/scans/infrastructure/services/urllib_robots_policy.py`**, y
   **cablear la impl** (inyección por constructor en `scans_wiring`, o `DomainContext`
   + `build_async_domain` si se prefiere (a) del §6) para que el handler la obtenga.
7. **`ScanCommand`/`ScanHandler`** (cuerpo compartido con 05): mirror de
   `ExampleJobCommand`/`ExampleJobHandler`.
   - (a) **`ScanCommand`** — `@dataclass` que subclasa `Command(ABC)`, con
     `to_dict` (@property, `asdict`) **y** `from_dict` classmethod (obligatorios; ver
     §5). Archivo: `src/scans/application/commands/scan.py` (cross-module import
     permitido: `tasks_mapping` ya importa commands de varios módulos). Campos:
     `site_id`, `level: ScanLevel`, `demo: bool = False`.
   - (b) **`ScanHandler`** — en `src/scans/application/command/scan_handler.py`
     (application, **no** infrastructure — convención del repo). Recibe por
     constructor `site_repository`, `robots_policy` y el healthcheck cacheado.
   - (c) Registrar en `backend/src/common/application/data/tasks_mapping.py`
     (`async_tasks_mapping[ScanCommand.__name__] = ScanCommand`).
   - (d) Crear `scans_wiring(domain, bus)` en
     `backend/src/scans/infrastructure/bus_wiring.py` con
     `bus.command_bus.subscribe(command=ScanCommand, handler=ScanHandler(...))`.
   - (e) **bus_wiring NO se auto-descubre:** importar y **llamar** `scans_wiring` en
     `backend/src/common/infrastructure/bus_builder.py` (junto a `auth_wiring`,
     `messaging_wiring`, `tenants_wiring`, `users_wiring`) **y** en
     `backend/src/common/infrastructure/event_bus.py` (mismo patrón). Sin (e) el
     handler nunca queda suscrito y el worker lanza `NotRegisteredCommand`.
8. **Seam de 05:** llamar `resolve_toolset` en el `ScanHandler` y poblar `tools=` de
   `owasp_agent` (la construcción del Team es de 05; aquí solo el call site).
9. **Healthcheck hexstrike (mecánica 04 §10):** la definición del healthcheck y su
   cacheo al `startup` del worker (`backend/config/tasks.py`) son **de 04**. 02 solo
   consume el booleano: el valor cacheado se **inyecta por constructor** en el
   `ScanHandler` vía `scans_wiring` (NO se lee de `ctx`, que el handler no recibe).
10. **Cron gov (01):** registrar el seed/cron en `worker_settings["cron_jobs"]` con
    `level=ScanLevel.BASICO` hard-coded (propiedad de 01/08; aquí solo se confirma el seam).

**Migraciones:** ninguna propia de este feature (todo lo persistido es de 06).

---

## 10. Pruebas

Todas unit, sobre la función pura y los VO congelados (sin I/O). Ubicación sugerida:
`backend/tests/scans/application/whitelist/`.

1. **Byte-identity gov/básico (guard anti-drift):** este test compara
   `resolve_toolset(True, BASICO)` contra la tupla canónica del piso legal, que es
   **idéntica en 01 §3 y 02 §4** (los dos specs están unificados). Asserta exactamente:
   testssl `--root`, security-headers `--root`, WhatWeb `--root`, Nuclei `-tags
   exposures,misconfiguration,ssl,tech,dns -etags intrusive,dos,fuzzing,network
   -no-spider`. Igualdad por valor gracias al `frozen=True`. El set es el canónico
   acordado por ambos specs (ya no hay misterio de byte-identity contra 01: 01 §3 y 02
   §4 coinciden).
2. **Allow-list negativo:** para `(True, BASICO)` ningún `ToolInvocation` tiene
   `tool in {ZAP_BASELINE, ZAP_FULL_ACTIVE, KATANA, FFUF, SQLMAP, NIKTO}` ni
   `HEXSTRIKE` — lo no listado **no** aparece.
3. **Acumulación:** `set(resolve_toolset(g, BASICO)) ⊆ set(resolve_toolset(g, INTERMEDIO))
   ⊆ set(resolve_toolset(g, AVANZADO))` para `g in {True, False}`.
4. **hexstrike gating:** `AVANZADO` con `hexstrike_ok=False` → fallback sin `HEXSTRIKE`;
   con `hexstrike_ok=True` → contiene `HEXSTRIKE` además del fallback. Default
   (`ENABLE_HEXSTRIKE=False`) nunca lo incluye.
5. **Demo ortogonal al nivel:** `resolve_toolset(g, lvl, demo=True) == DEMO_PROFILE`
   para **todo** `(g, lvl)` (asserción de que demo ignora `level` e `is_gov`).
6. **Inmutabilidad:** intentar mutar `TOOLSET_WHITELIST` lanza `TypeError`
   (`MappingProxyType`).
7. **robots:** `UrllibRobotsPolicy.is_allowed` honra `Disallow` para
   `Owliver-Scanner/1.0`; test con un `robots.txt` fixture (host stub).
8. **Demo timeout:** assert config `DEMO_PROFILE_TIMEOUT_SECONDS <= 90` y distinto de
   `SCAN_GLOBAL_BUDGET_SECONDS` (los dos números nunca se confunden).

La matriz a cubrir es `is_gov × level × demo × hexstrike_ok`; manejable por ser pura.

---

## 11. Riesgos y decisiones abiertas

- **RESUELTO — tags Nuclei del piso gov/básico (01 §3 ↔ 02 §4):** los dos specs están
  **unificados** sobre el mismo set canónico `-tags
  exposures,misconfiguration,ssl,tech,dns` (idéntico al básico general §3.1; el inválido
  `http-misconfig` quedó eliminado). La byte-equivalencia que persigue el guard de §10.1
  es **satisfacible** y `_BASIC_GOV` ya fija ese set; el test §10.1 asserta contra él.
- **RESUELTO — ownership de la whitelist `(is_gov, level)` (split 02 ↔ 04):** **02**
  posee la **política/definición** (el contenido de cada celda por nivel, incl.
  intermedio/avanzado, y el contrato lógico del resolver); **04** posee la **estructura
  de datos concreta** de la whitelist y el **enforcement en el worker** (materialización
  runtime + drop point + ejecución). 01 §3 cross-refiere a 02 para la definición y a 04
  para la estructura+enforcement. El plan modela el resolver (aceptado) y expresa la
  política de 02 de forma declarativa; la forma de datos congelada y el seam de
  enforcement se cross-refieren a [04](../04-scanning-engine/spec.md), no se reclaman aquí.
- **Reconciliación §3.3 ↔ §6 (pruebas de auth):** la tabla §3 / §3.3 listan "pruebas
  de auth" en el avanzado, pero §6 acota la batería **garantizada** a 3 tools. Se honra
  §6: "pruebas de auth" se considera **cubierta por ZAP full active** y **no** recibe
  ToolId propio. Recorte deliberado, documentado (no un olvido).
- **Flags exactos de Nuclei (no-warming):** no se añade `-duc` ni otros flags de
  "template warming" a la celda gov/básico — eso es mecánica de ejecución de
  [04](../04-scanning-engine/spec.md), no parte del piso legal.
- **Orden de módulos:** 06 es bloqueante (provee `ScanLevel`, `scans`/`sites`, `Finding`).
  *Mitigación:* el plan declara la dependencia; hasta entonces se acuerda la ruta de import.
- **Ownership del `ScanHandler`:** su cuerpo es compartido con [05](../05-agent-team/spec.md).
  *Pendiente:* confirmar con 05 que 02 contribuye solo el call site de `resolve_toolset` +
  el filtro `tools=`, y dónde se registra físicamente el cron seed con `level=basico` (01/08).
- **Robots en camino activo:** comportamiento de crawlers activos (ZAP/katana/ffuf) bajo
  scan atestado no está fijado por ningún spec (ver §6). **Marcado como pregunta abierta**
  para resolución cross-spec 01/02/03; **no** se decide unilateralmente en 02.
- **Acoplamiento resolver↔healthcheck:** mitigado pasando `hexstrike_ok` como argumento
  (sin I/O en la función pura).
- **Naming SAQ vs Arq:** specs 04/05 mencionan "Arq" pero el código usa **SAQ**
  (`backend/config/tasks.py`, `saq.Queue`). Este plan asume SAQ; drift a resolver en 04/05.
- **`max_jobs=1` vs `<90s` del básico:** el básico depende de concurrencia intra-scan
  (`asyncio.gather` sobre tools), **propiedad de [04](../04-scanning-engine/spec.md) §4.1**;
  02 solo asevera el target `<90s` y devuelve una tupla ordenada que 04 puede fan-out.
