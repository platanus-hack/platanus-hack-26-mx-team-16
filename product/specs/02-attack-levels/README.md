---
feature: attack-levels
type: spec
status: pending
coverage: 0
audited: 2026-06-20
sources: spec.md §4 (intro + "Subagente OWASP (Web)"), §17; spec-gaps.md §1.4, §1.5, §1.6, §7.1
---

# Owliver — Niveles de ataque y subagente OWASP (web)

> Owliver define **tres niveles de intrusividad creciente** (básico/pasivo, intermedio, avanzado) que se aplican **sobre cualquier URL**, sin verificación de propiedad del dominio. Cada nivel determina exactamente qué herramientas y flags ejecuta el **subagente OWASP (web)**. Este documento es la fuente de verdad para esa batería web: qué corre cada nivel, la whitelist de herramientas+flags por `(is_gov, level)` que el worker debe imponer, el manejo de `robots.txt`, y el alcance del power-up "avanzado". La superficie agéntica (chatbots/LLM), las mecánicas de ejecución (Docker, timeouts) y la orquestación viven en subspecs hermanas.

## 1. Alcance y límites de este documento

Este subspec es **dueño** de:

- La definición normativa de los **tres niveles** (básico/pasivo, intermedio, avanzado) como intrusividad creciente.
- **Exactamente qué herramientas y flags** ejecuta el subagente OWASP web en cada nivel.
- El **alcance (scope) del subagente OWASP web**.
- La **whitelist `(is_gov, level)`** que el worker impone como enforcement, incluyendo `.gob.mx`.
- El manejo de **`robots.txt`**.
- El alcance del power-up del nivel **avanzado** (qué SÍ y qué NO entra).

Lo que **NO** define aquí (resumen de una línea + cross-ref):

- **Niveles y comportamiento del subagente agéntico** (sondas por nivel, caps de payloads, banco de payloads, LLM-juez) → ver [03-agentic-surface](../03-agentic-surface/README.md).
- **Mecánica de ejecución de herramientas** (imagen `scanners`, `subprocess` vs socket Docker, watchdog, timeouts por tool, budget global, red de egress, parsers de salida → `Finding[]`) → ver [04-scanning-engine](../04-scanning-engine/README.md).
- **El Team Agno que orquesta** (coordinador Opus + 2 subagentes Sonnet, qué tools recibe cada agente por nivel) → ver [05-agent-team](../05-agent-team/README.md).
- **Gate de atestación, postura legal, escaneos automáticos = solo pasivos** → ver [01-legal-ethics](../01-legal-ethics/README.md).

Visión y decisiones de arquitectura transversales: ver spec.md (overview).

## 2. Modelo de niveles: intrusividad creciente sobre cualquier URL

Los tres niveles forman una escalera de **intrusividad creciente sobre cualquier URL**, sin verificación de propiedad del dominio (como tampoco la exigen ZAP, Burp o Nuclei). El modo activo (intermedio/avanzado) se permite contra cualquier página **detrás de advertencia + gate de atestación** (checkbox + términos + consentimiento registrado) antes de encolar; la responsabilidad legal del activo recae en el usuario que atesta. Los **escaneos automáticos (seed/cron del ranking gov) son SOLO pasivos**, restringidos por el scheduler. El detalle legal/enforcement de este gate vive en [01-legal-ethics](../01-legal-ethics/README.md).

Cada nivel define qué herramientas/intensidad usa **cada subagente**. Este documento cubre el subagente OWASP web; el subagente agéntico replica la escalera con su propia batería (ver [03-agentic-surface](../03-agentic-surface/README.md)).

## 3. Subagente OWASP (Web) — batería por nivel

| Nivel | Técnicas | Herramientas |
|-------|----------|--------------|
| **Básico** (pasivo, no intrusivo) | Fingerprint, TLS, headers de seguridad, templates pasivos, recon DNS | WhatWeb/Wappalyzer, testssl.sh, security-headers/Observatory, Nuclei (`exposures`, `misconfiguration`, `ssl`, `tech`, `dns`), robots/sitemap, subfinder/dnsx (passive) |
| **Intermedio** (activo suave, rate-limited) | Spider + scan pasivo, CVEs, enum ligero, CORS/cookies | + ZAP **baseline** scan, Nuclei full (CVEs, default-logins low-risk), Nikto, katana (crawl), ffuf/gobuster (dir enum ligero), checks CORS/cookie/clickjacking |
| **Avanzado** (activo / explotación, requiere autorización) | Active scan, inyección, orquestación autónoma | + ZAP **full active** scan, sqlmap (sobre params detectados), Nuclei fuzzing templates, pruebas de auth. **hexstrike-ai NO es parte de la batería garantizada del avanzado** (ver §6): el avanzado se realiza con ZAP full active + Nuclei fuzzing + sqlmap sobre 1 param conocido, dentro del budget global ~8 min (el perfil demo <90s pre-hornea lo pesado, ver §7) |

