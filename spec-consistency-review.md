# Revisión de consistencia — `spec.md`

> Auditoría interna de `spec.md` (1011 líneas, §1–§17). Método: 6 agentes de
> auditoría (referencias cruzadas, modelo de datos, numérica, tooling,
> terminología, lógica de flujo) + verificación adversarial por hallazgo.
> 28 hallazgos crudos → **24 confirmados** → deduplicados a **14 issues**.
> Fecha: 2026-06-20.

> **Estado: APLICADO (2026-06-20).** Los 14 issues se corrigieron en `spec.md`.
> Decisiones tomadas al aplicar: (A3) el nivel **"avanzado" = ZAP full active +
> Nuclei fuzzing + sqlmap** bajo el **budget global ~8 min**, y el `<90s` queda
> reservado al **perfil demo** (que pre-hornea lo pesado); (A2) se añadió un
> **watchdog** que aborta las tools restantes al agotar el budget + se declaró
> ejecución **concurrente** de las tools del básico. Caveats menores: **gobuster**
> (#15, BAJA) se deja como alternativa documentada — `run_ffuf` es la
> implementación cableada; **B5** (Team/`asyncio.gather`) se aclaró con una nota
> en el flujo del worker, sin reescribir el modelo de ejecución.

El documento es, en lo sustancial, coherente: las decisiones de arquitectura, el
modelo de scoring, los enums (`scan_events.type`, `agentic_status`,
`scans.status`) y el `dedupe_key` están alineados entre §6/§7/§8/§9/§12. Los
problemas son **referencias obsoletas, contradicciones de tooling/timing entre
secciones, y un par de contratos sin definir**. Ninguno invalida el diseño; todos
son arreglables con ediciones puntuales.

---

## ALTA prioridad

### A1 · Referencias cruzadas colgadas/obsoletas (sistémico)
El doc usa la convención `§N.M` correctamente en prosa (§9.1, §11.3, §12.1, §14.x)
**pero** arrastra paréntesis sueltos `(N.M)` de un esquema de numeración previo (o
del "análisis de huecos" externo). Ninguno resuelve:

| Ref escrita | Ubicación | Debe apuntar a |
|---|---|---|
| `(6.6)` | §7 L430, L446 | §12.1 (live-view persistencia/replay) |
| `(6.8)` | §7 L434 · §8 L512 `(ver §6.8/§9)` | §9.2 (cobertura parcial) |
| `(2.6)` | §7 L438 | §9.1 (`agentic_status` 3 estados) |
| `(6.7)` | §7 L439 | §9.4 (orden/desempate por `penalty_raw`) |
| `(6.2)` | §7 L458 | §14.1 (canje del magic-link) |
| `(4.1)` | §7 L462 | §12.1 (live-view persistencia obligatoria) |
| `(§17.3)` | §4 L128 | §17, guion paso 3 (no hay §17.3) |
| `§6.1 del análisis de huecos` | §12.1 L745 | doc **externo** citado inline → §5/§10/§15 (fixtures) |

§6 e §17 **no tienen subsecciones numeradas**, así que `§6.x`/`§17.3` nunca
resuelven. **Fix:** reemplazar cada paréntesis por la sección real en formato
`§N.M`; quitar la cita al doc externo.

### A2 · Time-boxes vs. timeouts por herramienta sin mecanismo de corte
Los time-boxes declarados no son honrables con los timeouts duros del §5, y el
spec **nunca** define (a) concurrencia de tools dentro de un subagente ni (b) un
watchdog que aborte la batería al agotar el budget. El único control entre tools
es el **flag manual de cancel** (§6 L380):
- §4 L88 ata "**<90s**" a "**ZAP full active**", cuyo timeout duro es **240s** (§5).
- §5 L254 "básico debe cerrar en **<90s**" vs. suma serial de tools básicos ≈ **270s**
  (nuclei 90 + testssl 60 + whatweb 30 + sec-headers 30 + subfinder/dnsx 60).
- "budget global ~8 min" (480s) vs. peor caso avanzado serial (ZAP full 240 +
  sqlmap 120 + nuclei 90 + …).

**Fix:** declarar explícitamente o (i) concurrencia de tools + watchdog que aborta
al vencer el budget/time-box, o (ii) timeouts reducidos en modo avanzado/demo
(p.ej. ZAP 60s, sqlmap 20s), y reservar "<90s" para el **perfil demo** (que ya
pre-hornea lo pesado, §11/§16/§17).

### A3 · Variante de ZAP para "avanzado" contradictoria
- §4 L88 y §13 L790: avanzado = **ZAP full active** + Nuclei fuzzing + sqlmap.
- §15 L961 y §16 L985: avanzado = **ZAP baseline** + Nuclei subset + sqlmap.

Son scanners distintos (240s vs 120s; activo-explotación vs activo-suave): cambia
budget e intrusividad. **Fix:** elegir una variante y usarla en §4/§13/§15/§16
(baseline es la compatible con el time-box).

### A4 · `AgenticResult` declarado contrato hora-0 pero nunca definido
§15 artefacto #1 (L920) congela `Finding` **+ `AgenticResult`** en `finding.py`
como contrato entre P2/P3/P4. Pero §6 (único lugar con clases Pydantic) y §8 solo
definen `Finding`. Tres de cuatro carriles dependen de un shape inexistente.
**Fix:** definir `AgenticResult` en §6 (campos implícitos: vendor/type/location_url
+ `{payload, respuesta_cruda, veredicto, reason}` + `agentic_status`), o eliminarlo
de §15 si los outputs agénticos son solo `Finding` + filas de `agentic_surface`.

### A5 · Diagrama de arquitectura (§5) desactualizado vs. el cuerpo
El ASCII del §5 contradice tres decisiones del texto:
- Caja agéntica = "**crawl+garak**" → pero §4 dice que la base es el **puente
  Playwright propio** y garak/promptfoo son fallback opcional frágil.
- Caja OWASP = "scanners Docker **+ hexstrike**" → pero §13/§15 lo **recortan a
  CERO desde el inicio** (feature-flag default OFF).
- Caja Opus = "**merge+score**+reporte" → pero §6/§9 insisten en que merge/dedup/
  scoring es **Python determinista, NO el LLM**; Opus solo redacta el resumen.

**Fix:** redibujar las cajas (agéntico = "crawl + puente Playwright + juez
(garak opcional)"; OWASP = "scanners (hexstrike opcional, default OFF)"; mover
"merge+score (Python)" a su propia etapa antes de Postgres).

---

## MEDIA prioridad

### M1 · Lista `tools=[...]` del `owasp_agent` (§6) incompleta
Faltan herramientas que §4/§5/§13 sí usan en básico:
- **security-headers/Observatory** — es uno de los **3 parsers prioritarios** (§6) y
  el comentario del pseudocódigo nombra `run_security_headers`, pero no está en la
  lista. El básico + ranking gov dependen de él.
- **subfinder/dnsx** — recon pasivo del básico, con fila propia en §5 y en §13.
- **gobuster** — pareado con ffuf en §4/§5/§13 pero solo existe `run_ffuf`.

La lista es claramente un subconjunto ilustrativo, pero conviene completarla o
anotar que el recon DNS corre fuera del agente. **Fix:** añadir
`run_security_headers` (y `run_subfinder`) a la lista del §6, o marcar la lista
como no-exhaustiva.

### M2 · `rq-scheduler` propuesto mientras la cola es Arq
§12 (swing #1) propone "APScheduler / **rq-scheduler**", pero la cola está fijada
como **Arq** ("no RQ", §15 L926; §14.3). `rq-scheduler` pertenece al ecosistema RQ
que el spec rechaza. **Fix:** usar el cron nativo de Arq (o solo APScheduler).

### M3 · El demo depende de PDF/share, pero es recortable sin Plan B
§17 guion paso 4 exhibe **export PDF + link público `/r/{token}`**. Pero §15 lo
lista **3º en el orden de recorte** ("PDF/share") y **no** está en "nunca se
corta"; el Plan B (§17) no cubre su ausencia (sí cubre live-view, bot, egress).
**Fix:** añadir PDF/share a "nunca se corta", o agregar una entrada de Plan B
(p.ej. "mostrar la página in-app del reporte con la redacción de exploits ahí").

### M4 · `juice-shop` sin definir como target web separado
§17 paso 2 escribe "**bot propio plantado / juice-shop en localhost**". El término
"juice-shop" aparece **una sola vez** y no se define; OWASP Juice Shop es una web
vulnerable, **no** un chatbot, así que no puede producir el finding agéntico
estrella (canary). El "/" lo confunde con el bot. Dado "los 2 subagentes" y
"targets" (plural) en §16/§17, parece el **target web** del subagente OWASP.
**Fix:** nombrarlo explícitamente como target web separado, no slasheado al bot.

---

## BAJA prioridad

- **B1 · Orden del leaderboard** se escribe `(overall_grade ASC, penalty_raw DESC)`
  en §9.4/§10 pero `(grade asc, penalty_raw desc)` en §16/§17. `grade` no es el
  nombre real de la columna. **Fix:** usar `overall_grade` y el mismo casing en todos.
- **B2 · `POST /scans` código de éxito ambiguo:** §14.3/§14.5 reservan **200** para
  el hit idempotente, pero nunca dan el código de la creación nueva (¿201/202?).
  L816 solo dice "encola, devuelve scan_id". **Fix:** declarar 201/202 para creación.
- **B3 · `DELETE /watchlist/{id}`:** no dice si `{id}` es el id de fila de
  `watchlist` o el `site_id`; `POST /watchlist` no documenta qué id devuelve.
  **Fix:** especificar el identificador en §14.4.
- **B4 · Autoridad de selección de tools (nit de redacción):** §6 instruye al
  subagente "Decide SOLO qué tools correr" pero el flujo paso 2 dice "el
  orquestador coordina qué tools dispara cada subagente". El resto del §6 deja
  claro que decide el subagente. **Fix:** reformular paso 2 ("el orquestador delega
  {url, level}; cada subagente elige sus tools").
- **B5 · `Team(mode="coordinate")` vs `asyncio.gather`** (fidelidad de librería, no
  inconsistencia interna): la delegación en coordinate-mode la conduce el LLM
  coordinador, no un `asyncio.gather` literal de los miembros. **Fix opcional:**
  aclarar dónde ocurre el fan-out real, o suavizar el framing "coordinate".

---

## Resumen

| Severidad | Issues |
|---|---|
| Alta | A1 refs colgadas · A2 time-box vs timeouts · A3 variante ZAP · A4 `AgenticResult` sin definir · A5 diagrama obsoleto |
| Media | M1 tools list incompleta · M2 rq-scheduler vs Arq · M3 PDF/share sin Plan B · M4 juice-shop |
| Baja | B1 orden leaderboard · B2 código POST /scans · B3 DELETE watchlist · B4 autoridad tools · B5 Team/gather |

Lo más urgente para un handoff sin sorpresas: **A1** (las refs rompen la
navegación), **A2/A3** (timing irrealizable como está escrito) y **A4** (contrato
hora-0 fantasma que rompería a 3 carriles).
