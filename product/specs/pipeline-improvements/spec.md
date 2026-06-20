---
status: draft
created: 2026-06-17
---

# Pipeline Improvements — Backlog (mini spec)

Ideas de mejora del pipeline (brainstorm 2026-06-17). Para **revisitar después** de la
consolidación `extraction_gate` (ver `product/plans/extraction-gate-consolidation/`).

> **No haremos (decidido):** nodos genéricos condicionales/loop en el recipe. El modelo
> lineal + *branch-dentro-de-fase durable* es deliberado (Temporal ya es la capa con
> control de flujo). `when` se **eliminó** por la misma razón (no aportaba; el routing del
> gate ya migró a la decisión en `scratch`, que a su vez consolidamos en `extraction_gate`).

## Prioridad alta

### 1. Backtest / simulación de `ActivationPolicy` ("what-if")
Re-evaluar una policy candidata contra snapshots de casos históricos y reportar cuántos
habrían ido a clarify / review / QA. Convierte el tuneo de `field_thresholds` / `sample_rate`
/ severidades de **adivinanza a dato**. Insumo: confianza por campo + resultados ya
persistidos. Es el feature ancla del sistema de compuertas. Esfuerzo: medio.

### 2. Observabilidad de casos atascados + SLA
Aging + breach de SLA + auto-escalamiento para fases durables (`await_documents`, tareas
humanas). Extiende la pestaña Ejecuciones y los timeouts existentes
(`resolution_timeout`/`on_timeout`). Esfuerzo: medio.

## Quick wins

### 3. Política de fallo por fase
Generalizar `enrich.on_failure` (`review|continue|fail`) a TODAS las fases (qué pasa si
OCR/analyze/deliver fallan). Hoy el manejo de error es ad-hoc por fase.

### 4. Straight-through más agresivo
Saltar `analyze` si todos los campos vienen sobre umbral y ninguna regla bloqueante aplica
⇒ entrega más rápida/barata. Construye sobre E7 (caso universal). La señal ya la da el gate.

### 5. UX de corrección a nivel campo desde los gate items
Los items del gate ya cargan `bbox` / `candidates` / `confidence`. UI de revisión enfocada
(resaltar el campo en el doc, sugerir candidatos, corregir inline) en vez de re-leer todo.
Encaja con el North Star "the inspection bench".

## Estructural (mayor esfuerzo)

### 6. Fragmentos de pipeline reutilizables
Sin romper el 1:1 del ADR 0002 — el "spine case-scope" se repite en cada plantilla.

### 7. Pinneo doc-type ↔ pipeline versionado
Que cambiar el schema de un doc-type no rompa silenciosamente versiones selladas.

### 8. Caché de extracción por hash de documento
Evitar re-OCR en re-subida del mismo documento.

## Recomendación de orden
Tras `extraction_gate`: **#1 (backtest de policy)** + **#2 (SLA/atascados)** primero —
juntos transforman las compuertas de "configuración a ciegas" a decisiones basadas en datos.
