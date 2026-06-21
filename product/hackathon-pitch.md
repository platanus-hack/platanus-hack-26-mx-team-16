---
status: implemented
title: Owliver — Guía de Pitch para Hackathon (3 minutos)
description: Guion slide-por-slide, coreografía del demo en vivo, diseño y plan B para presentar Owliver en 3 minutos.
---

# Owliver 🦉 — Guía de Pitch para Hackathon (3 min)

Guía lista para producir las slides y el guion hablado. **Regla de oro de un
pitch de 3 min:** una idea por slide, el **demo en vivo es el 40% del tiempo**, y
cierras con visión + ask. No leas las slides: la slide es el póster, tú eres la voz.

- **Duración objetivo:** 180 s. **Velocidad:** ~150 palabras/min → ~420 palabras
  totales. Cada guion abajo ya está medido.
- **Formato:** 8 slides + 1 segmento de demo. 16:9, modo oscuro (war-room).
- **Una sola promesa que el público debe recordar:** *"Owliver audita —y rompe—
  la IA del gobierno, en vivo, y le pone calificación A–F."*

---

## Presupuesto de tiempo (cronómetro)

| # | Slide | Tiempo | Acumulado |
|---|---|---|---|
| 1 | Hook | 0:15 | 0:15 |
| 2 | Problema | 0:25 | 0:40 |
| 3 | Solución | 0:25 | 1:05 |
| 4 | **DEMO en vivo (Theater)** | 1:05 | 2:10 |
| 5 | El diferenciador (superficie agéntica) | 0:20 | 2:30 |
| 6 | ranking + viralidad | 0:15 | 2:45 |
| 7 | Negocio (watchlist) | 0:08 | 2:53 |
| 8 | Cierre / ask | 0:07 | 3:00 |

> Si vas tarde, **recorta la slide 7**, nunca el demo. El demo es lo que se recuerda.

---

## Slide 1 — Hook (0:15)

- **En pantalla (grande):** 🦉 **Owliver** · debajo, en Geist Mono:
  *"¿Qué tan segura es la IA del gobierno?"*
- **Visual:** fondo casi negro, ojos ámbar del búho. Nada más.
- **Guion:**
  > "El gobierno está poniendo chatbots de IA en todos lados. La pregunta que
  > nadie está haciendo: **¿se pueden hackear?** Nosotros construimos algo que lo
  > responde — automáticamente."

## Slide 2 — El problema (0:25)

- **En pantalla:** dos bullets, iconos:
  - 🐢 El pentesting hoy es **manual, lento y caro** — semanas, consultores, PDFs muertos.
  - 🤖 **Nadie audita la "superficie agéntica"**: los chatbots/LLM nuevos se pueden
    *prompt-injectar* y *jailbreakear*, y los escáneres clásicos (OWASP) ni los ven.
- **Guion:**
  > "Hoy auditar un sitio toma semanas y un consultor caro que entrega un PDF que
  > nadie lee. Y hay un hueco nuevo: los chatbots de IA. Un atacante les inyecta un
  > prompt y les saca su system-prompt o los hace decir lo que no deben. Los
  > escáneres tradicionales son **ciegos** a eso."

## Slide 3 — La solución (0:25)

- **En pantalla:** flujo de 3 pasos →
  `URL + nivel`  →  `🦉 Equipo de agentes (Opus + 2 Sonnet)`  →  `Calificación A–F`
- **Sub-bullet:** "Cubre **OWASP + superficie agéntica**. Reporte que cualquiera entiende."
- **Guion:**
  > "Owliver: pegas una URL, eliges el nivel de ataque, y un **equipo de agentes de
  > IA** —un orquestador Opus con dos subagentes Sonnet— corre un pentest real:
  > OWASP **más** los chatbots. Te devuelve una **calificación de la A a la F** y un
  > reporte que tu jefe no técnico entiende. Pero déjenme **mostrárselos**."

## Slide 4 — DEMO EN VIVO · Live Theater (1:05) — *la pieza central*

> Cambia a la app real (`/scans/[id]`). Esto es cine: el ataque pasando en vivo.

- **Coreografía (narra mientras pasa):**
  1. **(0:10)** Pega `sat.gob.mx`, nivel **Básico**, click **Auditar**.
     > "Lanzo un escaneo contra el SAT, modo pasivo y legal."
  2. **(0:25)** Entra el **war-room**: dos carriles —🛡️ OWASP y 🤖 Agéntico— con
     chips de herramientas encendiéndose (`nuclei`, `testssl`…), barra de progreso,
     findings cayendo en vivo.
     > "Esto es en tiempo real: cada chip es una herramienta real disparando.
     > Izquierda, seguridad web. Derecha, el agente que ataca al **chatbot**."
  3. **(0:20)** Llega el **finding estrella**: fuga de system-prompt con **canary
     token** resaltado.
     > "Y aquí está el oro: el agente **jailbreikeó el chatbot** y sacó su prompt
     > interno. Esa cadena resaltada es nuestro **canary token** — prueba
     > irrefutable de que lo rompimos."
  4. **(0:10)** Click **"Ver reporte completo"** → grado **F**, dos gauges, párrafo
     **"Owliver te explica"**.
     > "Termina en segundos: calificación, y **Owliver te explica** en español qué
     > pasó y por qué importa."
- **PLAN B (ensayado):** si el SSE o el wifi falla, corta a un **video de respaldo
  de ~90 s** del mismo flujo. *Tenlo abierto en otra pestaña antes de empezar.*

