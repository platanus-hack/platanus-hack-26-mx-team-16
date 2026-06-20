---
name: Doxiq
description: Document extraction and business-rule analysis — trustworthy structured data at volume.
colors:
  teal-primary: "oklch(0.59 0.095 180.54)"
  teal-deep: "oklch(0.468 0.074 180.8)"
  teal-tint: "oklch(0.951 0.018 186.07)"
  ink: "oklch(0.222 0.029 253.225)"
  surface: "oklch(0.984 0.002 252.121)"
  card: "oklch(1 0 0)"
  muted: "oklch(0.945 0.005 252.232)"
  muted-foreground: "oklch(0.558 0.025 252.534)"
  border: "oklch(0.905 0.011 252.311)"
  on-primary: "oklch(1 0 0)"
  success: "oklch(0.626 0.139 155.038)"
  warning: "oklch(0.77 0.18 75.998)"
  destructive: "oklch(0.579 0.214 27.166)"
typography:
  display:
    fontFamily: "Figtree, Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.875rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Figtree, Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.005em"
  title:
    fontFamily: "Figtree, Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 500
    lineHeight: 1.5
    letterSpacing: "normal"
  body:
    fontFamily: "Figtree, Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "Figtree, Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: "normal"
  mono:
    fontFamily: "Geist Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
rounded:
  sm: "8px"
  md: "10px"
  lg: "12px"
  xl: "16px"
  "2xl": "20px"
spacing:
  xs: "6px"
  sm: "10px"
  md: "16px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.teal-primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.md}"
    padding: "0 10px"
    height: "40px"
  button-outline:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "0 10px"
    height: "40px"
  button-ghost:
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "0 10px"
    height: "40px"
  input:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "4px 10px"
    height: "36px"
  card:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.xl}"
    padding: "24px"
  badge:
    backgroundColor: "{colors.teal-tint}"
    textColor: "{colors.teal-deep}"
    rounded: "{rounded.md}"
    padding: "2px 8px"
---

# Design System: Doxiq

## 1. Overview

**Creative North Star: "The Inspection Bench"**

Doxiq is a workstation for examining documents: each one is pulled up, measured against the extracted data, corrected, and signed off. The interface should feel like a well-organized bench where every tool is within reach and nothing decorative competes for the eye. The reviewer's attention belongs on the document and the numbers, never on the chrome. Teal is the bench's single instrument light: it marks what is active, selected, or needs attention, and it stays rare so it keeps meaning.

The system is **tactile and confident** without being loud. Surfaces are real and pressable: solid primary buttons, clearly stateful controls, hairline-ringed cards that can lift a touch on interaction. Density is welcomed where reviewers work at volume (queues, tables, side-by-side document panels) and relaxes where non-technical admins configure doctypes and rules. The feeling to chase is quiet competence: the tool earns trust by getting out of the way and by never showing a value it can't stand behind.

This system explicitly rejects three failures. It is not a **generic SaaS / admin-kit template** (identical card grids, icon + heading + text repeated with no point of view). It does not cosplay as **the trendy AI-app look** (purple gradients, glassmorphism, gradient text, chatbot-forward layouts) even though Doxiq runs on AI. And it is not **legacy enterprise clutter** (gray-on-gray, cramped toolbars, dated chrome). Density yes; clutter no.

**Key Characteristics:**
- One teal instrument light on a cool-gray bench; the accent is rare and always meaningful.
- Near-flat depth: surfaces separated by hairline rings and whisper shadows, lifting only in response to state.
- One type family (Figtree) doing all the work, mono (Geist Mono) reserved for raw extracted values, IDs, and code.
- Keyboard-first, dense-where-it-helps, calm-where-it-configures.
- Provenance and confidence are visible on extracted data, never hidden.

## 2. Colors

A cool-neutral bench lit by a single muted teal, with a tight, unambiguous state vocabulary.

### Primary
- **Doxiq Teal** (`oklch(0.59 0.095 180.54)`): the instrument light. Primary buttons, current selection, focus rings, active nav, the chart-1 series. Used on a small fraction of any screen on purpose.
- **Teal Deep** (`oklch(0.468 0.074 180.8)`): text and icons that sit on teal tints; the readable end of the teal ramp for emphasis on light surfaces.
- **Teal Tint** (`oklch(0.951 0.018 186.07)`): the soft accent fill for badges, selected rows, hover wells, and quiet highlights where solid teal would shout.