Cada nivel es **acumulativo**: "intermedio" añade su columna a lo que ya corre "básico", y "avanzado" añade la suya a lo de "intermedio". El símbolo `+` en la tabla denota exactamente esa acumulación.

### 3.1 Nivel básico (pasivo, no intrusivo)

El nivel básico es el único que Owliver dispara **sin un humano atestando** (vía el seed/cron del ranking gov) y por tanto define el piso de "pasivo": no envía tráfico activo, no hace spider, no fuzzea. Su batería:

- **Fingerprint de tecnología:** WhatWeb / Wappalyzer sobre la raíz.
- **TLS:** testssl.sh.
- **Headers de seguridad:** security-headers / Observatory.
- **Templates pasivos Nuclei:** tags `exposures`, `misconfiguration`, `ssl`, `tech`, `dns`.
- **Recon ligero:** robots/sitemap, subfinder/dnsx en modo **passive**.

El nivel básico debe **cerrar en <90s por sitio** (presupuesto operativo que protege el seed gov de saturar recursos; ver [04-scanning-engine](../04-scanning-engine/README.md) para la concurrencia y los límites de recursos). Los tres parsers de alta densidad y buen JSON (Nuclei JSONL, testssl `-oJ`, security-headers/Observatory) garantizan que el nivel básico **siempre** produce `Finding[]` válidos, lo que a su vez garantiza el ranking gov.

### 3.2 Nivel intermedio (activo suave, rate-limited)

Añade tráfico activo suave y rate-limited sobre lo del básico:

- **ZAP baseline scan** (spider + scan pasivo de ZAP).
- **Nuclei full:** CVEs y default-logins de bajo riesgo (además de los tags pasivos del básico).
- **Nikto.**
- **katana** (crawl).
- **ffuf / gobuster** (enum de directorios ligero).
- Checks de **CORS / cookie / clickjacking**.

Requiere haber pasado el gate de atestación (es activo). Nunca se ejecuta de forma automática.

### 3.3 Nivel avanzado (activo / explotación)

Añade explotación dirigida sobre lo del intermedio:

- **ZAP full active scan.**
- **sqlmap** sobre params detectados (en la práctica del demo, sobre **1 param conocido**).
- **Nuclei fuzzing templates.**
- **Pruebas de auth.**

El alcance preciso del "avanzado" (qué entra y qué se recorta) está fijado en §6.

## 4. Whitelist `(is_gov, level)` — enforcement en el worker

El worker **impone** una whitelist de herramientas+flags indexada por `(is_gov, level)`. Esta whitelist es el control técnico que hace que "pasivo" sea pasivo de hecho, no solo de intención: **"pasivo" se define por herramientas+flags, no por intención**.

Para **`is_gov`/básico**:

- Herramientas permitidas: **testssl.sh**, **security-headers/Observatory** y **WhatWeb**, todas sobre la **raíz**.
- **Nuclei** con `-tags ssl,tech,http-misconfig` sobre la **URL raíz**, **sin spider**, y **excluyendo** `intrusive,dos,fuzzing,network`.
- **ZAP spider** y **katana** quedan **deshabilitados** para gov.
- Se **parsea y honra `robots.txt`** antes de cualquier request (ver §5).
- Owliver **nunca** dispara activo automático contra ningún sitio (gov o no); ver [01-legal-ethics](../01-legal-ethics/README.md).

Esta whitelist es el punto donde el subagente OWASP traduce el nivel lógico a una lista concreta de invocaciones. El worker la consulta **antes** de pasar tools al agente: para un target gov, el `owasp_agent` solo recibe las tools pasivas, de modo que ni siquiera tiene la opción de lanzar un activo (defensa en profundidad sobre el enforcement del scheduler descrito en [01-legal-ethics](../01-legal-ethics/README.md)).

