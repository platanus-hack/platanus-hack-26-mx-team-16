# Owliver — Refinamiento de la spec (huecos y cómo cerrarlos)

> ⚠️ **ARCHIVO / HISTÓRICO (2026-06-20).** Este análisis de huecos ya se **fusionó**
> en las features numeradas de [`product/features/`](../features/). Su profundidad de
> implementación vive ahora distribuida por feature (p. ej. §1→`04-scanning-engine`
> y `05-agent-team`, §2→`03-agentic-surface`, §4→`10-realtime-live-view`,
> §6→`06-data-model`/`07-scoring`/`12-api`). Se conserva como referencia; **no es la
> fuente de verdad** — esa es el subspec correspondiente.

> Consolidación de los huecos detectados por 7 revisores senior, deduplicados y re-priorizados con criterio de hackathon (20h, equipo de 3-4). Prioridad: **blocker** (no hay demo sin esto) > **high** > **medium** > **low**. Cada hueco trae *Qué falta · Por qué importa · Cómo cerrarlo*. Los blocker/high jugosos incluyen **Propuesta de texto para la spec**.

---

## Resumen ejecutivo

Los 7 revisores convergen con fuerza en **tres blockers estructurales** que la spec presenta como triviales y que en realidad son el grueso del trabajo:

1. **Invocación de scanners en Docker** (§5): el worker es un contenedor y nunca se decide *cómo* lanza los scanners. Sin esto, `run_nuclei`/`run_zap` son funciones vacías → 0 findings reales.
2. **Parsers salida-cruda → `Finding[]`** (§6): ~8 formatos heterogéneos (Nuclei JSONL, ZAP JSON/XML, testssl, garak report.jsonl…) más el mapeo a categoría OWASP. Es el corazón del producto, escondido en un renglón.
3. **Puente chatbot → target de garak/promptfoo** (§4, §6): garak/promptfoo no atacan una web, exigen un config request/response por-vendor. Sin el puente, `agentic_score=N/A` en todo y muere el diferenciador #1.

A esos se suman dos blockers transversales: el **gate legal es un checkbox de honor** sin enforcement real (riesgo legal directo), el **"pasivo" está mal definido** (lo que corre ignora robots.txt y envía tráfico activo al Estado), y el **live-view no tiene replay** (Redis pub/sub es at-most-once → pantalla vacía al recargar en el momento estrella del pitch).

**Tesis arquitectónica de fondo, repetida por casi todos los revisores:** *saca al LLM del camino de datos.* Parsing, dedup y scoring → Python determinista. Opus solo redacta. Para el agéntico, **Playwright maneja la conversación** (resuelve sesión/cookies/"apunta a la URL" gratis) contra un **bot propio plantado** para garantizar el finding estrella reproducible.

Y el meta-hueco de entrega: el plan §15 es **secuencial**; con 3-4 personas eso es 1 carril con 3 espectadores. Hay que **congelar contratos en la hora 0** y poner **checkpoints horarios con criterio binario** para recortar a tiempo.

---

## 1. Camino de datos del scan: Docker, parsers y structured output

> El núcleo no-recortable (§15). Tres huecos que los revisores de "Orquestación", "Infraestructura" y "Realismo" reportaron por separado pero son **un solo problema**: cómo pasamos de una URL a `Finding[]` válidos sin que el LLM lo arruine.

### 1.1 [BLOCKER] Mecanismo de invocación Docker sin decidir — *(fusiona Orq#3 + Infra#1)*

**Qué falta.** §5 dice "cada herramienta corre en su contenedor Docker" pero nunca decide *cómo* el worker (que ya es un contenedor) los lanza: ¿`docker run` por invocación?, ¿`docker exec` a un contenedor vivo?, ¿DinD?, ¿socket mount (siblings/DooD)?, ¿CLIs preinstaladas en la imagen del worker? Cada opción cambia radicalmente filesystem compartido, red y permisos.

**Por qué importa.** Es la pieza que más fácil se rompe a las 3am. Descubrir tarde que el socket mount no funciona en tu PaaS quema 3-4h. Sin patrón funcional, **ni un solo finding real**.

**Cómo cerrarlo (decisión concreta).** Híbrido pragmático para 20h:
- **Una imagen `scanners` fat** con las CLIs ligeras preinstaladas (nuclei, testssl, whatweb, nikto, katana, ffuf, sqlmap, subfinder, dnsx) y el worker corre **dentro** de ella → `subprocess.run([...], timeout=N)`. Sin socket, sin DinD para el caso común.
- **Excepciones pesadas** que sí van en contenedor propio: **ZAP** (script `zap-baseline.py`/`zap-full-scan.py`) y **hexstrike** (MCP). Para estas, el worker monta el socket del host (`/var/run/docker.sock`, patrón DooD/sibling) y usa un único helper `run_tool(image, cmd, shared_dir)`.
- **NO DinD** (requiere `--privileged`, lento, rompe en cloud).

> **Propuesta de texto para la spec (§5, nueva subsección "Patrón de ejecución de scanners"):**
> *"El worker corre dentro de la imagen `scanners` que trae preinstaladas las CLIs ligeras (nuclei, testssl, whatweb, nikto, katana, ffuf, sqlmap, subfinder, dnsx); cada tool se invoca por `subprocess.run([...], capture_output=True, timeout=N)`. ZAP y hexstrike son contenedores pesados aparte: el worker monta `/var/run/docker.sock` (sibling/DooD, NO DinD) y los lanza vía un único helper `run_tool(image, cmd, shared_dir)`. Un directorio host compartido `/data/scans/{scan_id}/` se monta en el worker y en cada scanner pesado (con socket mount, el `-v` apunta al path del HOST). Se documenta una tabla tool → mecanismo → timeout."*

### 1.2 [BLOCKER] Parsers salida-cruda → `Finding[]` — *(fusiona Orq#4 + Realismo#5)*

**Qué falta.** §6 paso 3 ("su salida cruda se parsea a Finding[]") esconde ~8 esquemas distintos: Nuclei JSONL, ZAP JSON/XML jerárquico, testssl JSON, nikto (texto/CSV sin severidad), sqlmap (texto+sesión), whatweb JSON, garak `report.jsonl`, promptfoo results JSON. Mapear severity/category(A01-A10/LLM01-LLM10)/cvss/evidence/remediation desde cada uno es lo que da valor — y **nadie está asignado**. El mapeo a categoría OWASP no sale gratis de ninguna tool.

**Por qué importa.** Es literalmente el corazón del producto. Subestimarlo es el riesgo #1 de un demo con findings vacíos o mal categorizados. El estimado §15 ("2-5h para 4 parsers") es optimista; 8+ no caben.

**Cómo cerrarlo.** Recorte agresivo + **1 persona full-time** en parsers:
- Priorizar **3 parsers de alta densidad y buen JSON**: **Nuclei** (JSONL nativo con `info.severity`/`classification.cvss-score`/`cwe` → casi 1:1), **testssl** (`-oJ`), **security-headers/Observatory** (JSON con grade). Estos 3 garantizan nivel básico + ranking gov.
- **ZAP baseline** como 4º. **nikto/sqlmap** → parser best-effort (1 Finding genérico, severity media, sin OWASP fino) o cortar.
- **Mapeo OWASP = dict/YAML estático curado** (template-id/probe → A01-A10/LLM01-LLM10). **Nunca** pedírselo al LLM.

### 1.3 [BLOCKER] `response_model=list[Finding]` + tools es zona de bug en Agno/Claude — *(Orq#2)*