### Neutral
- **Ink** (`oklch(0.222 0.029 253.225)`): primary text. Cool near-black; carries body and headings on the surface.
- **Surface** (`oklch(0.984 0.002 252.121)`): the app background. A true-cool off-white, not a warm cream.
- **Card** (`oklch(1 0 0)`): pure white content surfaces that sit a step above the surface.
- **Muted** (`oklch(0.945 0.005 252.232)`) / **Muted Foreground** (`oklch(0.558 0.025 252.534)`): secondary fills (hover wells, disabled tracks) and secondary text. Keep muted-foreground for metadata, never for primary reading.
- **Border** (`oklch(0.905 0.011 252.311)`): hairlines, input strokes, dividers.

### State
- **Success** (`oklch(0.626 0.139 155.038)`): rule passed, high confidence, applied. Solid green for affirmative actions.
- **Warning** (`oklch(0.77 0.18 75.998)`): low confidence, needs-review, soft-fail. Amber, used to draw a reviewer's eye, not to alarm.
- **Destructive** (`oklch(0.579 0.214 27.166)`): errors and irreversible actions. Note the soft treatment in components: destructive buttons use a 10% tint with red text, not a solid red slab. Solid destructive is reserved for genuine danger.

### Named Rules
**The One Light Rule.** Doxiq Teal appears on ≤10% of any screen. It means active, selected, or primary-action. If teal is decorating something that isn't one of those, remove it.

**The Cool Bench Rule.** Every neutral leans cool (hue ~252). Never introduce a warm cream/sand/beige surface; warmth here reads as a different product.

## 3. Typography

**Display / Body Font:** Figtree (with Geist, then `ui-sans-serif, system-ui` fallbacks)
**Label/Mono Font:** Geist Mono (with `ui-monospace, SFMono-Regular, Menlo` fallbacks)

**Character:** One humanist sans carries the entire interface, from page titles to dense table cells, leaning on weight and size for hierarchy rather than a second face. Geist Mono is the bench's measuring tape: raw extracted values, document IDs, JSON, and code, where character alignment and an unmistakable "this is data" signal matter.

### Hierarchy
- **Display** (600, 1.875rem / 30px, line-height 1.15): rare page-level titles. Fixed rem, never fluid; a sidebar-shrinking hero is wrong here.
- **Headline** (600, 1.5rem / 24px, line-height 1.2): section and dialog titles.
- **Title** (500, 1rem / 16px, line-height 1.5): card titles, panel headers, the most common heading weight in the app.
- **Body** (400, 0.875rem / 14px, line-height 1.5): the dominant UI and reading size. Cap prose at 65–75ch; data and table content may run denser.
- **Label** (500, 0.75rem / 12px, line-height 1.3): field labels, badges, metadata, table column heads.
- **Mono** (400, 0.8125rem / 13px): extracted raw values, IDs, JSON, code.

### Named Rules
**The Fixed-Scale Rule.** Type sizes are fixed rem with a tight ~1.2 ratio. No `clamp()` headings in product UI; users view at consistent DPI and fluid type only adds noise.

**The One-Voice Type Rule.** Figtree does headings, buttons, labels, and body. Reach for Geist Mono only when the content is literally data or code, never for flavor.

## 4. Elevation

The bench is near-flat. Depth is conveyed by a **hairline ring** (a 1px ring at ~10% ink) plus a **whisper shadow** (`shadow-xs`), not by lifted, heavily-shadowed cards. Cards use a ring rather than a hard border, which reads cleaner against the cool surface. In keeping with the "tactile and confident" direction, elevation is allowed to *respond to state*: an interactive surface may deepen its shadow slightly on hover or while dragged, but at rest everything sits low and quiet.

### Shadow Vocabulary
- **Whisper** (`box-shadow: 0 1px 2px rgba(0,0,0,0.05)`): the resting elevation for cards, inputs, and outline buttons. Barely there, just enough to separate from the surface.
- **Hairline ring** (`box-shadow: inset 0 0 0 1px color-mix(in oklch, var(--foreground) 10%, transparent)`): the structural separator for cards and raised panels; preferred over a solid border.

### Named Rules
**The Hairline Rule.** Surfaces are separated by a 1px hairline ring at 10% ink, not by heavy drop shadows. If a card needs a strong shadow to be legible, the contrast with the surface is wrong, fix that first.

**The State-Lift Rule.** Resting surfaces are low and flat. A shadow that grows is feedback (hover, drag, focus), never decoration.

## 5. Components

Components read as **tactile and confident**: solid where they act, hairline-quiet where they contain, with every interactive state actually authored (default, hover, focus-visible, active, disabled, loading). Built on Base UI primitives + class-variance-authority; one shape vocabulary across every screen.

