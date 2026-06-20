---
name: Owliver
description: AI-orchestrated pentest platform — Material 3 Expressive. Teal primary, amber "owl-eyes" accent, A–F grade scale, dark SOC live-view.
register: product
designLanguage: Material 3 Expressive
colors:
  # M3 light scheme — pastel-expressive variant (reference hex)
  primary: "#2C857A"
  on-primary: "#FFFFFF"
  primary-container: "#BEF3E8"
  on-primary-container: "#00201C"
  secondary: "#5C7A74"
  secondary-container: "#D9EDE8"
  on-secondary-container: "#101F1C"
  tertiary: "#FFC95C"          # the "owl-eyes" amber (pastel)
  tertiary-container: "#FFE9BC"
  on-tertiary-container: "#2A1F00"
  error: "#E5736E"
  error-container: "#FCE0DE"
  surface: "#F2FAF7"
  surface-container-low: "#ECF6F2"
  surface-container: "#E6F1ED"
  surface-container-high: "#E0ECE8"
  surface-container-highest: "#DAE7E2"
  on-surface: "#1E2B27"
  on-surface-variant: "#46524E"
  outline: "#76827D"
  outline-variant: "#C6D2CC"
  # Grade scale (pastel) — the single source of state color (A→F)
  grade-a: "#5FC487"
  grade-b: "#9FD06E"
  grade-c: "#ECCB68"
  grade-d: "#F0A05E"
  grade-e: "#EC7E63"
  grade-f: "#E0635F"
  # SOC dark-expressive (live-view only)
  soc-surface: "#121A18"
  soc-surface-container: "#1E2623"
  soc-outline: "#34403B"
  soc-on-surface: "#DCE6E2"
  soc-on-surface-variant: "#8A958F"
  soc-cyan: "#86DEDE"
  soc-amber: "#F4C77E"
  soc-red: "#EF8A86"
  soc-green: "#92DCA8"
typography:
  uiFont: "Roboto Flex, Roboto, ui-sans-serif, system-ui, sans-serif"
  monoFont: "Roboto Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
  scale:
    display-large:  { size: "57px", line: "64px", weight: 400, tracking: "-0.25px" }
    display-medium: { size: "45px", line: "52px", weight: 400 }
    display-small:  { size: "36px", line: "44px", weight: 400 }
    headline-large: { size: "32px", line: "40px", weight: 600 }   # Expressive: emphasized
    headline-medium:{ size: "28px", line: "36px", weight: 600 }
    headline-small: { size: "24px", line: "32px", weight: 600 }
    title-large:    { size: "22px", line: "28px", weight: 500 }
    title-medium:   { size: "16px", line: "24px", weight: 600, tracking: "0.15px" }
    title-small:    { size: "14px", line: "20px", weight: 600 }
    body-large:     { size: "16px", line: "24px", weight: 400 }
    body-medium:    { size: "14px", line: "20px", weight: 400 }
    body-small:     { size: "12px", line: "16px", weight: 400 }
    label-large:    { size: "14px", line: "20px", weight: 600 }
    label-medium:   { size: "12px", line: "16px", weight: 600, tracking: "0.5px" }
    label-small:    { size: "11px", line: "16px", weight: 600, tracking: "0.5px" }
shape:
  none: "0px"
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "28px"
  full: "999px"
  note: "Expressive favors larger corners and shape-morph (round at rest ↔ squircle/cookie on press)."
elevation:
  # M3 tonal elevation — surface containers carry depth; soft shadow only as it rises.
  level0: { surface: "{colors.surface}",                  shadow: "none" }
  level1: { surface: "{colors.surface-container-low}",     shadow: "0 1px 2px rgba(0,0,0,0.06)" }
  level2: { surface: "{colors.surface-container}",         shadow: "0 1px 3px rgba(0,0,0,0.10)" }
  level3: { surface: "{colors.surface-container-high}",    shadow: "0 2px 6px rgba(0,0,0,0.12)" }
  level4: { surface: "{colors.surface-container-high}",    shadow: "0 4px 10px rgba(0,0,0,0.14)" }
  level5: { surface: "{colors.surface-container-highest}", shadow: "0 8px 18px rgba(0,0,0,0.16)" }
  stateLayer: { hover: "8% on-color overlay", focus: "10%", pressed: "12%", dragged: "16%" }
