# Plan de migración del frontend a **Material 3 Expressive (pastel)**

> Fuente de verdad visual: **`/DESIGN.md`** (sistema Owliver M3 Expressive) + el archivo de diseño `owliver-design.pen` (pantallas hi-fi y el board *"Migración a M3 Expressive — Mapa de componentes"*). Este documento es el plan de implementación en código.

## 0. Principio rector

**No migrar pantalla por pantalla.** El frontend ya está bien factorizado: ~15 rutas que consumen **tokens CSS** (`globals.css`) a través de **primitivos shadcn/ui + Base UI** (`src/presentation/components/ui/*`, `cva`). Por eso el 80–90 % del cambio visual se logra en **dos capas**:

1. **Tokens** (`globals.css`): re-mapear los roles M3 + forma + tipografía + movimiento. → recolorea/retipa **todas** las pantallas de golpe.
2. **Primitivos** (`ui/*` `cva`): forma (pill, `xl`), elevación tonal, *state layers* y movimiento. → actualiza **todos** los usos de cada componente.

Solo después se hace un **paso por pantalla** para detalles (densidad de tablas, charts, formularios) y se **construyen las pantallas nuevas de Owliver** (pentest) que hoy no existen en código.

Stack confirmado: **Tailwind v4** (`@import "tailwindcss"`, `@theme inline`, sin `tailwind.config`), **shadcn** `style: base-vega` + **Base UI** (`@base-ui/react/*`), `cva`, `lucide`, `tw-animate-css`. Radio base `--radius: 0.75rem`; tema `.dark` ya presente.

---

## 1. Fase 0 — Tokens y tipografía (`src/app/globals.css`)

Mantener los **nombres** de variables shadcn (no romper consumidores) pero **remapear valores** a los roles M3 Expressive pastel de `DESIGN.md`, y **añadir** los roles que faltan.

### 1.1 Mapeo de roles (light)

| Var shadcn (mantener) | Rol M3 | Valor pastel |
|---|---|---|
| `--background` | surface | `#F2FAF7` |
| `--foreground` | on-surface | `#1E2B27` |
| `--card` / `--popover` | surface-container-low / -high | `#FFFFFF` / `#E0ECE8` |
| `--primary` / `--primary-foreground` | primary / on-primary | `#2C857A` / `#FFFFFF` |
| `--secondary` / `--secondary-foreground` | secondary-container / on- | `#D9EDE8` / `#101F1C` |
| `--muted` / `--muted-foreground` | surface-container / on-surface-variant | `#E6F1ED` / `#46524E` |
| `--accent` / `--accent-foreground` | **primary-container** / on- (hover/selected tint) | `#BEF3E8` / `#00201C` |
| `--destructive` / `-foreground` / `-deep` | error / on-error / on-error-container | `#E5736E` / `#FFFFFF` / `#7A1B18` |
| `--border` | outline-variant | `#C6D2CC` |
| `--input` | outline | `#76827D` |
| `--ring` | primary | `#2C857A` |

### 1.2 Roles M3 nuevos (añadir)

```css
--tertiary: #FFC95C;            /* ámbar "ojos del búho" (CTA/alerta). Texto sobre ámbar = ink, no blanco */
--tertiary-container: #FFE9BC;  --on-tertiary-container: #2A1F00;
--primary-container: #BEF3E8;   --on-primary-container: #00201C;
--secondary-container: #D9EDE8; --on-secondary-container: #101F1C;
--surface-container-lowest: #FFFFFF; --surface-container-low: #ECF6F2;
--surface-container: #E6F1ED; --surface-container-high: #E0ECE8; --surface-container-highest: #DAE7E2;
--outline: #76827D; --outline-variant: #C6D2CC;
/* Escala de grados A–F (color de estado, no se tematiza) */
--grade-a:#5FC487; --grade-b:#9FD06E; --grade-c:#ECCB68; --grade-d:#F0A05E; --grade-e:#EC7E63; --grade-f:#E0635F;
```
Exponer cada uno en `@theme inline` (`--color-tertiary: var(--tertiary)`, etc.) para clases `bg-tertiary`, `text-on-primary-container`…

### 1.3 Forma (M3 shape scale)

```css
--radius: 1rem;            /* md=12, lg=16 */
--radius-full: 9999px;    /* pill (botones, chips, FAB, switch) */
--radius-xl: 1.75rem;     /* 28px — cards hero */
```
El `@theme inline` ya deriva `--radius-sm..4xl`; añadir `--radius-full` y subir la base. Botones/chips → `rounded-full`; cards → `rounded-xl/2xl`.

### 1.4 Tipografía

```css
--font-sans: "Roboto Flex", "Roboto", ui-sans-serif, system-ui, sans-serif;
--font-mono: "Roboto Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
```
Cargar Roboto Flex + Roboto Mono vía `next/font/google` en `app/layout.tsx` (reemplazando Figtree/Geist). Definir la **escala de tipo M3** (Display/Headline/Title/Body/Label) como utilidades o un plugin de texto; *Headline/Label* en peso **emphasized** (600–700).

