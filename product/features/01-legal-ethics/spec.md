---
feature: legal-ethics
type: spec
status: pending
coverage: 0
audited: 2026-06-20
sources: spec.md §3; spec-gaps.md §3 (3.1, 3.2, 3.3)
---

# Owliver — Capa legal / ética (invariante)

> El pentesting **activo** contra sistemas sin autorización es ilegal en casi
> cualquier jurisdicción. La decisión de producto de Owliver es permitir el modo
> activo sobre **cualquier URL** —sin verificación de propiedad del dominio, igual
> que ZAP, Burp o Nuclei— pero **siempre** detrás de una advertencia prominente +
> atestación + registro de consentimiento, donde la responsabilidad legal recae en
> quien atesta. Esta capa no es un checkbox de honor: se convierte en una
> **invariante real, aplicada en código**, mediante cuatro controles —gate de
> atestación persistido, escaneos automáticos solo pasivos por el scheduler,
> ranking público solo con resultados pasivos, y una definición *operativa y
> verificable* de "pasivo" (whitelist de herramientas+flags + robots.txt)— más
> rate-limiting y `User-Agent` identificable en todo escaneo.

## 1. Principio rector

El pentesting **activo** (niveles intermedio/avanzado) contra sistemas sin
autorización es ilegal en casi cualquier jurisdicción. **Decisión de producto:**
el modo activo se permite sobre **cualquier URL** —no se exige verificación de
propiedad del dominio (como tampoco la exigen ZAP, Burp o Nuclei)— pero **siempre**
detrás de una **advertencia prominente + atestación + registro de consentimiento**.
La responsabilidad legal del activo recae en el usuario que atesta.

Esto es el único requisito **"no opcional"** del producto. Sin enforcement real, el
producto es legalmente indefendible y un revisor técnico (o un juez) lo refuta en
segundos. Por eso esta capa se diseña como **invariante en código**, no como prosa
ni como una casilla de UI: la defensa legal de Owliver descansa sobre estos cuatro
controles efectivos, no sobre la buena fe del usuario.

> Quedó **descartada** la propuesta histórica de bloquear los escaneos iniciados
> por usuario sobre dominios gubernamentales con un `is_gov → 422 hard`, así como
> la de exigir prueba de propiedad del dominio (DNS TXT `_owliver-verify` o
> `/.well-known/owliver-<token>.txt`) para activos no-gov. La decisión vigente es
> permitir el activo sobre **cualquier** URL bajo atestación; el enforcement en
> código se concentra en los caminos automáticos y públicos (puntos 2–4 abajo),
> que son los que pueden disparar tráfico sin un humano atestando.

## 2. Mitigaciones obligatorias del MVP

Las cinco mitigaciones siguientes son obligatorias para el MVP.

### 2.1 Gate de atestación + advertencia (para activos)

Antes de encolar un escaneo activo sobre cualquier URL: advertencia explícita
*"Vas a lanzar pruebas intrusivas contra {host}; hacerlo sin autorización es
ilegal"* + checkbox obligatorio *"Declaro tener autorización para auditar este
dominio"* + aceptación de términos. Se persiste `authorized=true` + `authorized_at`
+ `requested_by` en la tabla `scans`. Sin consentimiento el job **no** se encola.
**No** se bloquea por dominio: la advertencia + la atestación SON el control.

El checkbox de autorización es **consentimiento adicional registrado**, nunca la
única barrera: las barreras reales son las invariantes de los puntos 2.2–2.4, que
viven en código y no dependen de lo que el usuario declare.

La pantalla/gate de atestación (UI, copy, estados del formulario) la define
[13-frontend](../13-frontend/spec.md). El enforcement a nivel de endpoint del gate
de atestación (validación de `authorized`/`authorized_at`/`requested_by` antes de
encolar en `POST /scans`) lo detalla [12-api](../12-api/spec.md).

### 2.2 Escaneos automáticos = SOLO pasivos (enforcement en código)

El único camino que Owliver dispara **sin un humano atestando** es el seed/cron del
ranking gov, restringido **por el scheduler** a nivel básico/pasivo (headers, TLS,
fingerprint, templates pasivos) — equivalente a lo que hacen públicamente Mozilla
Observatory / SSL Labs / Shodan. Owliver **nunca** lanza un escaneo activo
automático contra ningún sitio (gov o no).

Este es un punto de enforcement: el scheduler/seed **no puede** emitir un job con
`level != basico`; la restricción es del código del scheduler, no una opción de
configuración. La mecánica del seed/cron del ranking la detalla
[08-ranking-watchlists](../08-ranking-watchlists/spec.md); aquí queda fijado el invariante de
que **todo** disparo automático es pasivo.

### 2.3 Ranking público = solo resultados pasivos

El leaderboard público muestra únicamente resultados de escaneos **pasivos**. Un
activo **iniciado por un usuario** queda **privado de su cuenta**; sólo se publica
si el usuario genera un link público explícito (`/r/{token}`). Así "auditar al
Estado" en público se mantiene 100% no intrusivo, aunque un usuario pueda correr un
activo sobre su propia infraestructura.

La superficie pública (leaderboard, link `/r/{token}`) la detallan
[08-ranking-watchlists](../08-ranking-watchlists/spec.md) y [12-api](../12-api/spec.md); el
invariante de esta capa es: **ningún resultado de un escaneo activo llega al ranking
público de forma automática.**