> Regla operativa: cualquier flag o tool que no esté explícitamente en la whitelist para el par `(is_gov, level)` evaluado **no se ejecuta**. La whitelist es allow-list, no deny-list.

## 5. Manejo de `robots.txt`

Antes de **cualquier** request del subagente OWASP web, Owliver **parsea y honra `robots.txt`** del host objetivo. Esto aplica de forma obligatoria al camino gov/pasivo (donde es parte de la definición de "pasivo") y es el comportamiento por defecto del recon ligero del nivel básico (robots/sitemap). El `User-Agent` con el que se evalúa y se ejecuta es el identificable `Owliver-Scanner/1.0 (+contacto)` (ver [01-legal-ethics](../01-legal-ethics/README.md) para la política de User-Agent y rate-limiting).

## 6. Alcance del nivel avanzado (power-up acotado, sin hexstrike)

El nivel "avanzado" es **narrativa de explotación acotada, no orquestación autónoma**. Su batería garantizada es:

- **ZAP full active scan**
- **Nuclei fuzzing templates**
- **sqlmap sobre 1 param conocido**

ejecutada dentro del **budget global de scan ~8 min** (con timeout duro por tool; ver [04-scanning-engine](../04-scanning-engine/README.md)).

**hexstrike-ai NO forma parte de la batería garantizada del avanzado.** hexstrike es un server TCP:8888 + wrapper MCP sobre imagen Kali con 150+ tools instaladas aparte, con orquestación LLM no-determinista; está **recortado a CERO desde el inicio del plan** (no es un slot tardío que se intenta "por si acaso"). El "avanzado" se realiza íntegramente con ZAP full active + Nuclei fuzzing + sqlmap, time-boxed dentro del budget.

Si en algún momento se reintroduce hexstrike, debe ser **detrás de un feature-flag `ENABLE_HEXSTRIKE` + healthcheck al arrancar el worker**: si el server no responde, el `owasp_agent` **no recibe esa tool** y cae al fallback (ZAP full active + Nuclei fuzzing + sqlmap). Bajo ninguna circunstancia el avanzado depende de hexstrike para producir findings.

## 7. Perfil demo vs. budget global (distinción explícita)

Existen **dos presupuestos de tiempo distintos** que no deben confundirse:

- **Budget global de scan ~8 min** — el límite real del nivel avanzado (ZAP full active + Nuclei fuzzing + sqlmap). Este es el comportamiento de producción del nivel avanzado.
- **Perfil demo / "demo level" <90s** — un perfil **explícito y curado** que corre SOLO un subconjunto rápido (Nuclei subset + testssl + 1 probe contra el bot propio) con **timeout duro garantizado por config (~60–90s)**. El perfil demo **pre-hornea lo pesado**: todo lo que tarda minutos (ZAP full, garak, hexstrike) se muestra desde resultados **ya almacenados** (fixtures), nunca corriendo en vivo durante el pitch.

> El número `<90s` pertenece **exclusivamente** al perfil demo, no al nivel avanzado. El nivel avanzado real opera bajo el budget ~8 min. No reemplazar el avanzado por el demo level: son cosas distintas con propósitos distintos.

El perfil demo se ejecuta contra **targets controlados en localhost** (bot propio plantado para el agéntico, OWASP Juice Shop / DVWA dockerizado para el web), nunca contra `.gob.mx` en vivo. El detalle del guion de demo vive en spec.md (overview, §17).

## 8. Resumen del contrato para el desarrollador

1. El nivel (`level`) es un parámetro del scan; junto con `is_gov` (derivado del host) determina la batería exacta vía la whitelist del §4.
2. El subagente OWASP web traduce `(is_gov, level)` a una lista concreta de invocaciones de tools+flags; **solo** se ejecuta lo que la whitelist permite (allow-list).
3. Básico = pasivo por herramientas+flags, cierra en <90s/sitio, único camino automático, honra `robots.txt`.
4. Intermedio y avanzado son activos → requieren gate de atestación, nunca automáticos.
5. Avanzado = ZAP full active + Nuclei fuzzing + sqlmap sobre 1 param, dentro del budget ~8 min; **sin** hexstrike en la batería garantizada.
6. El `<90s` es el perfil demo, no el avanzado.