motion:
  duration:
    short1: 50ms   short2: 100ms  short3: 150ms  short4: 200ms
    medium1: 250ms medium2: 300ms medium3: 350ms medium4: 400ms
    long1: 450ms   long2: 500ms   long3: 550ms   long4: 600ms
    extra-long: "700–1000ms"
  easing:
    emphasized: "cubic-bezier(0.2, 0.0, 0, 1.0)"
    emphasized-decelerate: "cubic-bezier(0.05, 0.7, 0.1, 1.0)"
    emphasized-accelerate: "cubic-bezier(0.3, 0.0, 0.8, 0.15)"
    standard: "cubic-bezier(0.2, 0.0, 0, 1.0)"
  spring:
    spatial-fast:    { stiffness: 800, damping: 0.85 }
    spatial-default: { stiffness: 380, damping: 0.80 }
    spatial-slow:    { stiffness: 200, damping: 0.80 }
    effects-default: { stiffness: 1600, damping: 1.0 }
components:
  button-filled:   { container: "{colors.primary}",            label: "{colors.on-primary}",            shape: "{shape.full}", height: "40px", stateLayer: "on-primary 8/10/12%" }
  button-tonal:    { container: "{colors.secondary-container}", label: "{colors.on-secondary-container}", shape: "{shape.full}", height: "40px" }
  button-elevated: { container: "{colors.surface-container-low}", label: "{colors.primary}", shape: "{shape.full}", height: "40px", shadow: "{elevation.level1.shadow}" }
  button-outlined: { container: "transparent", label: "{colors.primary}", border: "1px {colors.outline}", shape: "{shape.full}", height: "40px" }
  button-text:     { container: "transparent", label: "{colors.primary}", shape: "{shape.full}", height: "40px" }
  fab:             { container: "{colors.tertiary-container}", icon: "{colors.on-tertiary-container}", shape: "{shape.lg}", size: "56px", shadow: "{elevation.level3.shadow}" }
  chip:            { container: "{colors.surface-container}", label: "{colors.on-surface-variant}", shape: "{shape.sm}", height: "32px" }
  card:            { container: "{colors.surface-container-low}", shape: "{shape.xl}", padding: "24px", shadow: "{elevation.level1.shadow}" }
  text-field:      { container: "{colors.surface-container-highest}", shape: "{shape.xs}-top", indicator: "{colors.primary}", height: "56px" }
  progress-linear: { track: "{colors.surface-container-highest}", active: "{colors.primary}", style: "WAVY/squiggly active line (M3 Expressive signature)", shape: "{shape.full}" }
  switch:          { track: "{colors.surface-container-highest}", thumbOn: "{colors.on-primary}", trackOn: "{colors.primary}", shape: "{shape.full}" }
  grade-badge:     { container: "{colors.grade-*}", label: "Roboto Mono", shape: "{shape.lg}–{shape.xl} squircle" }
  gauge:           { track: "{colors.surface-container-highest}", value: "{colors.grade-*}", style: "semicircular, rounded caps, count-up" }
---

# Design System: Owliver — Material 3 Expressive

## 1. Overview

**Creative North Star: "The Inspection Bench," rebuilt in Material 3 Expressive.**

Owliver is the owl that watches over web and AI security: a user submits a URL + attack level, an Agno agent team runs a pentest, and Owliver returns an easy-to-read but technically valuable report with an **A–F grade**. The interface is still an inspection bench — every tool within reach, attention on the findings and the score, never on the chrome — but now that bench speaks **Material 3 Expressive**: tonal color, generous rounding, tactile state layers, and **motion as a first-class material**. Expressiveness here is *functional energy*, not decoration. Springs and emphasized easing make the product feel alive and confident; they never get between the reviewer and the data.

Owliver keeps its three personality pillars — **sharp, trustworthy, approachable** — and its anti-references: it is **not** a generic SaaS/admin template, **not** the trendy purple "AI-app" look (even though it runs on AI), and **not** legacy enterprise clutter. M3 Expressive supplies the structure (color roles, shape, elevation, motion); Owliver supplies the point of view (teal instrument-light, amber owl-eyes, the A–F grade as the only state color, the dark SOC live-view).

**Key characteristics**
- **Dynamic tonal color** built on M3 color roles (primary/secondary/tertiary + containers, tonal surfaces), with **teal** as primary and **amber = "the owl's eyes"** as tertiary.
- **Expressive shape**: large corners, pill buttons, squircle badges, and shape-morph on interaction.
- **Tonal elevation**: depth from surface-container levels + a soft shadow that grows with state — not hairline rings.
- **Motion is the system's signature**: emphasized easing + physical springs; grades count up, gauges sweep, findings spring in, the owl reacts.
- **Two themes that coexist**: the light app-shell ("claro de día") and the dark **SOC live-view** ("war room"), expressed as M3 light and dark-expressive schemes.
- **Roboto Flex** carries the UI; **Roboto Mono** is the measuring tape for scores, grades, payloads, and telemetry.

## 2. Color

Material 3 **color roles**, not ad-hoc swatches. Every fill maps to a role so theming and contrast stay correct.

