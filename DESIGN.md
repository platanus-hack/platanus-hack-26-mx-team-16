---
name: Owliver
description: AI-orchestrated pentest platform — Material 3 Expressive. Mercury-light-violet palette — #6858F2 UI primary, #5648E8 logo anchor, pale-purple containers + patina-teal on near-white neutrals, Albert Sans, A–F grade scale, dark SOC live-view.
register: product
designLanguage: Material 3 Expressive
colors:
  # M3 light scheme — Mercury violet + patina teal on near-white neutral (reference hex; canonical OKLCH in sidecar)
  primary: "#6858F2"                 # mercury-light-violet — filled CTAs, active nav, focus, primary charts
  on-primary: "#FFFFFF"             # white text on violet
  primary-container: "#ECE9FF"      # pale violet well — selected/hover tint (shadcn --accent)
  on-primary-container: "#1B116B"
  secondary: "#146F69"               # patina-deep teal — links, secondary actions
  on-secondary: "#FFFFFF"
  secondary-container: "#B3E3DD"
  on-secondary-container: "#00403D"
  tertiary: "#8F7CFF"                # mercury-bright — accent pop (hero CTA, owl-eyes)
  on-tertiary: "#160B6B"
  tertiary-container: "#F0EDFF"
  on-tertiary-container: "#20106F"
  violet-flash: "#A79BFF"            # violet flash — wordmark + focus glint (large/emphasis only)
  error: "#B23B1D"                   # vermilion — destructive/danger only
  on-error: "#FFFFFF"
  error-container: "#FDD3C8"
  on-error-container: "#6B1802"
  surface: "#FCFAF4"                  # warm near-white lacquer
  surface-container-low: "#F7F5EE"
  surface-container: "#F1EFE6"
  surface-container-high: "#EAE8DE"
  surface-container-highest: "#E4E1D7"
  on-surface: "#242218"
  on-surface-variant: "#58554C"
  outline: "#828078"
  outline-variant: "#D0CEC5"
  # Grade scale (pastel) — the single source of state color (A→F); data, not theme
  grade-a: "#5FC487"
  grade-b: "#9FD06E"
  grade-c: "#ECCB68"
  grade-d: "#F0A05E"
  grade-e: "#EC7E63"
  grade-f: "#E0635F"
  # SOC dark-expressive (live-view only) — warm-lacquer war-room, kintsugi neon
  soc-surface: "#090704"
  soc-surface-container: "#110F0A"
  soc-surface-container-high: "#1A1813"
  soc-outline: "#45423B"
  soc-on-surface: "#E0DED8"
  soc-on-surface-variant: "#A6A49F"
  soc-cyan: "#58CDC9"                 # patina — activity
  soc-violet: "#D1CBFF"              # mercury violet — tool running
  soc-red: "#E05C42"                 # vermilion — critical
  soc-green: "#6ECF9A"               # jade — ok