### 1.5 Elevación tonal + movimiento

```css
/* elevación: usar surface-container-* como nivel; sombra suave solo al elevar */
--elevation-1: 0 1px 2px rgb(0 0 0 / .06);  --elevation-3: 0 2px 6px rgb(0 0 0 / .12);
/* easing M3 */
--ease-emphasized: cubic-bezier(.2,0,0,1);
--ease-emphasized-decel: cubic-bezier(.05,.7,.1,1);
--ease-emphasized-accel: cubic-bezier(.3,0,.8,.15);
--dur-short: 150ms; --dur-medium: 300ms; --dur-long: 450ms;
```

### 1.6 Temas

- `.dark` → reescribir como **esquema M3 dark** (mismos roles, tonos oscuros teal).
- **Nuevo `.soc`** → tema **dark pastel-neón** para el Live Theater (`--background:#121A18`, neón cian/ámbar/coral/verde pastel de `DESIGN.md`). Se aplica solo en la ruta de escaneo en vivo.

**Resultado de la Fase 0:** todas las pantallas existentes quedan recoloreadas y re-tipadas a M3 pastel sin tocar JSX.

---

## 2. Fase 1 — Primitivos (`src/presentation/components/ui/*`)

Actualizar los `cva` para que el cambio aplique a todos los usos. Cambios por primitivo:

- **`button.tsx`** → `rounded-full` (pill). Mapear a la familia M3: `default`→**Filled** (`bg-primary`), `secondary`→**Tonal** (`bg-secondary` = secondary-container), nuevo `tonal`/`elevated` (con `shadow-[--elevation-1]`), `outline`→**Outlined**, `ghost`/`link`→**Text**. Añadir **state layer** (overlay `hover:` 8 % / `active:` 12 % de la on-color en vez de `/80`). `transition-[--dur-short] [--ease-emphasized]`. Conservar `size` (alturas) para no romper tablas densas.
- **FAB / icon-button** → variante nueva: `bg-tertiary-container`, `rounded-2xl`/`full`, `shadow-[--elevation-3]`; el FAB del CTA "Audita una URL".
- **`input.tsx` / `field.tsx` / `textarea.tsx`** → estilo **M3 filled**: `bg-surface-container-highest`, esquinas superiores redondeadas, **indicador inferior teal** en foco (en vez de ring completo); mantener el ring `aria-invalid`.
- **`card.tsx`** → `rounded-xl`/`2xl`, fondo `surface-container-low`, **elevación tonal + sombra suave** (quitar el hairline ring como separador primario).
- **`badge.tsx`** → pill, *assist/filter chip*; estados via grade-scale; el `SeverityChip` y `GradeBadge` (de Owliver) como variantes/derivados.
- **`dialog.tsx` / `sheet.tsx` / `alert-dialog.tsx`** → radios grandes (`2xl`), *scrim* M3, apertura con **spring** (ver Fase 2).
- **`tabs.tsx` / `toggle-group.tsx`** → **segmented button group** M3 (contenedor `rounded-full`, selección tonal).
- **`switch.tsx` / `checkbox.tsx`** → switch M3 (track `rounded-full`, thumb que crece al activar), check con *state layer*.
- **`table.tsx`** → filas más altas, hover tonal (`hover:bg-surface-container`), esquinas del contenedor `xl`.
- **`select.tsx` / `dropdown-menu.tsx` / `popover.tsx` / `combobox.tsx`** → superficies `surface-container-high`, `rounded-xl`, sombra suave, items con state layer.
- **`progress`** → indicador **wavy/squiggly** M3 Expressive (SVG con `<path>` animado) + circular determinado.
- **`skeleton.tsx`** → shimmer tonal (ya hay keyframe `shimmer`).
- **`tooltip.tsx` / `alert.tsx` / `separator.tsx` / `sidebar.tsx`** → roles M3 (sidebar = `surface-container`, activo con pill tonal). El `SettingsSidebar` ya existe en el .pen como referencia.

---

## 3. Fase 2 — Movimiento / animaciones

M3 Expressive = movimiento como material. Plan:

- **CSS** para *state layers*, transiciones de color/forma y los keyframes ya presentes (`shimmer`, `analysis-pulse`, `analysis-sweep`).
- **Librería de spring** (`motion` / Framer Motion, o `@react-spring`) para: entrada de *findings* (fade + spring slide-up), apertura de Dialog/Sheet (spring), morph del FAB, **count-up** del grado y **sweep** de los gauges, pulso del *finding* crítico, estados del búho.
- Tokens de easing/duración de la Fase 0; **springs** spatial (380/0.8) y effects (1600/1.0).
- **`prefers-reduced-motion`**: degradar a cross-fade corto o estado instantáneo (envolver en un hook `useReducedMotion`).

---

## 4. Fase 3 — Paso por pantalla (existentes)

La mayoría hereda de Fases 0–1. Ajustes puntuales:

