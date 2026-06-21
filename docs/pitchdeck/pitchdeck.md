# Owliver 🦉 — Pitch Deck (10 slides)

> **Cómo usar este archivo:** pega TODO este contenido en Claude design (o tu generador de slides) con esta instrucción:
> *"Genera una presentación de 10 slides en formato 16:9 usando exactamente este contenido y este sistema de diseño. Una idea grande por slide, mucho aire, tipografía grande. Estilo: confiado, técnico, cívico — no 'startup genérica'."*
> Cada slide trae: kicker, título, subtítulo, contenido, dato clave y dirección visual.

---

## 🎨 Sistema de diseño (aplicar a TODOS los slides)

- **Primario:** violeta `#5648E8` (Material 3 Expressive).
- **Neutros:** cool-gray (fondos `#0E0E12`–`#16161D` en slides oscuros; `#F7F7FA` en claros).
- **Acentos de severidad:** rojo `#E5484D` (crítico), ámbar `#F5A623` (medio), verde `#30A46C` (seguro / grado A).
- **Tipografía:** Roboto Flex (títulos, pesos 700–900) + Roboto Mono (kickers, datos, etiquetas técnicas).
- **Forma:** radios de 1rem, superficies tonales con sombra suave (M3, NO bordes de 1px).
- **Logo:** ojos de búho Owliver (`frontend/public/owliver_eyes_white.png` en oscuro, `_black.png` en claro). Esquina o centrado en portada.
- **Regla de oro:** los números van GIGANTES; el texto de apoyo, pequeño. Cita la fuente en `mono` 12px.

---

## Slide 1 — Portada / Hook

- **Kicker:** `LLAMITAI · PENTESTING AUTÓNOMO`
- **Título:** Owliver 🦉
- **Subtítulo:** Un equipo de IA que hackea tu sitio antes de que lo hagan los malos — y te da una calificación de la A a la F.
- **Contenido (una línea, grande):** *"Cada sitio del gobierno guarda tus datos. Casi nadie está vigilando si están seguros. Eso cambia hoy."*
- **Visual:** fondo violeta-a-negro en degradado, ojos de búho brillando al centro, tagline en Roboto Mono debajo. Minimalista, cinematográfico.

---

## Slide 2 — El problema (el gancho cívico)

- **Kicker:** `MÉXICO BAJO ATAQUE`
- **Título:** No es una amenaza futura. Ya está pasando.
- **Contenido (3 datos en tarjetas grandes):**
  - **324,000 millones** de intentos de ciberataque a México en 2024 — #1–2 de Latinoamérica. *(Fortinet, 2025)*
  - **6 TB** robados a la SEDENA en 2022 — el mayor hackeo en la historia de México. *(Guacamaya / DDoSecrets)*
  - **+90 millones** de registros de votantes del INE expuestos. *(SecurityWeek)*
- **Dato clave (remate):** *"Si cae la Secretaría de la Defensa, todo `.gob.mx` está en la mira."*
- **Visual:** fondo oscuro, mapa de México con puntos de alerta rojos, los 3 números en `#E5484D` enormes.

---

## Slide 3 — Por qué sigue sin resolverse

- **Kicker:** `LOS HUMANOS NO ESCALAN`
- **Título:** La seguridad es cara, lenta y faltan manos.
- **Contenido:**
  - Un pentest manual cuesta **$5,000–$50,000 USD** y tarda **4–6 semanas**. *(Astra, 2026)*
  - **4.8 millones** de vacantes de ciberseguridad sin cubrir en el mundo, +19% anual. *(ISC2, 2024)*
  - **75%** del pentesting sigue siendo 100% manual. *(MarketsandMarkets)*
- **Dato clave:** *"Hay miles de sitios `.gob.mx`. Hay muy pocos expertos. La cuenta no da."*
- **Visual:** reloj + billetes desvaneciéndose a la izquierda; barra de "brecha de talento" creciendo a la derecha.

---

## Slide 4 — El punto ciego nuevo (DIFERENCIADOR)

- **Kicker:** `LA SUPERFICIE AGÉNTICA`
- **Título:** Ahora todos ponen un chatbot de IA. Nadie lo está probando.
- **Contenido:**
  - **85%** de los equipos de soporte están desplegando IA conversacional de cara al cliente. *(Gartner, 2024)*
  - **40%** de las apps empresariales tendrán agentes de IA para 2026 — desde <5% hoy. *(Gartner, 2025)*
  - **Prompt Injection = riesgo #1** del OWASP Top 10 para LLMs (LLM01:2025).
- **Dato clave (3 desastres reales):**
  - ✈️ **Air Canada** fue declarada legalmente responsable por lo que dijo su chatbot (2024).
  - 🚗 Un usuario manipuló al bot de un concesionario **Chevrolet** para "venderle" una Tahoe en **$1 USD** (2023).
  - 📦 El bot de **DPD** se volvió loco e insultó a la propia empresa (2024).
- **Visual:** burbuja de chat con un prompt malicioso inyectado resaltado en rojo; abajo los 3 logos/iconos de los incidentes.
- **Remate:** *"Una superficie de ataque que ningún pentest tradicional toca. Owliver sí."*

---

## Slide 5 — La solución

