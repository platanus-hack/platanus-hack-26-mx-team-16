---
feature: pipeline
type: plan
status: implemented
coverage: 100
audited: 2026-06-16
---

# Pipeline Editor — paquete de integración (Next.js + TypeScript)

Editor visual de pipelines como **página con scroll vertical**: columna ordenada de
etapas (grupos colapsables + fases sueltas), frontera de scope `documento → caso`,
reordenar por arrastre con validación, panel de detalle por fase, y apariencia
configurable por props.

Esto es **solo la estructura visual**. Tú conectas los datos: pasas tu catálogo de
etapas y recibes el estado por `onChange`.

---

## Instalación

1. Copia la carpeta `pipeline-editor/` a tu proyecto, p. ej. `components/pipeline-editor/`.
2. No tiene dependencias externas (solo React 18+). Compatible con el App Router y el
   Pages Router. Todos los componentes interactivos ya llevan `"use client"`.

```tsx
import { PipelineEditor } from "@/components/pipeline-editor";

export default function Page() {
  return (
    <div style={{ height: "100dvh" }}>
      <PipelineEditor />            {/* datos de ejemplo incluidos */}
    </div>
  );
}
```

> El componente ocupa el **alto de su contenedor** (`height: 100%`). Dale un contenedor
> con altura (`100dvh`, una celda de grid, etc.).

---

## Conectar tus datos

```tsx
"use client";
import {
  PipelineEditor,
  type Stage, type PipelineState,
} from "@/components/pipeline-editor";

const stages: Stage[] = [ /* tu catálogo (ver sample-data.ts como referencia) */ ];

const initialState: PipelineState = {
  order: ["extraccion", "completitud", "salida"], // ids en orden del spine
  collapsed: { extraccion: false },
  optional: { assess: true, validate_extraction: true },
  config: {},
};

export function MyEditor() {
  return (
    <PipelineEditor
      stages={stages}
      initialState={initialState}
      onChange={(state) => {
        // se dispara en cada cambio estructural (orden, colapso, toggles, config)
        // persiste donde quieras: server action, fetch, store…
      }}
      onSelect={(sel) => {/* sel = { stageId, kind? } | null */}}
    />
  );
}
```

### Modelo (`types.ts`)
- **`Stage`** — etapa del spine. `type: "group" | "solo"`, `scope: "document" | "case"`,
  `layout: "stack" | "branch"`, `removable`, `atomic`, `phases: Phase[]`.
- **`Phase`** — fase dentro de una etapa. `kind`, `optional`, `when`, `branch`,
  `config: ConfigField[]`.
- **`PipelineState`** — `order`, `collapsed`, `optional`, `config`. Es lo que emite
  `onChange` y lo que pasas como `initialState`.

El **orden** es la única invariante dura: todas las etapas `document` van antes que las
`case`. El editor rechaza cualquier arrastre/inserción que rompa esa frontera (con aviso),
vía `validatePipeline()`.

---

## Apariencia (props, no Tweaks)

```tsx
<PipelineEditor
  appearance={{
    nodeStyle: "tarjetas",   // "tarjetas" | "lineas" | "pastillas"
    density: "comodo",       // "comodo" | "compacto"
    icons: true,
    edgeStyle: "bezier",     // "bezier" | "step"
    palette: "multicolor",   // "multicolor" | "grafito"
    background: "plano",     // "plano" | "cuadricula"
  }}
  showToolbar               // barra superior con chip de validación + toggle de calidad
  toggleableStageId="calidad"
  toggleAfterId="completitud"
/>
```

---

## Estilos / theming

`pipeline-editor.css` está **scopeado bajo `.pe-root`** y usa CSS variables. No colisiona
con tu app. Para encajarlo en tu theme de shadcn, remapea las variables:

```css
.pe-root {
  --pe-surface: hsl(var(--card));
  --pe-ink: hsl(var(--foreground));
  --pe-muted: hsl(var(--muted-foreground));
  --pe-line: hsl(var(--border));
  --pe-brand: hsl(var(--primary));
  /* tipografías (el prototipo usa Geist / Geist Mono): */
  --pe-font: var(--font-geist-sans);
  --pe-mono: var(--font-geist-mono);
}
```

Los **acentos por etapa** (teal/amber/gold/…) se calculan en `accents.ts` con `oklch`.
Cambia `getAccent()` o usa `palette: "grafito"` para un look monocromo.

> Usa Tailwind para el **contenedor** que envuelve `<PipelineEditor/>`. El interior del
> editor es CSS propio para mantener fidelidad 1:1 con el prototipo; no necesita Tailwind.

---

## API completa de uso avanzado

El barrel `index.ts` exporta también las piezas puras por si quieres un control total
(estado controlado, render propio, etc.):

| Export | Qué es |
|---|---|
| `PipelineEditor` | componente principal |
| `usePipeline(opts)` | hook de estado (orden, colapso, toggles, config, selección, validación) |
| `computeLayout(stages, ui)` | motor de layout puro → coordenadas absolutas |
| `validatePipeline(stages)` | reglas de scope (devuelve `ValidationMessage[]`) |
| `edgePath(edge, style)` | generador de path SVG (bezier/step) |
| `getAccent(name, palette)` / `accentVars(a)` | sistema de acentos |
| `PipeIcon` | iconos de línea por `kind` |
| `SAMPLE_STAGES` / `SAMPLE_INITIAL_STATE` | datos de ejemplo |

---

## Archivos

```
pipeline-editor/
├─ index.ts                # barrel
├─ pipeline-editor.tsx     # componente principal
├─ pipeline-editor.css     # estilos scopeados (.pe-root)
├─ use-pipeline.ts         # hook de estado + acciones
├─ nodes.tsx               # SoloNode / GroupBox / CollapsedGroup / InnerNode / PipeEdges
├─ inspector.tsx           # panel de detalle + controles de config
├─ layout.ts               # motor de layout + validación (puro)
├─ accents.ts              # ramp de acentos oklch
├─ icons.tsx               # PipeIcon
├─ types.ts                # tipos del dominio + apariencia
└─ sample-data.ts          # catálogo + estado de ejemplo (reemplázalo)
```

---

## Notas

- La configuración de cada fase (`config`) es solo UI: `onChange` te entrega los overrides
  en `state.config[stageId][kind][key]`. Tú decides cómo mapearlos a tu backend.
- `human_review` compartido (review_gate + approval): el editor lo refleja con la nota de
  `sameKind`; el rol real lo decides por `config.trigger`, no por el kind.
- No incluye persistencia ni llamadas de red — es deliberadamente "headless de datos".
```