typography:
  uiFont: "Albert Sans, \"Avenir Next\", \"Helvetica Neue\", Arial, system-ui, sans-serif"
  displayFont: "Alumni Sans, \"Albert Sans\", system-ui, sans-serif"   # condensed display — landing hero + wordmark
  monoFont: "Roboto Mono, \"SFMono-Regular\", \"JetBrains Mono\", ui-monospace, Menlo, monospace"
  scale:
    display-large:  { size: "57px", line: "60px", weight: 400, tracking: "-0.5px",  font: "displayFont" }
    display-medium: { size: "45px", line: "52px", weight: 400, tracking: "-0.25px", font: "displayFont" }
    display-small:  { size: "36px", line: "44px", weight: 400, font: "displayFont" }
    headline-large: { size: "32px", line: "40px", weight: 600, tracking: "-0.25px" }   # Expressive: emphasized
    headline-medium:{ size: "28px", line: "36px", weight: 600 }
    headline-small: { size: "24px", line: "32px", weight: 600 }
    title-large:    { size: "22px", line: "28px", weight: 600 }
    title-medium:   { size: "16px", line: "24px", weight: 600, tracking: "0.15px" }
    title-small:    { size: "14px", line: "20px", weight: 600 }
    body-large:     { size: "16px", line: "24px", weight: 400 }
    body-medium:    { size: "14px", line: "20px", weight: 400 }
    body-small:     { size: "12px", line: "16px", weight: 400 }
    label-large:    { size: "14px", line: "20px", weight: 600 }                                                # button text — Albert Sans, normal case
    label-medium:   { size: "12px", line: "16px", weight: 600, tracking: "1px",   case: "uppercase", font: "monoFont" }   # eyebrow/overline/meta
    label-small:    { size: "11px", line: "16px", weight: 600, tracking: "1.2px", case: "uppercase", font: "monoFont" }
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
  level1: { surface: "{colors.surface-container-low}",     shadow: "0 1px 2px rgba(40,30,8,0.06)" }
  level2: { surface: "{colors.surface-container}",         shadow: "0 1px 3px rgba(40,30,8,0.10)" }
  level3: { surface: "{colors.surface-container-high}",    shadow: "0 2px 6px rgba(40,30,8,0.12)" }
  level4: { surface: "{colors.surface-container-high}",    shadow: "0 4px 10px rgba(40,30,8,0.14)" }
  level5: { surface: "{colors.surface-container-highest}", shadow: "0 8px 18px rgba(40,30,8,0.16)" }
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
  wordmark:        { label: "{colors.primary}", font: "displayFont", case: "uppercase", tracking: "0.15em" }
---

# Design System: Owliver — Material 3 Expressive

## 1. Overview

**Creative North Star: "The Inspection Bench, lit by Mercury violet."**

Owliver is the owl that watches over web and AI security: a user submits a URL + attack level, an Agno agent team runs a pentest, and Owliver returns an easy-to-read but technically valuable report with an **A–F grade**. The interface is still an inspection bench — every tool within reach, attention on the findings and the score, never on the chrome — but now that bench is lit by **Mercury-light violet**: a precise, modern signal that keeps the logo color `#5648E8` as the anchor and uses a lighter `#6858F2` for everyday UI. Owliver marks the active path, the primary action, and the inspection focus in violet; the signal *is* the point of view. The bench speaks **Material 3 Expressive** — tonal color, generous rounding, tactile state layers, and **motion as a first-class material**. Expressiveness here is *functional energy*, not decoration. Springs and emphasized easing make the product feel alive and confident; they never get between the reviewer and the data.

Owliver keeps its three personality pillars — **sharp, trustworthy, approachable** — and its anti-references: it is **not** a generic SaaS/admin template, **not** the trendy purple-gradient "AI-app" look (even though it runs on AI), and **not** legacy enterprise clutter. M3 Expressive supplies the structure (color roles, shape, elevation, motion); Owliver supplies the point of view (**Mercury violet** over near-white tonal surfaces, **patina-teal** as the second color, the A–F grade as the only state color, the dark SOC live-view).

**Key characteristics**
- **Dynamic tonal color** built on M3 color roles (primary/secondary/tertiary + containers, tonal surfaces), with **Mercury-light violet `#6858F2`** as UI primary, **logo violet `#5648E8`** as the anchor, and **patina teal** as the secondary color — two crisp accents on near-white neutrals.
- **Expressive shape**: large corners, pill buttons, squircle badges, and shape-morph on interaction.
- **Tonal elevation**: depth from surface-container levels + a soft (warm) shadow that grows with state — not hairline rings.
- **Motion is the system's signature**: emphasized easing + physical springs; grades count up, gauges sweep, findings spring in, the owl reacts.
- **Two themes that coexist**: the light app-shell ("claro de día") and the dark **SOC live-view** ("war room"), expressed as M3 light and dark-expressive schemes — both warm-lacquer.
- **Albert Sans** carries the UI; **Alumni Sans** sets the display/wordmark; **Roboto Mono** is the measuring tape for scores, grades, payloads, eyebrows, and telemetry.

## 2. Color

Material 3 **color roles**, not ad-hoc swatches. Every fill maps to a role so theming and contrast stay correct.