### 2.4 Advertencia reforzada (no bloqueo) para dominios sensibles

Si el host es `.gob.mx` u otro marcado sensible, la advertencia del paso 2.1 es más
enfática (copy en rojo), pero el usuario **puede proceder** bajo su responsabilidad.
Es un refuerzo **no bloqueante**: la resolución de `is_gov` por sufijo `.gob.mx`
afecta el copy y la visibilidad por defecto (punto 2.3), **no** la posibilidad de
lanzar el activo.

### 2.5 Rate-limiting y User-Agent identificable

**Rate-limiting** y `User-Agent` identificable (`Owliver-Scanner/1.0 (+contacto)`)
en todos los escaneos para minimizar impacto. Ver §4 para la definición precisa de
los dos límites distintos (API por usuario vs worker por target).

## 3. Definición precisa de "pasivo" (whitelist operativa, no intención)

La defensa legal entera del ranking gov ("equivalente a Observatory / SSL Labs /
Shodan") sólo se sostiene si lo que corre es realmente pasivo. **El riesgo:** las
herramientas elegidas no son pasivas por defecto. **Nuclei** con
`exposures`/`misconfiguration`/`ssl` **envía requests activos** (su `-passive` es
file-mode sobre respuestas ya capturadas, no un modo de red pasivo); **ZAP baseline**
corre el **spider** (crawl activo); y tanto el spider de ZAP como **katana NO
respetan robots.txt**. Sin un control efectivo, el "pasivo automático" contra 50
sitios `.gob.mx` generaría tráfico de scanner real contra el Estado ignorando
robots — trivial de refutar técnicamente.

Por eso **"pasivo" se define por una whitelist de herramientas y flags codificada en
el worker, no por intención** y no configurable por el usuario. El worker
selecciona el conjunto de herramientas+flags en función de `(is_gov, level)`.

**Para `is_gov` / nivel básico (pasivo gov):**

- `testssl.sh` — análisis TLS.
- security-headers / Observatory — **1 request a la raíz**.
- WhatWeb — fingerprint de la home (URL raíz).
- Nuclei limitado a `-tags ssl,tech,http-misconfig` **solo sobre la URL raíz, sin
  spider**, excluyendo los tags `intrusive,dos,fuzzing,network`.
- **ZAP spider y katana quedan deshabilitados para gov.**
- **Honrar `robots.txt`:** parsear `robots.txt` **antes de cualquier request** y
  excluir los paths marcados `Disallow`.

Este conjunto es deliberadamente equivalente, en huella de red, a lo que Mozilla
Observatory, SSL Labs y Shodan hacen públicamente: un puñado de requests a la raíz +
inspección de TLS/headers/fingerprint, sin crawling y respetando robots.txt.

La whitelist completa de herramientas+flags por nivel (incluyendo los perfiles
intermedio/avanzado para escaneos activos iniciados por usuario) la posee
[04-scanning-engine](../04-scanning-engine/spec.md); esta capa fija el contrato
**legal** del perfil pasivo: si una herramienta o flag no aparece en esta whitelist
para `(is_gov, basico)`, no se ejecuta en un escaneo gov.

## 4. Rate-limiting: dos límites distintos

El rate-limiting obligatorio combina **dos límites diferentes** que deben aplicarse
en puntos distintos del sistema; no son el mismo control:

1. **API (por usuario).** `5 scans/hora` por usuario en `POST /scans`, implementado
   con Redis `INCR` + TTL (o `slowapi`). Protege el presupuesto del demo y evita que
   un usuario sature la cola. Es el límite mínimo imprescindible.
2. **Worker (por target).** Límites de tasa hacia el objetivo: Nuclei `-rl`, y delay
   entre requests de `ffuf` / `katana` al target. Minimiza el impacto sobre el host
   escaneado.

Todo escaneo, además, emite el `User-Agent` identificable `Owliver-Scanner/1.0
(+contacto)` para que el operador del sitio pueda identificar y contactar el origen
del tráfico.

El detalle de implementación del límite de API (slowapi / Redis, respuesta `429`) lo
posee [12-api](../12-api/spec.md); el detalle de los flags de rate-limit por
herramienta en el worker lo posee [04-scanning-engine](../04-scanning-engine/spec.md).

## 5. Resumen del invariante

| Control | Dónde se aplica | Efecto |
|---|---|---|
| Atestación + consentimiento persistido (`authorized`, `authorized_at`, `requested_by`) | `POST /scans` (ver [12-api](../12-api/spec.md)) | Sin atestación, no se encola activo |
| Disparo automático solo pasivo | Scheduler / seed-cron gov | Ningún activo automático, nunca |
| Ranking público solo pasivo | Visibilidad de resultados | Activos de usuario son privados por defecto |
| "Pasivo" = whitelist tools+flags + robots.txt | Worker, por `(is_gov, level)` | Huella de red equivalente a Observatory/Shodan |
| Rate-limit API + worker, UA identificable | `POST /scans` + worker | Impacto minimizado y trazable |

La suma de estos controles es la capa legal/ética de Owliver: una **invariante
aplicada en código**, no una declaración de UI ni un checkbox de honor. El checkbox
es consentimiento adicional registrado; las barreras reales viven en el scheduler,
en la visibilidad del ranking y en la whitelist del worker.
