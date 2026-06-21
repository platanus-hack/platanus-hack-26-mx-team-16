# Owliver 🦉 — Guion del Pitch (narrative)

> Guion hablado para los 10 slides. **Duración objetivo: ~4 minutos.** Tono: confiado, cercano, técnico sin ser árido. `[ ]` = indicaciones de escena/pausa. **Negritas** = énfasis al hablar.

---

### Slide 1 — Portada *(~20s)*

> Hola. Somos **Llamitai**, y esto es **Owliver**.
>
> [pausa] Piensen en el último trámite que hicieron en línea con el gobierno. Su CURP, su dirección, su identidad… vive en un servidor `.gob.mx`. [pausa] La pregunta incómoda es: **¿alguien revisó si ese sitio es seguro?**
>
> Casi nunca. Owliver es un **equipo de inteligencia artificial que hace pentesting de forma autónoma** — y le pone una calificación, de la A a la F, a cualquier sitio web.

---

### Slide 2 — El problema *(~30s)*

> Esto no es una amenaza teórica. **Ya está pasando.**
>
> En 2024, México recibió **324 mil millones** de intentos de ciberataque. Somos el blanco **número uno o dos de toda Latinoamérica**, año tras año.
>
> En 2022, el grupo Guacamaya extrajo **6 terabytes** de la **Secretaría de la Defensa**. El mayor hackeo en la historia del país. Y el padrón del INE — más de **90 millones** de registros de votantes — ya estuvo expuesto.
>
> [pausa] Si cae la **Defensa Nacional**, ¿qué le espera al sitio de un municipio? La verdad es que **nadie lo sabe**, porque nadie lo está midiendo.

---

### Slide 3 — Por qué sigue sin resolverse *(~25s)*

> ¿Y por qué no se arregla? Porque la forma actual de auditar seguridad **no escala**.
>
> Un pentest profesional cuesta entre **5 y 50 mil dólares** y tarda de **4 a 6 semanas**. Encima, faltan **4.8 millones** de expertos en ciberseguridad en el mundo.
>
> [pausa] Hagan la cuenta: **miles** de sitios de gobierno, **un puñado** de especialistas, semanas por cada auditoría. **Es imposible.** Los humanos, solos, no dan abasto.

---

### Slide 4 — La superficie agéntica *(~35s)*

> Y aquí viene la parte que casi nadie está viendo.
>
> Hoy **todos** le están poniendo un chatbot de IA a su sitio. El **85%** de los equipos de soporte ya lo están haciendo. Para 2026, el **40%** de las apps empresariales tendrán agentes de IA.
>
> El problema: el riesgo **número uno** de OWASP para modelos de lenguaje se llama **prompt injection**. Y nadie lo está probando.
>
> [pausa, contar con los dedos] **Air Canada** perdió en tribunales por lo que dijo su chatbot. Un usuario engañó al bot de un concesionario **Chevrolet** para "venderle" una camioneta en **un dólar**. El bot de **DPD** terminó insultando a su propia empresa.
>
> Esto es una **superficie de ataque completamente nueva** — y ningún pentest tradicional la toca. **Owliver sí.**

---

### Slide 5 — La solución *(~25s)*

> Entonces, ¿cómo funciona Owliver? [pausa] **Pegas una URL. Eso es todo.**
>
> Eliges el nivel de ataque, y un **equipo de agentes de IA** ejecuta un pentest de verdad: las vulnerabilidades clásicas de OWASP **más** la superficie agéntica de los chatbots.
>
> Y te devuelve un **reporte calificado de la A a la F**: técnico por dentro, pero que **cualquier persona** puede entender. Lo que costaba veinte mil dólares y un mes… en minutos, y al alcance de todos.

---

### Slide 6 — Cómo funciona *(~30s)*

> Por dentro no es un simple script. Es un **equipo**.
>
> Un **orquestador**, corriendo en **Opus**, dirige a **dos subagentes** en Sonnet que razonan, planean y atacan. Detrás tienen un arsenal real, contenido en Docker: **Nuclei, OWASP ZAP, testssl, garak, promptfoo**.
>
> Y aquí está el truco que lo hace confiable: **la IA decide, pero las herramientas comprueban.** Usamos parsers deterministas y un LLM-juez, así que en el reporte final **no hay alucinaciones** — solo hallazgos verificados. Es el **criterio de un pentester senior** a **velocidad de máquina**.

---

### Slide 7 — Demo en vivo *(~30s)*

> Pero déjenme **mostrárselos**, porque esto es lo bonito.
>
> [iniciar demo / señalar pantalla] Owliver no es una caja negra. Tiene un **teatro en vivo**: ven cada hallazgo, cada herramienta y cada decisión del agente **en tiempo real**, mientras sucede.
>
> [señalar el reporte] Y al final… **la calificación**. Hallazgos ordenados por severidad, y exactamente **cómo arreglarlos**. Del primer request hasta el grado final: **transparencia total.**

---

### Slide 8 — El ranking público *(~25s)*

> Ahora, la parte que lo convierte en un **movimiento**.
>
> Tomamos los resultados y construimos un **ranking público** de los sitios `.gob.mx`, calificados de la A a la F, **a la vista de todos**.
>
> [pausa] Porque la **transparencia crea presión**, y la presión crea **mejoras**. **Nadie** quiere ser la dependencia con una "F" en la portada. Y esa incomodidad, esa vergüenza pública… **salva datos de ciudadanos reales.**

---

### Slide 9 — Watchlists y negocio *(~25s)*

> La seguridad no es una foto, es **video**. Un sitio seguro hoy puede romperse mañana.
>
> Por eso ofrecemos **watchlists privadas**: monitoreo continuo y **alertas** cuando algo cambia. Ese es nuestro negocio — **SaaS recurrente** para gobierno y empresas, con el ranking público gratuito como motor de adquisición.
>
> Y el mercado nos acompaña: el pentesting va de **2 mil millones hoy a más de 4 mil millones** de dólares en 2031, creciendo doble dígito cada año.

---

### Slide 10 — Por qué ahora + cierre *(~30s)*

> Última pregunta: **¿por qué ahora?** Porque la IA **ya está ganando** en seguridad ofensiva.
>
> Una IA llamada **XBOW** llegó al **número uno** del leaderboard de HackerOne, por encima de **todos los hackers humanos**. **Google** encontró un 0-day real con IA. **DARPA** halló **18 vulnerabilidades de día cero** con agentes autónomos. [pausa] Esto **ya no es teoría. Está funcionando.**
>
> Nuestra visión es **democratizar la seguridad ofensiva**. Empezamos por el gobierno de México. Seguimos con **todo Internet**.
>
> [pausa, mirar al jurado] **Owliver. El banco de inspección para la era de la IA.** [pausa] Gracias.

---

## Cheat-sheet de cierre rápido (por si te apuran)

- **Qué:** equipo de IA que hace pentesting autónomo (OWASP + chatbots) y califica A–F.
- **Quién:** sitios `.gob.mx` (ranking público) + empresas (watchlists privadas).
- **Por qué importa:** 324 mil millones de ataques a México/año; los pentests no escalan; los chatbots son un punto ciego total.
- **Por qué nosotros, por qué ahora:** la IA ofensiva ya superó a los humanos (XBOW #1 en HackerOne).
- **El gancho:** *"Nadie quiere una 'F' en la portada."*