| Ruta | Vista | Ajuste M3 |
|---|---|---|
| `/` , `/register`, `/reset-password`, `/invitations/[token]` | `presentation/auth` | Card `2xl`, botón pill, campos filled, mascota/owl opcional. Reusar patrón magic-link del .pen. |
| `(protected)/dashboard` | `presentation/dashboard` | Charts → paleta M3 (`--chart-1..5` ya remapeados); métricas en cards tonales; usar gauges si aplica. |
| `(protected)/members`, `/roles` | tablas | Filas más altas, hover tonal, chips de rol pill, dialog de invitación spring. |
| `(protected)/profile`, `/settings`, `/api-keys` | settings | **Settings shell** (sidebar M3 + panel); el .pen ya tiene `SettingsSidebar` y las pantallas Perfil/Equipo/API/Notificaciones como referencia 1:1. |
| `/forbidden`, `/unassigned` | estados | Estado vacío M3 (icono tonal, copy claro). |

Charts: revisar la librería (recharts/visx) y aplicar colores M3 + esquinas redondeadas en barras.

---

## 5. Fase 4 — Pantallas nuevas de Owliver (pentest)

No existen en código todavía; construirlas **directo en M3** siguiendo el `.pen` y `DESIGN.md`:
Hall of Shame `/`, Auditar URL `/scan` (+ gate de atestación), **Live Pentest Theater** `/scans/[id]` (tema `.soc`), Reporte `/scans/[id]/report`, Reporte público `/r/[token]`, Historial `/sites/[id]`, Watchlist `/watchlist`, Cómo funciona, magic-link auth. Reusar primitivos ya migrados + componentes Owliver (GradeBadge, SeverityChip, Gauge, ToolChip, OwlMascot, Footer, TopNav).

---

## 6. Riesgos y verificación

- **Contraste AA**: la paleta pastel baja el contraste de algunos pares; verificar `on-*` (texto sobre `primary`, badges, grade-scale) en light, dark y `.soc`. Sobre ámbar pastel → texto **ink**, nunca blanco.
- **Base UI ≠ Radix**: los `@custom-variant data-*` ya están adaptados a Base UI; al tocar primitivos, conservar esos selectors.
- **Tailwind v4**: todo token nuevo debe exponerse en `@theme inline` para generar utilidades.
- **shadcn updates**: documentar los primitivos personalizados; un `npx shadcn add` puede sobrescribir — fijar y revisar diffs.
- **Densidad**: pill + cards `xl` aumentan el aire; mantener variantes `sm/xs` y filas compactas donde hay volumen (tablas, queues).
- **Movimiento**: medir performance y respetar `prefers-reduced-motion`.

**QA:** snapshots visuales (Playwright/Storybook) por primitivo y ruta; auditoría a11y (axe) en los 3 temas; revisión de `globals.css` diff.

## 7. Orden de ejecución (checklist)

- [x] **F0 — hecho.** `globals.css`: roles M3 pastel (`:root`), `.dark` M3, **nuevo `.soc`**, `--radius:1rem` + `--radius-full`, roles nuevos expuestos en `@theme inline`, easing/duración M3; `layout.tsx` carga **Roboto Flex/Mono** vía `next/font`. → todas las pantallas existentes ya renderizan en M3 pastel.
- [x] **F1 — hecho.** `button` (pill + state-layer `before:bg-current` + familia Filled/Tonal/Elevated/Outlined/Text/`tertiary` + press), `card` (`rounded-2xl` tonal, sin hairline ring), `badge` (pill), `input`/`textarea` (`rounded-lg` tonal, alturas +1), `switch` (track pill + thumb que crece), `checkbox` (18px, `border-2 border-outline`), `skeleton` (tonal), `tooltip` (`rounded-lg`), `dialog` (`rounded-3xl` + scrim `black/32`), `sheet` (`bg-card` `rounded-2xl`), `tabs` (segmented pill + indicador `primary`), `toggle-group` (pill segmentado tonal), `table` (hover tonal, filas más altas), `popover`/`select`/`dropdown-menu` (superficies `rounded-xl` tonales, items `rounded-lg`, sin ring). **Pendiente menor:** `sidebar` (item activo pill tonal — el `.pen` ya tiene `SettingsSidebar` de referencia), `field` (wrapper, hereda), y `progress` wavy (componente nuevo → F4).
- [ ] **F2** capa de movimiento (lib spring + tokens + reduced-motion).
- [ ] **F3** paso por pantalla existente (dashboard/members/roles/profile/settings/api-keys/auth).
- [ ] **F4** pantallas Owliver nuevas desde el `.pen`.
- [ ] **QA** contraste AA · snapshots · a11y · diff de tokens.

**Estimación gruesa:** F0 ~0.5 día · F1 ~2–3 días · F2 ~1–2 días · F3 ~2 días · F4 (pantallas nuevas) el grueso del trabajo de producto. Las Fases 0–1 ya entregan el "look M3 Expressive" en todo lo existente.