- **Kicker:** `PEGA UNA URL. ESO ES TODO.`
- **Título:** Owliver hace el resto.
- **Contenido (flujo de 3 pasos):**
  1. **Pega una URL** y elige el nivel de ataque.
  2. Un **equipo de agentes de IA** hace un pentest real: OWASP **+** superficie agéntica.
  3. Recibes un **reporte calificado de la A a la F** — técnico por dentro, legible para cualquiera.
- **Dato clave:** *"Lo que cuesta $20,000 y 4 semanas, en minutos y para todos."*
- **Visual:** los 3 pasos como flechas/tarjetas horizontales; usar la captura real `scan-form-avanzado.png` a la derecha.

---

## Slide 6 — Cómo funciona (el wow técnico)

- **Kicker:** `BAJO EL CAPÓ`
- **Título:** Un equipo de agentes, no un script.
- **Contenido:**
  - **Orquestador Opus** dirige a **2 subagentes Sonnet** que razonan, planean y atacan (framework Agno).
  - **Arsenal real en Docker:** Nuclei · OWASP ZAP · testssl · **garak** · **promptfoo** · hexstrike.
  - **Parsers deterministas + LLM-judge:** la IA decide, las herramientas comprueban. Cero alucinaciones en el reporte.
  - **Detección agéntica:** sondea chatbots/widgets con prompt-injection y jailbreaks reales.
- **Dato clave:** *"Combina el criterio de un pentester senior con la velocidad de una máquina."*
- **Visual:** diagrama de arquitectura — nodo orquestador violeta → 2 agentes → fila de logos de herramientas → reporte. Estética "blueprint".

---

## Slide 7 — Míralo en vivo (DEMO)

- **Kicker:** `EL TEATRO EN VIVO`
- **Título:** No es una caja negra. Lo ves pensar.
- **Contenido:**
  - Vista en tiempo real: cada hallazgo, cada herramienta, cada decisión del agente — en vivo.
  - Al final: **calificación A–F**, hallazgos priorizados por severidad y cómo arreglarlos.
- **Dato clave:** *"Transparencia total: del primer request al grado final."*
- **Visual:** SLIDE DE DEMO. Captura grande `scan-live-tripto-avanzado.png` (en progreso) + `scan-real-tripto-DONE.png` (reporte final con la calificación). *(Aquí va el demo en vivo durante el pitch.)*

---

## Slide 8 — El ranking público (el movimiento)

- **Kicker:** `RENDICIÓN DE CUENTAS`
- **Título:** Una tabla pública de qué tan seguro es tu gobierno.
- **Contenido:**
  - Ranking abierto de sitios **`.gob.mx`** calificados de la **A a la F**.
  - La transparencia crea presión. La presión crea mejoras.
  - "El banco de inspección" de la seguridad pública mexicana.
- **Dato clave:** *"Nadie quiere ser el sitio con 'F'. Esa vergüenza salva datos de ciudadanos."*
- **Visual:** mockup de leaderboard — lista de dependencias con badges de grado (A verde → F rojo). Limpio, tipo tabla de posiciones.

---

## Slide 9 — Watchlists + negocio

- **Kicker:** `DE UN ESCANEO A SIEMPRE-ACTIVO`
- **Título:** La seguridad no es una foto, es video.
- **Contenido:**
  - **Watchlists privadas:** monitoreo continuo + alertas cuando algo cambia o se rompe.
  - Modelo: SaaS recurrente para gobierno y empresas; ranking público como motor de adquisición.
  - **Mercado:** pentesting de **$1.98B (2025) → $4.39B (2031)**, 14.2% anual; pruebas de seguridad hacia **$41B para 2031**. *(MarketsandMarkets)*
- **Dato clave:** *"Empezamos gratis y públicos para `.gob.mx`; monetizamos el monitoreo continuo."*
- **Visual:** dashboard de watchlist con línea de tiempo de alertas; a la derecha, gráfica de mercado creciendo.

---

## Slide 10 — Por qué ahora + visión + cierre

- **Kicker:** `EL MOMENTO ES AHORA`
- **Título:** La IA ya está ganando en seguridad ofensiva. La traemos a `.gob.mx`.
- **Contenido (prueba de "por qué ahora"):**
  - 🥇 **XBOW**, una IA, llegó al **#1 del leaderboard de HackerOne** con ~1,060 vulnerabilidades reales (2025).
  - 🔍 **Google Big Sleep** encontró un **0-day real** en software ampliamente usado (2024).
  - 🛡️ **DARPA AIxCC** halló **18 zero-days reales** en 54M de líneas de código (2025).
- **Visión:** *"Democratizar la seguridad ofensiva. Empezamos por el gobierno de México. Seguimos con todo Internet."*
- **Cierre (grande):** **Owliver 🦉 — El banco de inspección para la era de la IA.**
- **CTA:** `owliver.com · contact@llamitai.com`
- **Visual:** vuelve a la portada — ojos de búho sobre violeta-negro, tagline final, datos de contacto en `mono`.

---

### Apéndice — Assets reales del repo para los slides
- Logo: `frontend/public/owliver_eyes_white.png` · `owliver_eyes_black.png`
- Formulario (Slide 5): `scan-form-avanzado.png`
- Teatro en vivo (Slide 7): `scan-live-tripto-avanzado.png` · `scan-real-tripto-inprogress.png` · `scan-real-tripto-progress2.png`
- Reporte final A–F (Slide 7): `scan-real-tripto-DONE.png` · `scan-live-after-fix.png`