The palette is the **pastel-expressive variant**: softer, lower-chroma tones that keep M3 contrast (filled-button and badge text stay legible) while feeling lighter and friendlier.

### Core roles (light)
- **Primary** `#2C857A` / **on-primary** `#FFFFFF` — the instrument light: filled buttons, active nav, focus, primary charts. **Primary-container** `#BEF3E8` / on `#00201C` for quiet teal wells and selected states.
- **Secondary** `#5C7A74` + **secondary-container** `#D9EDE8` — tonal buttons and neutral grouped actions.
- **Tertiary** `#FFC95C` ("**owl-eyes amber**", pastel) + **tertiary-container** `#FFE9BC` — the energetic accent: hero CTAs, the owl's eyes, "needs attention" emphasis. Rare and meaningful; on a pastel amber, label text is **ink**, never white.
- **Error** `#E5736E` + **error-container** `#FCE0DE` — destructive/danger only.

### Tonal surfaces (elevation by color)
`surface` `#F2FAF7` → `surface-container-low` `#ECF6F2` → `surface-container` `#E6F1ED` → `-high` `#E0ECE8` → `-highest` `#DAE7E2`. Text: **on-surface** `#1E2B27`, **on-surface-variant** `#46524E`. Lines: **outline** `#76827D`, **outline-variant** `#C6D2CC`.

### Grade scale — the single source of *state* color (pastel)
A `#5FC487` · B `#9FD06E` · C `#ECCB68` · D `#F0A05E` · E `#EC7E63` · F `#E0635F`. Softened to pastel, but F still reads clearly as the worst — the Hall-of-Shame red wall is gentler, not gone. This ramp is the **only** place semantic red/amber/green appears (chips, gauges, leaderboard rows, the Hall-of-Shame "F" wall). It is intentionally **not** themed away by M3 — a grade's color is data.

### SOC dark-expressive (live-view only)
The Live Pentest Theater uses an M3 **dark, pastel-neon** scheme: surface `#121A18`, container `#1E2623`, outline `#34403B`, on-surface `#DCE6E2`. Functional neon, softened to pastel — cyan `#86DEDE` (activity), amber `#F4C77E` (tool running), red `#EF8A86` (critical), green `#92DCA8` (ok) — never decorative.

**Named rules.** *The Owl-Eyes Rule:* tertiary amber is reserved for the primary CTA and the owl's "alert" state; if amber isn't drawing the eye to an action or an alert, make it teal or neutral. *The Grade-Is-Data Rule:* the A–F ramp is the only semantic color; don't recolor it for mood.

## 3. Typography

**UI:** Roboto Flex. **Mono:** Roboto Mono. One variable family carries the full M3 type scale; Expressive leans on **emphasized weights** (600–700) for headlines and labels to add energy without a second face.

Scale (role · size/line · weight): **Display L** 57/64 · 400 — landing hero only. **Headline L/M/S** 32/28/24 · **600 (emphasized)** — section + dialog titles. **Title L/M/S** 22/16/14 · 500–600 — card and panel headers. **Body L/M/S** 16/14/12 · 400 — dominant reading size. **Label L/M/S** 14/12/11 · 600, +0.5px tracking — buttons, chips, metadata, table heads.

**Mono (Roboto Mono):** every **score, grade letter, percentage, payload, request/response, canary token, and terminal line.** It is the "this is a measured value" signal — never used for flavor.

## 4. Shape

Material 3 **shape scale**: none 0 · xs 4 · sm 8 · md 12 · lg 16 · xl 28 · full 999. Expressive pushes corners **larger and rounder**:
- **Buttons, FABs, chips, switches → `full` (pill).**
- **Cards → `xl` (28)** for hero/feature surfaces, `lg` (16) for dense lists.
- **GradeBadge → rounded squircle** (`lg`–`xl`).
- **Shape-morph:** interactive shapes may morph from round (rest) to squircle/cookie (pressed/selected) using a spring — a hallmark Expressive flourish, used sparingly on toggles, selected chips, and the FAB.

## 5. Elevation

Depth comes from **tonal surface containers** first, a **soft shadow** second — never a hairline ring as the primary separator. Levels 0–5 map surface → surface-container-highest with a shadow that grows from `none` to `0 8px 18px rgba(0,0,0,.16)`. At rest, surfaces sit on their tonal level with a whisper shadow; **elevation responds to state** — hover/drag/focus lift a step. *The Tonal-First Rule:* if two surfaces don't separate, change their container level before reaching for a heavier shadow.

## 6. Motion & Animation (the Expressive core)

Motion is a material, not a finish. It follows the M3 **emphasized** set and **spring physics**, and always honors `prefers-reduced-motion` (transforms collapse to short cross-fades or instant state).