The palette is **Mercury-inspired**: **lighter UI violet `#6858F2`, logo violet `#5648E8`, pale-purple containers, and patina teal on near-white neutral surfaces.** Surfaces stay close to neutral so the product feels crisp instead of decorative; brand energy is carried by violet as the active signal, with patina as the quieter second color and the A–F grade scale reserved for status. (Values below are reference hex; the canonical OKLCH lives in `.impeccable/design.json`.)

### Core roles (light)
- **Primary** `#6858F2` (Mercury-light violet) / **on-primary** `#FFFFFF` — filled buttons, active nav, focus, primary charts. Filled CTAs are **violet container + white text** and remain AA at 4.92:1; primary text on `surface-container-low` reads 4.51:1. **Primary-container** `#ECE9FF` / on `#1B116B` for quiet wells and selected states (the hover/selected tint, a.k.a. shadcn `--accent`). The logo may still use the deeper anchor `#5648E8`.
- **Secondary** `#146F69` (patina-deep teal) + **secondary-container** `#B3E3DD` — links, tonal buttons, neutral grouped actions. As a link on paper it reads **5.74:1**; white text on the solid teal reads **5.99:1**.
- **Tertiary** `#8F7CFF` (Mercury bright) + **tertiary-container** `#F0EDFF` — the brighter violet accent pop: hero CTAs, the owl's eyes, "needs attention" emphasis. Because it is lighter, solid tertiary fills use **on-tertiary** `#160B6B`, not white.
- **Violet flash** `#A79BFF` — focus glints, strokes, and large/emphasis accents. It is reserved for emphasis, never body copy.
- **Error** `#B23B1D` (vermilion) + **error-container** `#FDD3C8` — destructive/danger only.

### Tonal surfaces (elevation by color) — warm near-white lacquer
`surface` `#FCFAF4` → `surface-container-low` `#F7F5EE` → `surface-container` `#F1EFE6` → `-high` `#EAE8DE` → `-highest` `#E4E1D7`. Text: **on-surface** `#242218` (**15.3:1**), **on-surface-variant** `#58554C` (**7.1:1**). Lines: **outline** `#828078`, **outline-variant** `#D0CEC5`.

### Grade scale — the single source of *state* color (pastel)
A `#5FC487` · B `#9FD06E` · C `#ECCB68` · D `#F0A05E` · E `#EC7E63` · F `#E0635F`. Softened to pastel, but F still reads clearly as the worst — the Hall-of-Shame red wall is gentler, not gone. This ramp is the **only** place semantic green/amber/red appears as *grade* (chips, gauges, leaderboard rows, the Hall-of-Shame "F" wall). It is intentionally **not** themed away by M3 — a grade's color is data. (It is deliberately distinct from the brand's violet/teal so a high grade never reads as "brand color.")

### SOC dark-expressive (live-view only)
The Live Pentest Theater uses an M3 **dark, warm-lacquer** scheme: surface `#090704`, container `#110F0A`, container-high `#1A1813`, outline `#45423B`, on-surface `#E0DED8` (**15:1**). Dark SOC neon, functional only — patina-cyan `#58CDC9` (activity, 10.5:1), pale Mercury violet `#D1CBFF` (tool running), vermilion `#E05C42` (critical, 5.5:1), jade `#6ECF9A` (ok, 10.6:1) — never decorative.

**Named rules.** *The Mercury-Violet Rule:* `#6858F2` marks what matters in the UI — the primary action, active path, focus, and current inspection state — while `#5648E8` remains the deeper logo anchor; if violet isn't marking attention or action, make it neutral. *The Two-Color Rule:* violet leads, patina-teal is the only second brand color (links / secondary / quiet structure); never introduce a third brand hue — vermilion is danger, the A–F ramp is data. *The Grade-Is-Data Rule:* the A–F ramp is the only semantic color; don't recolor it for mood.

## 3. Typography

**UI:** Albert Sans. **Display/Wordmark:** Alumni Sans (condensed). **Mono:** Roboto Mono. Albert Sans — a clean humanist sans — carries the full M3 type scale; Expressive leans on **emphasized weights** (600–700) for headlines and titles to add energy. Alumni Sans appears only at display sizes and in the wordmark. Pair on a contrast axis (humanist sans + condensed sans + mono), never two near-identical faces.