### Buttons
- **Shape:** gently rounded (`rounded-md`, 10px). Heights step 24 / 32 / 40 / 44px (xs / sm / default / xl); default is 40px.
- **Primary:** solid Doxiq Teal, white text, hover dims to 80% opacity. The single most assertive control on a screen; one per region.
- **Outline:** surface background, hairline border, whisper shadow; hover fills to muted. The workhorse for secondary actions.
- **Ghost:** transparent until hovered (fills to muted); for tertiary and toolbar actions where chrome should stay minimal.
- **Secondary:** muted-gray fill for neutral grouped actions.
- **Destructive:** soft by default, a 10% red tint with red text, escalating only for truly dangerous actions.
- **Success:** solid green, for affirmative confirmations (approve, apply).
- **Focus / Disabled:** focus-visible draws a 3px teal ring at 50% plus a teal border; disabled drops to 50% opacity and removes pointer events.

### Chips / Badges
- **Style:** teal-tint fill with teal-deep text for the default/identity badge; state badges borrow success / warning / destructive at low chroma fills.
- **Use:** status (passed / needs-review / failed), confidence bands, and counts. Pill-to-`rounded-md`, label type (12px, 500).

### Cards / Containers
- **Corner Style:** `rounded-xl` (16px).
- **Background:** white card on the cool surface.
- **Separation:** hairline `ring-1` at 10% ink plus whisper shadow (see Elevation), not a hard border.
- **Internal Padding:** 24px (lg); compact `data-size="sm"` drops to 16px with tighter gaps.
- **Rule:** cards are containers, not the default layout reflex. Never nest a card inside a card.

### Inputs / Fields
- **Style:** white fill, hairline border, `rounded-md`, whisper shadow; 36px default height (lg 40, xl 44).
- **Focus:** border shifts to teal and a 3px teal-at-50% ring appears. The same focus signature as buttons, for one consistent keyboard story.
- **Placeholder:** muted-foreground at full 4.5:1 contrast, never lighter "for elegance."
- **Error / Disabled:** `aria-invalid` paints a destructive ring + border; disabled drops opacity and blocks pointers.

### Navigation
- **Sidebar:** its own slightly-distinct neutral layer (`--sidebar`), `rounded-md` (8px) items at 32px height, label type.
- **States:** hover fills to sidebar-accent; the active route uses sidebar-accent fill with accent-foreground text. One active item, clearly marked, never two.

### Signature: Confidence & Provenance
The trust principle made visible. Extracted values carry a small confidence indicator (a dot + percentage) coloured by band, success at high confidence, warning at low, and link back to where in the source document the value came from. A value Doxiq is unsure about must *look* unsure; never render a low-confidence extraction with the same authority as a verified one.

## 6. Do's and Don'ts

### Do:
- **Do** keep Doxiq Teal on ≤10% of any screen, reserved for active / selected / primary-action (The One Light Rule).
- **Do** separate surfaces with the 1px hairline ring at 10% ink and a whisper shadow; let shadow grow only as state feedback.
- **Do** drive hierarchy with Figtree weight + fixed-rem size at a ~1.2 ratio; reserve Geist Mono for actual data and code.
- **Do** author every interactive state (hover, focus-visible, active, disabled, loading) and use the shared 3px teal focus ring everywhere for a keyboard-first story.
- **Do** make low-confidence extractions visibly uncertain and link values back to their place in the source document.
- **Do** use skeletons for loading content, empty states that teach the interface, and density where reviewers work at volume.

### Don't:
- **Don't** ship a **generic SaaS / admin-kit template**: identical card grids, icon + heading + text repeated endlessly with no point of view.
- **Don't** reach for the **trendy AI-app look**: purple gradients, glassmorphism, gradient text, chatbot-forward layouts. Doxiq uses AI; it must not cosplay as one.
- **Don't** drift into **legacy enterprise clutter**: gray-on-gray, cramped toolbars, dated chrome. Density is fine; clutter is not.
- **Don't** use `background-clip: text` gradient text, or a `border-left` / `border-right` > 1px colored side-stripe on cards, list items, or alerts. Use full hairline rings, background tints, or leading icons instead.
- **Don't** introduce a warm cream / sand / beige surface; every neutral stays cool (hue ~252).
- **Don't** nest cards, default to a modal before exhausting inline / progressive options, or render a low-confidence value with full authority.
- **Don't** use `clamp()` / fluid headings or muted-gray body text below 4.5:1 contrast.