### Tokens
- **Easing:** `emphasized` `cubic-bezier(0.2,0,0,1)` (default), `emphasized-decelerate` `cubic-bezier(0.05,0.7,0.1,1)` (enter), `emphasized-accelerate` `cubic-bezier(0.3,0,0.8,0.15)` (exit).
- **Duration:** short 50–200ms (state layers, small), medium 250–400ms (most transitions), long 450–600ms (large/expressive), extra-long 700–1000ms (showpiece reveals).
- **Springs (Expressive):** spatial-fast 800/0.85, spatial-default 380/0.80, spatial-slow 200/0.80; effects-default 1600/1.0. **Spatial springs move things; effect springs change color/opacity.**

### Signature Owliver animations
- **Grade reveal:** the A–F letter **counts up** and the two semicircular **gauges sweep 0→value** on `emphasized-decelerate`, ~700ms. The headline grade lands with a subtle spring overshoot.
- **Finding enters the live feed:** **fade + spring slide-up** (spatial-default); **critical** findings **pulse once** in red (effects spring) to demand the eye.
- **Owl mascot (activity indicator):** state changes are spring transitions — *idle* (eyes closed) → *watching* (cyan eyes, slow head tilt) → *alert* (amber eyes ignite + glow pulse). The owl is the product's heartbeat.
- **Tool chips ignite:** in the SOC theater each tool chip springs in scale and lights its status dot (idle → running amber pulse → ok green / failed red).
- **Wavy progress:** the scan progress uses the **M3 Expressive wavy/squiggly** active indicator; the wave animates along its length while running and flattens on complete.
- **Buttons/FAB:** state-layer cross-fade (short) + shape-morph on press (spring); the FAB grows/settles with spatial-default.

*The Motion-Means-Something Rule:* every animation reports a real state change (loading, arrival, severity, success). Decorative perpetual motion is banned.

## 7. Components

M3 Expressive components, themed to Owliver. Authored states: enabled / hover / focus-visible / pressed / disabled / loading, using M3 **state layers** (8/10/12%).

- **Buttons (pill / `full`):** **Filled** (primary CTA — one per region), **Tonal** (secondary-container), **Elevated** (level-1 shadow), **Outlined**, **Text**. Default height 40px; an **expressive large** 56px exists for hero CTAs. Plus **segmented button groups** for filters (grade, dimension).
- **FAB:** tertiary-container, `shape-lg`, level-3 shadow — e.g. "Audita una URL." Morphs/extends on scroll.
- **Chips:** assist / filter / input, `shape-sm`, state layers. **SeverityChip** is a grade-colored pill (Roboto Mono label). **ToolChip** carries a status dot (SOC).
- **Cards:** `shape-xl` (hero) / `shape-lg` (lists), tonal elevation + soft shadow, 24px padding. Cards are containers, not the default reflex — never nest a card in a card.
- **Text fields:** M3 **filled** style, `surface-container-highest`, rounded-top, teal active indicator; same focus signature everywhere.
- **Progress:** **wavy linear** (signature) + circular determinate.
- **Owliver-specific:** **GradeBadge** (squircle, grade color, Roboto Mono), **Gauge** (semicircular, rounded, count-up), **OwlMascot** (3 motion states), **AgentLane** and **FindingFeedItem** (SOC theater), **AttestationGate** (the legal control as UI).

## 8. Do's and Don'ts

### Do
- **Do** map every color to an M3 **role** and let tonal surfaces (containers) carry elevation; add a soft shadow only as it rises.
- **Do** make corners large and friendly — **pill buttons, `xl` cards, squircle badges** — and use shape-morph sparingly for delight.
- **Do** treat **motion as a material**: spring physics, emphasized easing, count-up grades, spring-in findings — and always ship a `prefers-reduced-motion` fallback.
- **Do** keep **amber (tertiary)** for the primary CTA and the owl's alert, and the **A–F ramp** as the only semantic state color.
- **Do** drive type hierarchy with Roboto Flex weight at the M3 scale; reserve Roboto Mono for measured values, payloads, and grades.
- **Do** author every interaction state with M3 state layers and one consistent focus ring.

### Don't
- **Don't** revert to hairline-ring-as-primary-separator, tiny radii, or flat-static surfaces — that's the old system, not Expressive.
- **Don't** animate for decoration; every motion must report a real state change (no perpetual ambient motion).
- **Don't** recolor the grade scale for mood, or spend amber on anything that isn't a primary action or an alert.
- **Don't** drift into the **purple AI-app** look, **generic SaaS** card grids, or **legacy enterprise** clutter. Expressive ≠ noisy.
- **Don't** use `clamp()`/fluid headings or on-surface-variant text below 4.5:1 contrast; keep AA in both light and SOC themes.