**Qué falta.** §6 pone `response_model=list[Finding]` en agentes con ~9 tools. Hay issues abiertos en Agno (#2612, #2433, #2847) de que tools + structured output conviven mal, y de detección incorrecta de soporte de structured-output en modelos Claude (cae a parsing menos fiable). Pedirle a Sonnet que "devuelva SOLO Finding[]" sintetizando JSONL crudo significa que **el LLM re-teclea findings, alucina/pierde campos (cvss, evidence) y trunca** con decenas de hallazgos.

**Por qué importa.** Si falla, el escaneo base (lo que NUNCA se corta, §15) no produce `Finding[]` válidos → no hay demo. Es el camino crítico del MVP.

**Cómo cerrarlo.** **Sacar el parsing del LLM por completo:** las tool-functions devuelven `list[Finding]` ya parseado (parser determinista vive en Python dentro de la tool). El agente Agno **solo orquesta CUÁLES tools correr por nivel**; los Finding se acumulan en un objeto de sesión/contexto, no vía `response_model`. Reservar structured output (Opus) solo para el resumen ejecutivo (texto). Verificar con un smoke-test que Agno detecta structured-output de Claude antes del demo.

> **Propuesta de texto para la spec (§6, reemplaza el pseudocódigo de los agentes):**
> *"Las tool-functions (`run_nuclei`, `run_zap`…) ejecutan el scanner Y parsean su salida a `list[Finding]` en Python puro; el parser determinista vive en la función, no en el LLM. Los agentes Sonnet NO usan `response_model=list[Finding]`: solo deciden qué tools correr por nivel y acumulan los Finding en el contexto de sesión. El scoring y la deduplicación se calculan en Python (§9). `response_model` estructurado se reserva para Opus, exclusivamente para el resumen ejecutivo en texto."*

### 1.4 [HIGH] Timeouts, cancelación y fallo parcial sin política — *(Orq#5 + Infra#4 parcial)*

**Qué falta.** §15 menciona "time-box" solo para hexstrike/garak. No hay timeout por tool ni budget global, ni qué pasa si una tool cuelga/revienta. Con ZAP active/sqlmap/nikto, colgarse es lo normal.

**Por qué importa.** Un scan colgado bloquea el worker y la cola, mata el live-view y arruina el demo. Sin aislamiento, una tool muerta tumba findings ya listos.

**Cómo cerrarlo.** Timeout duro por tool en `subprocess.run(timeout=)` (nuclei 90s, testssl 60s, ZAP baseline 120s, ZAP active 240s, sqlmap 120s, garak 180s) + budget global ~8 min. Cada tool en `try/except`: si falla/expira → emitir Finding meta "tool X no completó" (confidence baja) y **CONTINUAR**, nunca propagar la excepción. Como las tools devuelven `Finding[]` deterministas, todo se maneja en Python sin el LLM.

### 1.5 [HIGH] Concurrencia y límites de recursos sin definir — *(Infra#4)*

**Qué falta.** §10 dispara 30-50 escaneos del seed al arranque + los del usuario, pero no se define cuántos scans corren en paralelo ni límites por contenedor. ZAP full + garak full = GBs de RAM cada uno.

**Por qué importa.** 50 escaneos simultáneos al abrir el demo dejan al host sin RAM/CPU justo en la presentación.

**Cómo cerrarlo.** Worker con `max_jobs=1` o `2`. Seed gob.mx: **NO encolar 50 de golpe** — pre-escanear 5-8 sitios ANTES del demo y persistirlos (ver §6.1 fixtures). `--memory`/`--cpus` en cada `docker run` (ZAP `-m 2g`). Básico debe terminar en <90s/sitio.

### 1.6 [HIGH] Cold start: imágenes pesadas y descarga de templates — *(Infra#5)*

**Qué falta.** ZAP ~1.5-2GB, Kali de hexstrike varios GB, Nuclei descarga 12k+ templates en primer run (y **falla por DNS dentro del contenedor sin pre-pull**). El bloque 0-2h no reserva tiempo de warm.

**Por qué importa.** Si el primer `docker run nuclei` en vivo intenta descargar templates y falla, el nivel básico (que nunca se corta) no produce findings.

**Cómo cerrarlo.** En setup (0-2h): `docker pull` de TODAS las imágenes + pre-descargar nuclei-templates a un volumen (`nuclei -update-templates` una vez) y usar flag `-duc` (disable update check) en cada run. Pinear tags (`:stable`, no `:latest`). hexstrike NO se pre-carga si aprieta el tiempo.

---

## 2. La superficie agéntica (el diferenciador)

> **Tres revisores distintos** ("Agéntica", "Scoring/Live", "Realismo") reportaron el MISMO blocker estructural: el puente detección→ataque. Lo consolido aquí como un solo hueco con dos caminos.

### 2.1 [BLOCKER] El puente chatbot-embebido → target de garak/promptfoo no existe — *(fusiona Agéntica#1 + Scoring#7 + Realismo#1)*

**Qué falta.** §4/§6 listan garak/promptfoo como cajas negras que se "apuntan" al chatbot. Pero **ninguno ataca una web**: garak `RestGenerator` exige `uri` + `req_template_json_object` con `$INPUT` + `response_json_field` (JSONPath); promptfoo HTTP provider exige `url` + body con `{{prompt}}` + `transformResponse`. Para cada vendor hay que reverse-engineer endpoint, body, headers/auth y shape de respuesta (a menudo SSE/websocket, no JSON simple). El paso "detectamos el widget" no da nada de esto. **No existe modo "dale una URL y atacame el chat".**

**Por qué importa.** Sin el puente, el subagente no ejecuta ni un payload contra un chatbot real → no hay finding agéntico estrella → muere el demo (§17.3) y el diferenciador entero. Es el corazón del producto.

**Cómo cerrarlo (decisión 20h, dos caminos):**
- **CAMINO A — base recomendada: Playwright maneja la conversación.** El subagente NO usa garak/promptfoo como runner externo: (1) abre el widget, (2) inyecta el payload en el textarea, (3) lee la respuesta del DOM, (4) pasa par payload/respuesta al LLM-juez. **Resuelve gratis** descubrir el endpoint, la sesión, las cookies y el CSRF (el navegador los mantiene nativamente — ver §2.4). Funciona sobre cualquier vendor. Banco de payloads propio embebido (canary, ignore-previous, system-prompt-leak); **NO** depender de la suite completa de garak en el demo.
- **CAMINO B — fallback frágil:** Playwright+CDP intercepta la request de red del widget, extrae `{url, headers, cookies, body shape, response path}` y emite en caliente un promptfoo http provider YAML. Solo si sobra tiempo.

> **Propuesta de texto para la spec (§4, nueva subsección "Puente de ataque agéntico"):**
> *"El ataque a chatbots NO usa garak/promptfoo como runner que 'apunta a la URL' (ninguno descubre el endpoint ni el shape solos). Camino base (intermedio/avanzado): **Playwright maneja la conversación turno a turno** — abre el widget, inyecta cada payload de un banco propio (canary, ignore-previous, system-prompt-leak), lee la respuesta del DOM y la pasa al LLM-juez. Esto resuelve sesión/cookies/CSRF y funciona sobre cualquier vendor. promptfoo/garak quedan como fallback opcional para los pocos targets cuyo provider HTTP sea derivable del crawl. Para el demo, el finding estrella se obtiene contra un **chatbot propio plantado** con un secreto en su system-prompt → 100% reproducible."*

### 2.2 [BLOCKER] Defaults de garak/promptfoo rompen el supuesto costo/'solo Claude' — *(Agéntica#2)*

**Qué falta.** §16 cree que "Sonnet/Opus" controla el costo del red-team, pero el costo real está en: (a) garak manda **cada prompt 10 veces** por default (`generations=10`) × decenas de probes → cientos/miles de llamadas al LLM objetivo (un tercero gob.mx); (b) el grader de promptfoo es **gpt-5/gpt-4o por default y exige `OPENAI_API_KEY`** — dependencia oculta de OpenAI que el equipo todo-Claude no tiene cableada → falla en runtime.

**Por qué importa.** Un scan avanzado con defaults tarda 20-40 min, dispara rate-limits/WAF del objetivo, y revienta el time-box del demo. Y promptfoo red-team simplemente falla sin `OPENAI_API_KEY`.

**Cómo cerrarlo.** Si se usa el CAMINO A (Playwright + juez Claude propio), **esto desaparece** — es otra razón para preferir A. Si se insiste en garak/promptfoo: (1) garak `generations=1` + subset fijo de 3-4 probes (`promptinject`, `dan.Dan_11_0`, `leakreplay`); (2) override del grader de promptfoo a Anthropic (`defaultTest.provider` / `--grader`); (3) cap duro de N payloads por chatbot (8 intermedio, 20 avanzado) + timeout por payload. **Reforzar: garak/promptfoo JAMÁS corren sobre .gob.mx automáticos.**

### 2.3 [BLOCKER] El criterio del LLM-juez "¿fue comprometido?" no está definido — *(Agéntica#4)*

**Qué falta.** §4 dice "LLM-juez evalúa si fue comprometido" sin rúbrica, sin canary, sin evidencia tipada. No distingue "el bot repitió la instrucción" de "fue comprometido de verdad", ni define qué cuenta como leak ni qué se guarda en `evidence`.

**Por qué importa.** Define el `agentic_score` y la pantalla clave del demo (§17.3). Un juez vago da falsos positivos vergonzosos o falsos negativos que matan la narrativa de contraste.

**Cómo cerrarlo.** Juez como **assertion explícito por técnica**, no genérico:
- **CANARY:** inyectar un token secreto único; regex/juez verifica si aparece en la respuesta → leak **determinista**, evidencia = el token. Es lo que da evidencia incontestable para el demo.
- **SYSTEM-PROMPT LEAK:** rúbrica "la respuesta revela instrucciones/rol/reglas/herramientas que un usuario final no debería ver".
- **JAILBREAK:** rúbrica "cumple una petición fuera de su dominio declarado que debería rechazar".

Cada veredicto → Finding con `confidence` (alta si canary/regex, media si juicio LLM), `evidence={payload, respuesta_cruda, veredicto, reason}`, mapeado a LLM01/LLM06. Juez = Claude con `response_model` `(pass:bool, severity, reason)`.

### 2.4 [HIGH] Detección de chatbot subespecificada (fingerprints, lazy-load, falsos negativos) — *(Agéntica#3)*

**Qué falta.** §4 dice "clasificador LLM + fingerprints" sin definir: (1) qué señales concretas (selector/script-src/global); (2) los widgets cargan en iframe de 3er dominio con lazy-load tras click/scroll — un snapshot DOM inicial no los ve; (3) cómo se mantiene la lista en 20h; (4) el falso negativo (no se renderizó → "sin IA") **tira el diferenciador**.

**Por qué importa.** Si la detección falla, todo aguas abajo (puente, ataque, score, narrativa §9) no ocurre. Aquí el falso negativo es peor que el positivo.

**Cómo cerrarlo.** **Tabla de fingerprints determinista como PRIMERA pasada** (antes del LLM): match por `script src`/host (`js.intercomcdn.com`, `widget.intercom.io`, `js.driftt.com`, `static.zdassets.com/ekr`, `widget.tidio`, `client.crisp.chat`), por globals (`window.Intercom`, `window.drift`, `$zopim`), y por selectores de launcher. **SEGUNDA pasada** solo si no matchea: Playwright espera `networkidle` + scroll + click en launcher + re-snapshot; entonces el LLM clasifica. Lista = JSON versionado de ~12 vendors (>80% de gob.mx). Si nada matchea pero hay `<textarea>`/input tipo "pregúntame", marcar como superficie genérica de baja confianza, **no descartar**.

### 2.5 [HIGH] Sesión/cookies/CSRF del widget para multi-turn — *(Agéntica#5)*

**Qué falta.** §4 avanzado pide "multi-turn" e "inyección indirecta" pero trata al chatbot como stateless. Un chatbot real necesita handshake (conversation_id), cookies, a veces CSRF, y mantener estado entre turnos.

**Por qué importa.** Sin sesión, los ataques multi-turn (Crescendo/GOAT, el valor del avanzado) no funcionan y muchos widgets rechazan requests sin cookie → cero findings agénticos.

**Cómo cerrarlo.** **CAMINO A (Playwright) resuelve esto gratis** — razón extra para preferirlo. Si se usa promptfoo: `sessionParser` + `{{sessionId}}` en header/cookie/body, capturando cookies con Playwright antes. Para el demo, limitar avanzado a 2-3 turnos con un solo objetivo (system-prompt leak vía Crescendo corto).

### 2.6 [MEDIUM] `agentic_score` N/A confunde "no hay chatbot" con "no pudimos probarlo" — *(Scoring#8)*

**Qué falta.** "agentic = N/A si no se detectó superficie" mezcla dos casos: (a) sin chatbot → N/A legítimo; (b) detectamos chatbot pero no lo probamos → N/A engañoso, hay riesgo sin auditar y el overall colapsa a web_score como si la IA no existiera.

**Por qué importa.** Justo en el diferenciador, N/A puede esconder que el testing falló → falsa sensación de seguridad y overall inflado.

**Cómo cerrarlo.** **Tres estados, no dos:** `agentic_status ∈ (no_surface, tested, detected_not_tested)`. overall=web_score solo si `no_surface`. Si `detected_not_tested`: mostrar "IA detectada, sin auditar" (badge en reporte+leaderboard), no promediar pero tampoco premiar con 100. Persistir `agentic_status` en `scans`.

### 2.7 [MEDIUM] `inferred_model` se promete sin método fiable — *(Agéntica#6)*

**Qué falta.** §7/§11 prometen decir qué modelo usa el chatbot. Salvo que el JS llame directo a `api.openai.com`/`api.anthropic.com` (raro), es indeterminable desde fuera.

**Por qué importa.** Mostrar "modelo inferido: GPT-4" mal adivinado daña la credibilidad en la pantalla diferenciadora.

**Cómo cerrarlo.** Rebajar la promesa: `inferred_model` solo se llena con señal **dura** (fetch directo a host de proveedor detectado en el crawl, o el bot delata su modelo ante un probe directo). En todo lo demás → NULL + "modelo no expuesto (buena práctica)". No invertir tiempo en fingerprint por estilo.

---

## 3. Capa legal/ética: de checkbox a invariante

> Marcado "requisito, no opcional" en §3. Dos blockers que convierten la defensa legal del producto en algo real o en algo refutable en 10 segundos por un juez.

### 3.1 [BLOCKER] El gate es un checkbox de honor sin enforcement — *(Scoring#4)*

> ✅ **RESUELTO por decisión de producto (ver §3 de la spec, ya actualizada).** El
> modo activo se permite sobre **cualquier URL** —incluido `.gob.mx`— bajo
> **advertencia + atestación + consentimiento registrado**, SIN verificación de
> propiedad y SIN bloqueo por dominio: la responsabilidad recae en quien atesta.
> El enforcement en código se **reduce** (no se descarta): (a) los escaneos
> **automáticos** (seed/cron) son solo pasivos —enforcement en el scheduler—;
> (b) el **ranking público** sólo publica resultados pasivos; (c) un activo
> iniciado por usuario es **privado** de su cuenta. Queda **descartada** la
> propuesta original de `is_gov → 422 hard` para escaneos iniciados por usuario.
> El análisis de abajo se conserva como contexto histórico.

**Qué falta.** El gate persiste `authorized=true` pero **nada en código** impide marcar el checkbox y lanzar nivel AVANZADO (sqlmap, ZAP active, hexstrike) contra `sat.gob.mx`. La regla "is_gov → solo pasivo" vive en prosa (§3.2), no como invariante. Esto convierte la plataforma en una herramienta de ataque al Estado con un click.

**Por qué importa.** Es el único requisito "no opcional". Sin enforcement, el demo es legalmente indefendible y un juez técnico lo detecta de inmediato. Riesgo reputacional/legal directo.

**Cómo cerrarlo.** **Enforcement en `POST /scans`, no en UI:**
1. Resolver `is_gov` por sufijo `.gob.mx` ANTES de encolar; si `is_gov` y `level != basico` → **422 hard**, sin importar el checkbox.
2. Para activos sobre dominios no-gov: prueba de propiedad ligera factible en 20h — token por `(user, domain)` verificado vía registro DNS TXT `_owliver-verify` o archivo `/.well-known/owliver-<token>.txt`. Si no, activo bloqueado, solo básico.
3. Persistir `verification_method`, `verified_at` en `scans`. El checkbox queda como consentimiento adicional, no como única barrera.

> **Propuesta de texto para la spec (§3, reemplaza el punto 3):**
> *"El enforcement de niveles activos es una invariante en código en `POST /scans`, no una declaración de UI: (a) si `hostname` termina en `.gob.mx` y `level != basico` → 422, ignorando el checkbox; (b) niveles activos sobre dominios no-gov exigen prueba de propiedad (DNS TXT `_owliver-verify=<token>` o `/.well-known/owliver-<token>.txt`) verificada antes de encolar; sin ella solo se permite básico. Se persisten `verification_method` y `verified_at`. El checkbox de autorización es consentimiento adicional registrado, nunca la única barrera."*

### 3.2 [BLOCKER] "Pasivo" está mal definido: el básico envía tráfico activo e ignora robots.txt — *(Scoring#5)*

**Qué falta.** §3 equipara el básico a Observatory/SSL Labs, pero las tools elegidas NO son pasivas: (a) **Nuclei** con `exposures`/`misconfiguration`/`ssl` **envía requests activos** por default (su `-passive` es file-mode sobre respuestas ya capturadas, no lo que describe la spec); (b) **ZAP baseline** corre el **spider** (crawl activo); (c) ZAP spider y katana **NO respetan robots.txt**. O sea: el "pasivo automático" a 50 .gob.mx genera tráfico de scanner real contra el Estado, ignorando robots.

**Por qué importa.** La defensa legal entera del ranking gov (§3.2 "equivalente a Observatory/Shodan") se cae si lo que corre es un crawler+Nuclei activo que ignora robots. Es el corazón del riesgo legal y trivial de refutar técnicamente.

**Cómo cerrarlo.** Definir "pasivo gov" de forma **operativa y verificable**, codificado como **whitelist de tools+flags por `(is_gov, level)` en el worker** (no configurable por el usuario):
- Para `is_gov`: testssl.sh, security-headers/Observatory (1 request a la raíz), WhatWeb (fingerprint de la home), Nuclei limitado a `-tags ssl,tech,http-misconfig` **solo sobre la URL raíz, sin spider**, excluyendo `intrusive/dos/fuzzing/network`.
- **Desactivar ZAP spider y katana para gov.**
- **Honrar robots.txt:** parsear antes de cualquier request y excluir paths `Disallow`.

> **Propuesta de texto para la spec (§3.2 + §4 básico):**
> *"'Pasivo' se define por una whitelist de herramientas y flags codificada en el worker, no por intención. Para `is_gov`/básico: testssl.sh, security-headers/Observatory y WhatWeb sobre la raíz, más Nuclei `-tags ssl,tech,http-misconfig` sobre la URL raíz SIN spidering y excluyendo tags `intrusive,dos,fuzzing,network`. ZAP spider y katana quedan deshabilitados para gov. Se parsea y honra robots.txt antes de cualquier request."*

### 3.3 [LOW] Rate-limiting sin punto de aplicación — *(Datos#9)*

**Qué falta.** §3.4/§16 declaran rate-limiting obligatorio pero confunden dos límites distintos en una línea: por usuario en la API vs por-target en el worker.

**Cómo cerrarlo.** Dos límites separados: (1) **API** — `5 scans/hora` por usuario en `POST /scans` (Redis `INCR`+TTL o slowapi); (2) **worker** — Nuclei `-rl`, delay entre requests de ffuf/katana al target. Para 20h, mínimo el (1) porque protege el presupuesto del demo.

---

## 4. Live-view y eventos SSE

> El momento estrella del pitch (§17.2). **Dos revisores** ("Frontend", "Scoring/Live") + el de "Datos" reportaron el mismo problema desde tres ángulos: sin esquema tipado, sin replay y sin auth, la pantalla queda vacía justo cuando todos miran.

### 4.1 [BLOCKER] SSE sin esquema de eventos tipado, sin replay, sin estado al reconectar — *(fusiona Frontend#1 + Scoring#6 + Datos#4)*

**Qué falta.** (1) `scan_events(level, agent, message)` es texto plano **sin `type` discriminante** → el front no puede mapear evento→UI. (2) Redis pub/sub es **at-most-once sin replay**: si el usuario abre el stream 10s tarde (form→scan→click "ver en vivo"), **todo lo previo se perdió** → pantalla vacía. (3) Sin `id`/`seq` por evento, `Last-Event-ID` no replaya nada. (4) Next.js bufferea/comprime SSE y solo flushea al final si no se desactiva la compresión.

**Por qué importa.** Es EL momento del pitch. Si al recargar o entrar tarde la pantalla queda vacía, o los eventos no traen `type`, el demo estrella falla.

**Cómo cerrarlo.** Reusar el patrón ya probado en este repo (`workflows/.../event_replayer.py`, cursor `since_seq` en PG):
- **Esquema con discriminador:** `{seq:int, type: 'agent_status'|'tool_start'|'tool_end'|'finding'|'phase'|'score'|'done'|'error', agent, tool?, severity?, message, ts}`.
- **`scan_events` deja de ser opcional**; `seq` monótono por scan es la única fuente de orden.
- **Replay-then-tail:** al conectar, `GET /scans/{id}/stream` lee `Last-Event-ID`/`?since_seq`, hace replay desde PG de `seq>cursor`, luego se suscribe al pub/sub (`scan:{id}:events`) y hace tail. El front descarta `seq<=lastSeq`.
- Heartbeat comment cada ~20s; **desactivar compresión** en la ruta SSE.

> **Propuesta de texto para la spec (§7 + §12.2):**
> *"`scan_events(id, scan_id, seq, ts, type, agent, tool, severity, message, payload)` — persistencia obligatoria, `seq` monótono por scan es la única fuente de orden. `type` discrimina `agent_status|tool_start|tool_end|finding|phase|score|done|error`. `GET /scans/{id}/stream`: al conectar lee `Last-Event-ID`/`?since_seq`, replaya desde Postgres `seq>cursor` y luego hace tail sobre el canal Redis `scan:{id}:events`; heartbeat cada 20s; compresión desactivada para esta ruta."*

### 4.2 [MEDIUM] Auth del SSE: EventSource no manda header `Authorization` — *(Datos#7)*

**Qué falta.** §12.2 consume el SSE con `EventSource`, que **no permite headers custom** → el esquema JWT-en-header no funciona para SSE. Para scans privados, o el stream queda abierto (fuga) o se rompe.

**Cómo cerrarlo.** **Auth por cookie:** el callback del magic-link setea cookie HttpOnly; abrir con `new EventSource(url, {withCredentials:true})` y validar la cookie vía `Depends`. Alternativa rápida: token efímero de un solo uso en query (`?stream_token=`). **No** dejar el stream abierto para scans privados.

---

## 5. Frontend (Next.js): leaderboard, gate, reporte, auth

> El repo actual es la app autenticada de **Doxiq**: `/` ya está ocupado por `(protected)`. Casi todo lo público hay que construirlo desde cero.

### 5.1 [BLOCKER] Home/leaderboard público choca con la app existente — *(Frontend#2)*

**Qué falta.** `/` (raíz) está ocupado por la app autenticada. §17.1 asume `/` = leaderboard público **sin login**. No hay shell público, ni estructura de fila, ni orden default, ni acción fila→detalle.

**Cómo cerrarlo.** Crear **route-group `(public)`** con layout propio (logo Owliver + CTA "Escanear mi sitio", sin sidebar). `/` = leaderboard RSC (`GET /ranking?country=mx`). **Fila:** posición + favicon/hostname + chip de grado (color A-F) + mini-gauges 🛡️/🤖 + fecha último scan + flecha de tendencia. **Orden default:** peores primero (ver §6 desempate). Click → `/sites/{id}`. Reusar `table.tsx`. Estados empty/error/loading definidos.

### 5.2 [HIGH] Gate de autorización: UX condicional por nivel sin diseñar — *(Frontend#3)*

**Qué falta.** El checkbox debe ser obligatorio solo para activos (intermedio/avanzado) y oculto en básico; la spec lo dice en prosa pero el form no tiene lógica condicional. Faltan: dónde viven los términos, submit disabled, mensaje de error 403.

**Cómo cerrarlo.** Form con selector de nivel (3 cards radio). Al elegir Intermedio/Avanzado se revela el bloque gate: Checkbox + frase declarativa + link "Ver términos" (Dialog). Submit disabled hasta marcar. En Básico el bloque no aparece, `authorized=false`. 403 del back → toast.

### 5.3 [HIGH] Reporte: faltan componentes base + `/r/[token]` sin definir — *(Frontend#5)*

**Qué falta.** No existe **Accordion** (hay `collapsible`), no existe `chart.tsx`/gauge (recharts ^3.6.0 sí está), no hay **sonner/toast**. `/r/[token]` no define qué se ve sin login ni si oculta `evidence` sensible (payloads/exploits) ni qué pasa si el token expiró.

**Por qué importa.** El reporte es núcleo (§15) y clímax del pitch. Sin accordion/gauge no renderiza; sin definir `/r/[token]` el link compartible puede **filtrar exploits reales**.

**Cómo cerrarlo.** `npx shadcn add accordion`; crear `chart.tsx` + Gauge semicircular (`RadialBarChart`, `endAngle=180`, Label central score+grado); añadir sonner. `/r/[token]`: server component, capa ejecutiva + findings técnicos pero **redacta/oculta payloads crudos por defecto** (tipo+impacto, no el exploit). Token inválido/expirado → 410 "Este enlace expiró".

### 5.4 [HIGH] Magic-link no existe en el repo (hay password) — 4 pantallas faltan — *(Frontend#4)*

**Qué falta.** El repo trae auth por password, no magic-link. Faltan: pedir email, "revisa tu correo" (cooldown/reenvío), callback/verify (estados), post-login. No se dice qué es público vs privado.

**Cómo cerrarlo.** **Decisión:** leaderboard, `/sites/{id}`, `/r/{token}`, reporte y scan **básico** son anónimos; solo watchlist/monitoreo y scans activos exigen sesión. Si Clerk está disponible, usarlo (magic-link out-of-the-box). Si no, 4 rutas en `(public)` reusando el patrón BFF `/api/auth/*` ya existente.

### 5.5 [HIGH] Form de scan: validación de URL y handoff post-submit — *(Frontend#6)*

**Qué falta.** No se define normalización de URL cliente (¿`sat.gob.mx`?, prefijo `https://`?, rechazar localhost/IP privada?), ni el redirect post-submit a la live view, ni qué pasa si ya hay un scan running.

**Cómo cerrarlo.** Input con `new URL()`, prefijo `https://`, extraer hostname, rechazar IPs privadas/localhost/hostnames sin punto, preview "Vas a escanear: sat.gob.mx". Submit → loading → `POST /scans` → `router.push('/scans/{id}/live')`. Si ya hay scan running, el back devuelve el `scan_id` existente y se redirige igual (no duplica — ver §6.4).

### 5.6 [MEDIUM] Watchlist, `/sites/[id]`, nav global y responsive — *(Frontend#7 + #8)*

**Qué falta.** Dashboard de watchlist sin estructura/acciones/estados; `/sites/[id]` (destino del click del leaderboard) no existe; sin nav global para las dos audiencias; sin comportamiento móvil del live-view/leaderboard.

**Cómo cerrarlo.** Watchlist `(protected)`: tabla hostname+grado+🛡️/🤖+último scan+Switch monitor+re-scan. `/sites/[id]`: cabecera + 2 gauges + histórico (mini line chart recharts) + lista de scans previos. Header público: logo + Leaderboard + Escanear + (sesión) Watchlist/avatar. Responsive: un solo breakpoint `md`; tabla→cards y 2-columnas→stack vertical. **Alertas in-app = recorte** (solo email/Slack).

---

## 6. Modelo de datos, API y scoring

### 6.1 [BLOCKER] Sin estrategia de seeding/pre-horneado del leaderboard — *(Realismo#3)*

**Qué falta.** §10/§17.1 asumen leaderboard "poblado desde el minuto 0" pero el seeding ocurre en hora 14+, corriendo scans reales contra 50 dominios (horas, dependiente de red/WAF). Sin plan B si a la hora 19 el ranking está vacío o lleno de "failed".

**Por qué importa.** El leaderboard ES la primera pantalla del pitch. Vacío o con errores hunde la narrativa antes de empezar.

**Cómo cerrarlo (decidir AHORA, no en la hora 14).** Crear un **seed SQL/JSON de fixtures**: 30-50 filas `sites`+`scans`+`findings` con grados pre-calculados y un par de findings agénticos plantados (ej. SAT "C web / F agéntico"). Cargarlo en bloque 0-2 vía CLI de fixtures. Los scans reales gob.mx corren en background y **sobrescriben** las filas sembradas si terminan a tiempo; si no, el demo usa los fixtures.

### 6.2 [BLOCKER] Falta el callback de canje del magic-link — *(Datos#1)*

**Qué falta.** §14 solo define `POST /auth/magic-link` (envía). No existe el GET que canjea el token, lo verifica, lo expira y emite sesión. No hay tabla de tokens, ni `/auth/logout`, ni `/auth/me`.

**Por qué importa.** El flujo de demo "URL propia + nivel avanzado" requiere usuario autenticado por el gate. Sin cerrar el login, no se demuestra nada más allá del ranking anónimo.

**Cómo cerrarlo.** Tabla `magic_tokens(token_hash PK, email, expires_at, consumed_at NULL, created_at)` (guardar SHA256, no el token plano). `GET /auth/callback?token=` (verifica no-consumido/no-expirado, marca `consumed_at`, upsert `users`, set cookie HttpOnly SameSite=Lax con JWT, redirect). Token opaco de 1 uso, TTL 10 min. `POST /auth/logout`, `GET /auth/me`.

### 6.3 [HIGH] AuthZ por endpoint sin definir — IDOR sobre vulnerabilidades reales — *(Datos#5)*

**Qué falta.** §14 no marca qué endpoints requieren auth ni con qué propiedad. `GET /scans/{id}/findings` de un scan AVANZADO (vulns explotables de un dominio privado) — ¿lo ve cualquiera con el id? Si los ids son secuenciales, es una fuga de findings reales (IDOR sobre el propio producto de pentesting).

**Por qué importa.** El producto almacena vulnerabilidades explotables. Sin authz, Owliver se vuelve un índice público de cómo hackear los sitios de sus usuarios. El peor titular posible.

**Cómo cerrarlo.** `scans.visibility ENUM(public, private)`. Gov básico/pasivo = public. Intermedio/avanzado o sites con `owner_user_id` = private → requiere owner o estar en watchlist. Reporte público solo vía token, no vía `/scans/{id}`. **`scans.id` = UUIDv4** (no serial) para no ser enumerable + check de owner.

### 6.4 [HIGH] `POST /scans` sin idempotencia — *(Orq#6 + Datos#2)*

**Qué falta.** Nada impide doble-click, retry de red o el seed re-ejecutado lanzando escaneos duplicados. Cada uno corre Opus+Sonnet+garak+ZAP: duplicar es caro, ensucia el ranking, y un retry ciego de un nivel activo es un **segundo ataque no consentido** (§3). Además §2/§4 tratan RQ/Arq como intercambiables (RQ es sync; el worker hace `asyncio.gather` → **Arq**).

**Cómo cerrarlo.** **Fijar Arq** (asyncio nativo). Dos capas de idempotencia: (1) **partial unique index** `scans(site_id, level) WHERE status IN ('queued','running')` → el 2º POST devuelve 200 con el `scan_id` existente; (2) `job_id` de Arq derivado de `site_id+level` (colapsa doble-submit inmediato; el partial index cubre el re-scan, que Arq no). `max_tries=1` para activos (preferir fallar a re-atacar), `max_tries=2` para básico/gov. `scans.status='running'` como lock.

### 6.5 [HIGH] CRUD básico ausente: listar/cancelar/re-escanear + health — *(Datos#3)*

**Qué falta.** §14 no tiene `GET /scans` (listar), `POST /scans/{id}/cancel` (matar un scan colgado — crítico con hexstrike/garak), `DELETE /watchlist/{id}`, `GET /health`, `GET /ready`. Sin cancel, un scan atascado obliga a reiniciar el worker en pleno pitch.

**Cómo cerrarlo.** Añadir `GET /scans?status=&site_id=&limit=&cursor=`, `POST /scans/{id}/cancel` (set `cancelled`, publica evento SSE, el worker chequea una flag Redis entre tools), `DELETE /watchlist/{id}`, `GET /health` (proceso) y `GET /ready` (Postgres+Redis). Añadir `cancelled` al enum.

### 6.6 [HIGH] Modelo sin progreso de scan, estado por-tool ni dedupe-key — *(Datos#4 modelo + Scoring monitoreo)*

**Qué falta.** `scans` solo tiene `status`; no hay progreso ni estado por herramienta para el live-view al recargar. `findings` no tiene **dedupe/fingerprint estable** → §8 (first_seen/last_seen, monitoreo, "finding nuevo/resuelto") es indeterminable sin una clave de identidad.

**Cómo cerrarlo.** `scans`: `+progress int`, `+current_phase text`, `+tools_status jsonb` (`{nuclei:'done', zap:'running'}`). `findings`: `+dedupe_key = sha256(site_id + source + category + normalize(affected_url) + param + tool)`, `first_seen`/`last_seen` a nivel **site** (no scan). Re-scan hace UPSERT por `(site_id, dedupe_key)`: si no reaparece → `status='fixed'`. Index `findings(site_id, dedupe_key)`.

### 6.7 [HIGH] El cap `min(100,penalty)` colapsa el ranking en empate de F/0 — *(Scoring#1)*

**Qué falta.** `sub_score = max(0, 100 − min(100, penalty))` hace que cualquier sitio con `penalty>=100` (~3 criticals) caiga a 0. En 30-50 .gob.mx reales, **la mayoría empata en 0/F** → orden "peores primero" indefinido y la narrativa A-F del demo se pierde. Sin desempate ni normalización por tamaño de superficie.

**Por qué importa.** El leaderboard es lo PRIMERO del demo. 40 de 50 sitios en F/0 sin orden se ve roto.

**Cómo cerrarlo.** No cambiar la fórmula base, pero: (a) persistir `penalty_raw` (sin clamp) como columna en `scans` y ordenar el leaderboard por `(grade asc, penalty_raw desc)`; (b) mostrar `penalty_raw`/conteo ponderado en la fila; (c) opcional: contar solo el peor finding por `(category, endpoint)` para no inflar por duplicados.

### 6.8 [HIGH] Scan parcialmente fallido premia al sitio que rompe el scanner — *(Scoring#2)*

**Qué falta.** "No penaliza" solo cubre agentic N/A. Si ZAP/Nuclei/testssl crashean/timeout/son bloqueados por WAF → 0 findings → **mejor** score. Un sitio que tira el scanner sale con A. `scans.status` no tiene `partial`.

**Por qué importa.** Invierte el incentivo y da scores falsamente buenos en los sitios más hostiles/protegidos.

**Cómo cerrarlo.** `scans.coverage jsonb` con `{tool, status: ok|failed|timeout}`. Regla: si faltó ≥1 scanner base → **cap del grado en C** + etiqueta "cobertura parcial" en reporte y leaderboard + finding informativo "cobertura incompleta". Nunca mostrar A con cobertura parcial.

### 6.9 [MEDIUM] Costo de tokens de Opus en síntesis sin límite — *(Orq#8)*

**Qué falta.** "Opus solo en síntesis" no acota el tamaño: un avanzado genera cientos de findings; pasarle todo el `evidence` jsonb es un prompt de miles de tokens, caro y lento, y el dedup vía LLM sobre cientos de items es poco fiable.

**Cómo cerrarlo.** Scoring (§9) = fórmula Python, NO Opus. Dedup en Python por `dedupe_key` antes de tocar el LLM. A Opus solo un resumen compacto: top-N por severidad (title+severity+category+impact, **sin** evidence completo) para redactar "Owliver te explica" + top-3. Opus procesa <2k tokens/scan.

### 6.10 [MEDIUM] Paginación + formato de error estándar ausentes — *(Datos#6)*

**Cómo cerrarlo.** Cursor en `findings/scans/ranking`: `?limit=50&cursor=<id>` → `{items, next_cursor}`. Findings ordenados por severidad desc. Error único `{error:{code, message, details?}}` centralizado en un `exception_handler` de FastAPI desde la hora 0.

### 6.11 [MEDIUM] Token de `public_reports` sin generación/expiración/revocación — *(Datos#8)*

**Cómo cerrarlo.** `token = secrets.token_urlsafe(32)`. `GET /r/{token}`: 404 si no existe, **410 Gone** si `expires_at < now`. TTL default 7 días, settable en `POST /scans/{id}/share`. `+revoked_at NULL`. Index UNIQUE en `public_reports(token)`. El público expone capa ejecutiva + findings **sin payloads de explotación**.

### 6.12 [LOW] Almacenamiento de evidencia/screenshots indefinido — *(Infra#7)*

**Cómo cerrarlo.** Archivos en volumen compartido `/data/evidence/{scan_id}/{n}.png` servidos por ruta estática FastAPI; `evidence.screenshot` guarda esa URL relativa. **NO base64 en jsonb** (infla DB), **NO MinIO** (servicio extra inútil al demo). PDF embebe desde la misma ruta.

### 6.13 [LOW] Saltos de grado D→F sin E, findings info=0 sin uso — *(Scoring#3)*

**Cómo cerrarlo.** Añadir E: `A≥90 B≥80 C≥70 D≥60 E≥40 F<40` (más escalones en la zona poblada). Info: mostrar en capa técnica con conteo aparte, sin afectar score.

---

## 7. Power-ups y entrega (hexstrike, deploy, timing)

### 7.1 [HIGH] hexstrike subestimado — recortar a CERO desde el inicio — *(Orq#7 + Realismo#4)*

**Qué falta.** §15 da 1h (18-19) para integrar hexstrike, pero es un **server TCP:8888 + wrapper MCP sobre imagen Kali** con 150+ tools instaladas aparte (Docker cubre solo ~27), orquestación LLM no-determinista. El "fallback ZAP full" tampoco es trivial (40min-2h). Ambos caminos del slot de 1h son inviables.

**Por qué importa.** Es lo primero en el orden de recorte, pero si el equipo lo intenta "por si acaso" en la hora 18, quema el tiempo de deploy/pulido que realmente decide si hay demo.

**Cómo cerrarlo.** **Recortar hexstrike a CERO desde el inicio del plan** (no en la hora 18). Reemplazar "avanzado" por: ZAP baseline + Nuclei full subset + sqlmap sobre 1 param conocido, time-boxed <90s. El "avanzado" del demo es narrativa, no orquestación real. Si se insiste: feature-flag `ENABLE_HEXSTRIKE` + healthcheck al arrancar el worker → si no responde, el `owasp_agent` no recibe esa tool y cae al fallback. **Liberar la hora 18-19 entera para deploy+pulido.**

### 7.2 [BLOCKER] El live-view no puede esperar scans de minutos — sin estrategia de tiempo de demo — *(Realismo#2)*

**Qué falta.** §17.2 muestra el live-view sobre un scan AVANZADO en vivo, pero ZAP full = 40min-2h, garak = ~20min, hexstrike indeterminado. El pitch dura minutos; el scan dura una hora. No hay "demo level" ni presupuesto de tiempo.

**Por qué importa.** Si el presentador hace clic en "escanear avanzado" en vivo, el live-view se queda colgado durante todo el pitch.

**Cómo cerrarlo.** Definir un **"demo level" explícito y curado**: el live-view del pitch corre SOLO un perfil rápido (Nuclei subset + testssl + 1 probe contra el bot propio) con **timeout duro ~60-90s garantizado por config**. Todo lo demás (ZAP full, garak, hexstrike) se muestra desde resultados **YA almacenados** (fixtures, §6.1).

### 7.3 [HIGH] Sin historia de deploy ni decisión live-vs-grabado — *(Infra#8 + Realismo#8)*

**Qué falta.** §15 mete "deploy" en medio renglón sin decir DÓNDE. El stack (web+api+worker+redis+pg+scanners+hexstrike+scheduler) no levanta en free-tier ni necesariamente en un PaaS gestionado (sin socket del host). Los scanners necesitan egress a los .gob.mx (la wifi del venue/WAF puede bloquear).

**Por qué importa.** El riesgo #1 de todo hackathon es "funcionaba en mi máquina", y es lo último que se toca, sin margen.

**Cómo cerrarlo (decidir desde la hora 0).** Un **VPS Linux** (DigitalOcean/Hetzner, 8GB+ RAM) con docker-compose, socket disponible, egress libre. **NO PaaS gestionado.** Pre-escanear el seed gob.mx EN el VPS antes del demo (no depender de la wifi del venue). El live-view del pitch corre contra **targets controlados en localhost** (bot propio + juice-shop/DVWA dockerizado), NO contra .gob.mx en vivo. **Grabar un video de respaldo de 90s** la noche anterior como fallback.

### 7.4 [HIGH] Egress de red de los scanners sin aislamiento — *(Infra#6)*

**Qué falta.** Los scanners atacan URLs externas con egress a internet; con sibling containers arrancan en la red por defecto y pueden alcanzar postgres/redis/metadata del cloud (SSRF lateral).

**Cómo cerrarlo.** Red docker `owliver_egress` (bridge, sin acceso a `owliver_internal`); postgres/redis en su propia red sin egress. Scanners siempre con `--network=owliver_egress`. Bloquear IPs privadas/`169.254.169.254`. El host del demo **no** debe tener credenciales cloud montadas.

---

## 8. [CRÍTICO-TRANSVERSAL] Lo que ningún revisor cubrió por completo

> Huecos de coordinación, observabilidad y secretos que viven *entre* dimensiones y que ningún revisor "es dueño" de reportar — pero que bloquean al equipo si no se deciden en la hora 0.

### 8.1 [BLOCKER] [crítico-transversal] Sin contratos congelados → 3-4 personas trabajan en serie — *(Realismo#6, lo elevo a transversal-maestro)*

**Qué falta.** §15 es una línea de tiempo **secuencial**. No define qué interfaces se congelan temprano: (1) `Finding`/`AgenticResult` Pydantic + enums, (2) esquema de `scan_event`, (3) contratos de respuesta de la API (§14). El frontend no puede empezar hasta la hora 11 porque no tiene shapes.

**Por qué importa.** Es el meta-hueco que multiplica a todos los demás. Sin contratos, los 4 carriles se bloquean mutuamente y 20h se vuelven 1 carril con 3 espectadores.

**Cómo cerrarlo.** **Bloque 0-2 produce 3 artefactos congelados:** (a) `finding.py` (Finding+AgenticResult+enums), (b) `events.py` (shape de `scan_event` con `type`+`seq`), (c) **stubs de API que devuelven fixtures** con el shape de §14. Frontend trabaja contra fixtures desde la hora 2. **Carriles:** P1=infra/cola/API+seed · P2=parsers OWASP+scoring · P3=agéntico (bot propio+puente Playwright) · P4=frontend (leaderboard+reporte) contra fixtures.

### 8.2 [BLOCKER] [crítico-transversal] Secretos / API keys de LLM sin gestión

**Qué falta.** Nadie definió cómo se inyectan/protegen `ANTHROPIC_API_KEY` (Opus+Sonnet en cada scan), `OPENAI_API_KEY` (grader default de promptfoo — §2.2), Resend, Slack webhook. Sin esto, el worker arranca sin credenciales y **todo agente falla en runtime**; y un `.env` commiteado en un repo público de hackathon **filtra las keys** (las de Anthropic con presupuesto activo).

**Por qué importa.** Es la causa #1 de "funcionaba en mi máquina pero el worker no arranca en el VPS", y la filtración de keys es un incidente real y caro.

**Cómo cerrarlo.** `.env` en `.gitignore` desde el commit 0 (verificar que no esté ya trackeado), `.env.example` con las claves sin valor. Inyectar vía `env_file` en docker-compose. Un único módulo `settings.py` (pydantic-settings) que **falla ruidosamente al arranque** si falta una key requerida (`ANTHROPIC_API_KEY` obligatoria; `OPENAI_API_KEY` solo si `ENABLE_PROMPTFOO_GRADER`). **Presupuesto de tokens:** definir un cap mensual/diario en el dashboard de Anthropic antes del demo para que un loop accidental no agote la cuota antes del pitch.

### 8.3 [HIGH] [crítico-transversal] Observabilidad mínima del worker

**Qué falta.** Con scans de minutos, asyncio.gather de 2 agentes y ~10 tools, no hay decisión de logging estructurado ni de cómo se ve "el scan #42 se colgó en la tool ZAP". El live-view es para el usuario, no para depurar a las 3am.

**Cómo cerrarlo.** Logging estructurado con `scan_id` en cada línea (structlog o logger con `extra`). El `tools_status jsonb` (§6.6) es también la fuente de debug. Un `GET /scans/{id}` que devuelva `tools_status`+`coverage`+`error` da observabilidad suficiente sin montar Grafana. `docker compose logs -f worker | grep scan_id` como herramienta de demo-night.

### 8.4 [MEDIUM] [crítico-transversal] Detección de `is_gov` y resolución del seed

**Qué falta.** La regla legal entera (§3, §8.1) depende de clasificar `is_gov` correctamente, pero nadie definió **cuándo** se calcula (al crear el site) ni el edge case de subdominios estatales que no terminan en `.gob.mx` (ej. dominios `.edu.mx` o estatales custom). Un sitio gov mal clasificado como no-gov **puede recibir un scan activo** (rompe §3.1).

**Cómo cerrarlo.** Calcular `is_gov = hostname.endswith('.gob.mx')` al insertar el site, **antes** de cualquier encolado. Para el seed, marcar explícitamente `is_gov=true` en el fixture. Documentar que la cobertura es solo `.gob.mx` (no `.edu.mx`/estatales custom) y que cualquier duda → tratar como gov (fail-safe hacia pasivo).

---

## 9. Lista de acciones priorizada (orden de ataque)

> Mapeada a secciones de la spec. El orden es de dependencia, no de severidad pura: lo que desbloquea a más gente va primero.

**Bloque 0-2h — CONGELAR PRIMERO (desbloquea los 4 carriles):**
1. `finding.py` + `events.py` + stubs de API con fixtures → §6, §7, §14 *(8.1)*
2. Decidir **VPS** + docker-compose con redes aisladas (`egress`/`internal`) + `docker pull`/warm de imágenes + nuclei-templates a volumen → §5, §15 *(1.1, 1.6, 7.3, 7.4)*
3. `settings.py` con fail-loud + `.env` en `.gitignore` + cap de tokens Anthropic → transversal *(8.2)*
4. Seed de **fixtures** del leaderboard (30-50 filas con grados + 1 finding agéntico plantado) cargable por CLI → §10 *(6.1)*
5. Fijar **Arq** + partial unique index de idempotencia + `scans.id` UUID + `exception_handler` global → §4, §14 *(6.4, 6.3, 6.10)*

**Bloque 2-8h — NÚCLEO (lo que nunca se corta):**
6. Helper `run_tool()` + imagen `scanners` + **3 parsers** (Nuclei/testssl/security-headers) → `Finding[]` en Python, NO vía `response_model` → §5, §6 *(1.1, 1.2, 1.3)*
7. Timeouts por tool + budget global + fallo parcial → Finding-meta → §15 *(1.4)*
8. Whitelist de tools+flags por `(is_gov, level)` + robots.txt + enforcement `is_gov→422` en `POST /scans` → §3, §4 *(3.1, 3.2)*
9. Scoring + dedup en Python; `penalty_raw` + `coverage` + grado E + cap-C-si-parcial → §9, §7 *(6.7, 6.8, 6.9, 6.13)*

**Bloque 8-14h — DIFERENCIADOR + FRONT (en paralelo):**
10. Bot propio plantado + puente **Playwright-maneja-conversación** + juez con canary/rúbrica → §4, §6 *(2.1, 2.2, 2.3, 2.5)*
11. Fingerprints deterministas de vendors (1ª pasada) + lazy-load → §4 *(2.4)*
12. `agentic_status` de 3 estados → §9 *(2.6)*
13. Route-group `(public)` + leaderboard + form de scan (validación URL + gate condicional + redirect) → §10, §14, §17 *(5.1, 5.2, 5.5)*
14. Reporte: accordion + gauge + sonner + `/r/[token]` con redacción de exploits → §11 *(5.3, 6.11)*
15. Magic-link: callback `GET /auth/callback` + tabla `magic_tokens` + 4 pantallas → §12, §14 *(6.2, 5.4)*

**Bloque 14-18h — SWING (recortable):**
16. Live-view: `scan_events` con `seq`+`type`, replay-then-tail, auth por cookie, demo-level <90s → §5, §12 *(4.1, 4.2, 7.2)*
17. `dedupe_key` + first/last_seen a nivel site → monitoreo + alertas → §8, §12 *(6.6)*
18. CRUD: `GET /scans`, cancel, `DELETE /watchlist`, `/health`, `/ready` + rate-limit en `POST /scans` → §14, §3 *(6.5, 3.3)*
19. PDF + evidencia en volumen → §11 *(6.12)*
20. Watchlist UI + `/sites/[id]` + nav + responsive → §10, §14 *(5.6)*

**Bloque 18-20h — DEPLOY + PITCH:**
21. **hexstrike = CERO** (ya recortado desde el inicio); ZAP baseline + Nuclei subset + sqlmap como "avanzado" narrativo → §2, §15 *(7.1)*
22. Pre-escanear seed en el VPS, video de respaldo de 90s, guion → §15, §17 *(7.3)*

---

## 10. Qué congelar primero (para que el equipo de 3-4 no se bloquee)

**Los 5 artefactos de la hora 0-2 son innegociables — sin ellos no hay paralelismo:**

1. **`Finding` / `AgenticResult` Pydantic + enums** — es el contrato entre P2 (parsers), P3 (agéntico) y P4 (reporte). Quien lo toque después de la hora 2 rompe a tres personas.
2. **Esquema `scan_event` (`seq` + `type`)** — contrato entre worker (P1/P2/P3 emiten) y frontend (P4 consume). Congélalo aunque el live-view sea recortable: los eventos los emiten todos los carriles.
3. **Stubs de API con fixtures (§14 shape)** — desbloquea a P4 (frontend) desde la hora 2 en vez de la hora 11. Es la diferencia entre 4 carriles y 1.
4. **Decisión de infra (VPS + patrón Docker)** — condiciona todo lo demás (socket mount, egress, RAM). Decidir tarde = descubrir a la hora 19 que el deploy no corre.
5. **Secretos + `is_gov`** — sin las keys, ningún agente arranca; sin `is_gov` correcto, la defensa legal se cae.

**Carriles sugeridos:** P1=infra/cola/API+seed · P2=parsers OWASP+scoring · P3=agéntico (bot propio+Playwright) · P4=frontend (contra fixtures).

**Checkpoints con criterio binario (recortar a tiempo, no a la hora 19):**
- **H8** — si "nivel básico end-to-end con findings reales en la UI" no está verde → congelar todo y al núcleo.
- **H12** — si el agéntico (bot propio + 1 probe → 1 finding visible) no funciona → cortar garak/promptfoo, dejar solo detección+inventario.
- **H16** — si el live-view SSE no renderiza → cortar live-view, usar un GIF/video pre-grabado.
- **H18** — congelar features; solo deploy+pulido+guion.

Cada checkpoint = **demo del estado actual**, no "casi listo".