Scale (role · size/line · weight): **Display L/M/S** 57/45/36 · 400 · *Alumni Sans*, tight tracking — landing hero + marketing only. **Headline L/M/S** 32/28/24 · **600 (emphasized)** · Albert Sans — section + dialog titles. **Title L/M/S** 22/16/14 · 600 — card and panel headers. **Body L/M/S** 16/14/12 · 400 — dominant reading size (prose capped 65–75ch). **Label-large** 14 · 600 · Albert Sans — **button text, normal case**. **Label-medium/small** 12/11 · 600, uppercase, +1px tracking · **Roboto Mono** — eyebrows, overlines, metadata, table heads (the "measured-value" voice).

**Mono (Roboto Mono):** every **score, grade letter, percentage, payload, request/response, canary token, terminal line — and every uppercase eyebrow/overline.** It is the "this is a measured value" signal — never used for flavor.

**The Eyebrow-Is-Mono Rule.** Overlines and metadata labels are Roboto Mono, uppercase, wide-tracked — that is impeccable's signature kicker. **Button text is not**: keep it Albert Sans, normal case, so the primary affordance stays approachable, never terminal.

## 4. Shape

Material 3 **shape scale**: none 0 · xs 4 · sm 8 · md 12 · lg 16 · xl 28 · full 999. Expressive pushes corners **larger and rounder**:
- **Buttons, FABs, chips, switches → `full` (pill).**
- **Cards → `xl` (28)** for hero/feature surfaces, `lg` (16) for dense lists.
- **GradeBadge → rounded squircle** (`lg`–`xl`).
- **Shape-morph:** interactive shapes may morph from round (rest) to squircle/cookie (pressed/selected) using a spring — a hallmark Expressive flourish, used sparingly on toggles, selected chips, and the FAB.

## 5. Elevation

Depth comes from **tonal surface containers** first, a **soft warm shadow** second — never a hairline ring as the primary separator. Shadows are tinted warm (`rgba(40,30,8,…)`) to sit on the lacquer neutrals, not neutral black. Levels 0–5 map surface → surface-container-highest with a shadow that grows from `none` to `0 8px 18px rgba(40,30,8,.16)`. At rest, surfaces sit on their tonal level with a whisper shadow; **elevation responds to state** — hover/drag/focus lift a step. *The Tonal-First Rule:* if two surfaces don't separate, change their container level before reaching for a heavier shadow.

## 6. Motion & Animation (the Expressive core)

Motion is a material, not a finish. It follows the M3 **emphasized** set and **spring physics**, and always honors `prefers-reduced-motion` (transforms collapse to short cross-fades or instant state).

### Tokens
- **Easing:** `emphasized` `cubic-bezier(0.2,0,0,1)` (default), `emphasized-decelerate` `cubic-bezier(0.05,0.7,0.1,1)` (enter), `emphasized-accelerate` `cubic-bezier(0.3,0,0.8,0.15)` (exit).
- **Duration:** short 50–200ms (state layers, small), medium 250–400ms (most transitions), long 450–600ms (large/expressive), extra-long 700–1000ms (showpiece reveals).
- **Springs (Expressive):** spatial-fast 800/0.85, spatial-default 380/0.80, spatial-slow 200/0.80; effects-default 1600/1.0. **Spatial springs move things; effect springs change color/opacity.**

### Signature Owliver animations
- **Grade reveal:** the A–F letter **counts up** and the two semicircular **gauges sweep 0→value** on `emphasized-decelerate`, ~700ms. The headline grade lands with a subtle spring overshoot.
- **The violet signal:** when a finding resolves to the report, its active path is **traced in Mercury violet** — a stroke that draws on along the path (`emphasized-decelerate`), the inspection gesture made literal.
- **Finding enters the live feed:** **fade + spring slide-up** (spatial-default); **critical** findings **pulse once** in vermilion (effects spring) to demand the eye.
- **Owl mascot (activity indicator):** state changes are spring transitions — *idle* (eyes closed) → *watching* (patina-cyan eyes, slow head tilt) → *alert* (Mercury-violet eyes ignite + glow pulse). The owl is the product's heartbeat.
- **Tool chips ignite:** in the SOC theater each tool chip springs in scale and lights its status dot (idle → running violet pulse → ok green / failed red).
- **Wavy progress:** the scan progress uses the **M3 Expressive wavy/squiggly** active indicator; the wave animates along its length while running and flattens on complete.
- **Buttons/FAB:** state-layer cross-fade (short) + shape-morph on press (spring); the FAB grows/settles with spatial-default.