## Slide 5 — El diferenciador (0:20)

- **En pantalla:** título *"No solo escaneamos. Rompemos la IA — y lo probamos."*
  - 🤖 Detecta el chatbot → lo sondea con prompt-injection/jailbreak.
  - 🔬 Un **LLM-judge + canary token** confirma el jailbreak (cero falsos positivos teatrales).
  - Estados: `detectado-sin-auditar` · `probado-limpio` · `probado-vulnerable`.
- **Guion:**
  > "Este es nuestro foso: cualquiera corre Nuclei. **Nadie** está auditando
  > automáticamente la superficie agéntica del gobierno y **probándolo con un
  > canary**. Ese es Owliver."

## Slide 6 — ranking + viralidad (0:15)

- **En pantalla:** screenshot del leaderboard `.gob.mx` (filas F en rojo) + el
  **Report Card** OG-image (la "F" roja grande).
- **Guion:**
  > "Y lo hacemos **público**: un ranking de sitios `.gob.mx`, los peores arriba.
  > Cada reporte genera una tarjeta que, pegada en X o WhatsApp, **se vuelve
  > viral**. Presión pública = nuestra distribución, gratis."

## Slide 7 — El negocio (0:08)

- **En pantalla:** *"Watchlist privada → monitoreo continuo + alertas (email/Slack)."*
- **Guion:**
  > "El ranking es el gancho. El **negocio** es la watchlist: monitoreo continuo
  > privado con alertas cuando baja tu grado. Eso es SaaS recurrente."

## Slide 8 — Cierre / ask (0:07)

- **En pantalla:** 🦉 **Owliver** · *"La IA del gobierno, bajo la lupa."* · logo
  Llamitai · una línea de contacto/ask.
- **Guion:**
  > "Owliver: pentesting con IA, que audita a la IA. **La superficie agéntica del
  > Estado, bajo la lupa.** Gracias."

---

## Coreografía del demo (checklist pre-pitch)

- [ ] App corriendo en **modo demo con fixtures** (no depende del backend en vivo).
- [ ] Scan de `sat.gob.mx` **pre-cargado** o que arranque en <2 s.
- [ ] **Video de respaldo de 90 s** abierto en otra pestaña (Plan B).
- [ ] Brillo de pantalla al máximo (el modo oscuro se ve lavado en proyector).
- [ ] Zoom del navegador a ~125% para que los chips/findings se lean desde atrás.
- [ ] Wifi del venue es traicionero → ten el demo **local** o video, nunca dependas de red.
- [ ] Ensaya el demo **3 veces con cronómetro**; el resto del guion, 2 veces.

---

## Diseño de las slides (usa la marca real)

- **Modo:** oscuro/SOC para slides 1, 4, 5, 8; claro/institucional para 6, 7
  (contraste = drama → calma → cierre).
- **Tokens:** primario teal `oklch(0.59 0.095 180.54)`; acento **ámbar** (ojos del
  búho) para CTAs/highlights; rojo `oklch(0.58 0.22 25)` solo para la **F** y críticos.
- **Tipografía:** **Figtree** para texto, **Geist Mono** para scores, payloads,
  el canary token y todo lo "instrumento".
- **Grados A–F:** A verde → F rojo (mismo mapa de color que la app).
- **Densidad:** máx. **6 palabras por bullet**, máx. 2 bullets por slide. Si tienes
  un párrafo en una slide, va en tus notas, no en pantalla.
- **Mascota 🦉:** dormida (slide 1) → alerta/ojos ámbar (slide 4–5) como hilo visual.

---

## Errores que matan un pitch de 3 min (no los cometas)

- ❌ Gastar 60 s en el problema. **40 s máximo** — el jurado ya conoce el dolor.
- ❌ Demo sin Plan B. El wifi **va** a fallar. Ten el video.
- ❌ Leer las slides. Mira al jurado; la slide es respaldo.
- ❌ Arquitectura técnica en pantalla. A nadie le importa tu diagrama en 3 min;
  guárdalo para Q&A.
- ❌ Cerrar sin ask. Di qué quieres (ganar, piloto con una dependencia, etc.).

---

## Preparación de Q&A (10 s cada respuesta)

- **"¿Es legal escanear `.gob.mx`?"** → "El ranking corre **solo en modo pasivo**
  —equivalente a Mozilla Observatory—. Los escaneos activos exigen una **atestación
  legal de autorización** forzada en código, no es un checkbox decorativo."
- **"¿Falsos positivos en el jailbreak?"** → "Un **canary token**: si aparece en la
  respuesta del modelo, el jailbreak es prueba reproducible, no opinión."
- **"¿Qué los hace mejores que un escáner OWASP?"** → "OWASP es la mitad. La otra
  mitad —la **superficie agéntica**— no la cubre nadie automáticamente."
- **"¿Modelo de negocio?"** → "Ranking público gratis (distribución viral) →
  watchlist privada de pago (monitoreo + alertas)."
- **"¿Qué tan rápido?"** → "El perfil demo corre en **<90 s** con timeout duro."

---

## Versión de 60 segundos (si te cortan el tiempo)

Slides **1 → 4 (demo, 35 s) → 5 → 8**. Una frase cada una:
> "¿Qué tan segura es la IA del gobierno? *(demo: jailbreak + canary)* Owliver
> audita OWASP **y** los chatbots, lo prueba con un canary, y le pone una F en
> público. La IA del Estado, bajo la lupa."