*The Motion-Means-Something Rule:* every animation reports a real state change (loading, arrival, severity, success). Decorative perpetual motion is banned.

## 7. Components

M3 Expressive components, themed to Owliver. Authored states: enabled / hover / focus-visible / pressed / disabled / loading, using M3 **state layers** (8/10/12%).

- **Buttons (pill / `full`):** **Filled** (primary CTA — violet container + white text, one per region), **Tonal** (secondary-container / patina), **Elevated** (level-1 shadow), **Outlined**, **Text**. Default height 40px; an **expressive large** 56px exists for hero CTAs. Label is Albert Sans, normal case. Plus **segmented button groups** for filters (grade, dimension).
- **FAB:** tertiary-container (pale violet), `shape-lg`, level-3 shadow — e.g. "Audita una URL." Morphs/extends on scroll.
- **Chips:** assist / filter / input, `shape-sm`, state layers; chip text is the mono uppercase label. **SeverityChip** is a grade-colored pill (Roboto Mono label). **ToolChip** carries a status dot (SOC).
- **Cards:** `shape-xl` (hero) / `shape-lg` (lists), tonal elevation + soft warm shadow, 24px padding. Cards are containers, not the default reflex — never nest a card in a card.
- **Text fields:** M3 **filled** style, `surface-container-highest`, rounded-top, **Mercury-violet active indicator**; same focus signature everywhere.
- **Progress:** **wavy linear** (signature) + circular determinate.
- **Wordmark:** Alumni Sans, uppercase, +0.15em tracking, in Mercury violet.
- **Owliver-specific:** **GradeBadge** (squircle, grade color, Roboto Mono), **Gauge** (semicircular, rounded, count-up), **OwlMascot** (3 motion states), **AgentLane** and **FindingFeedItem** (SOC theater), **AttestationGate** (the legal control as UI).

## 8. Do's and Don'ts

### Do
- **Do** map every color to an M3 **role** and let tonal surfaces (containers) carry elevation; add a soft warm shadow only as it rises.
- **Do** make corners large and friendly — **pill buttons, `xl` cards, squircle badges** — and use shape-morph sparingly for delight.
- **Do** treat **motion as a material**: spring physics, emphasized easing, count-up grades, the violet signal trace, spring-in findings — and always ship a `prefers-reduced-motion` fallback.
- **Do** keep **Mercury violet** for the primary action and active path, **patina teal** as the only second brand color, and the **A–F ramp** as the only semantic state color.
- **Do** fill primary buttons with **`#6858F2` + white text**; use deeper `#5648E8` for logo/anchor moments and reserve bright violet `#A79BFF` for strokes and large/emphasis accents — never body copy on paper.
- **Do** drive type hierarchy with Albert Sans weight at the M3 scale; set display in Alumni Sans; reserve Roboto Mono for measured values, payloads, grades, and uppercase eyebrows.
- **Do** author every interaction state with M3 state layers and one consistent focus ring.

### Don't
- **Don't** revert to hairline-ring-as-primary-separator, tiny radii, or flat-static surfaces — that's the old system, not Expressive.
- **Don't** animate for decoration; every motion must report a real state change (no perpetual ambient motion).
- **Don't** recolor the grade scale for mood, introduce a third brand hue, or spend violet on anything that isn't a primary action, active state, focus, or the wordmark.
- **Don't** set body text in bright violet `#A79BFF`, or use mono-uppercase on button labels — keep buttons Albert Sans and approachable.
- **Don't** drift into the **purple-gradient AI-app** look, **generic SaaS** card grids, or **legacy enterprise** clutter. Expressive ≠ noisy.
- **Don't** use `clamp()`/fluid headings in the app shell (display sizes on marketing surfaces only), or on-surface-variant text below 4.5:1 contrast; keep AA in both light and SOC themes.
