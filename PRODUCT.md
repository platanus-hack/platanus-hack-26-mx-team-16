# Product

## Register

product

## Users

Doxiq serves four roles inside a tenant, frequently overlapping at smaller customers:

- **Ops / back-office reviewers** — process documents at volume. They live in the queue: open a document, check extracted fields against the source, correct errors, approve. Their context is repetitive, high-throughput work where every extra click compounds.
- **Compliance / risk analysts** — verify extracted data against business rules, investigate flagged cases, and need a defensible audit trail. Their context is scrutiny: they must be able to trust a value and show why a rule passed or failed.
- **Admins / configurers** — set up document types, analysis rules, the knowledge base, members, and integrations. Often not developers. Their context is occasional but high-stakes setup that the whole pipeline depends on.
- **Developers / integrators** — wire Doxiq into other systems via the API and integrations, and manage data sources.

The center of gravity is the **review-and-correct extraction** task; the document-detail view is the heart of the app.

## Product Purpose

Doxiq (by Llamitai) extracts structured data from documents using OCR + LLM, then evaluates configurable business rules against that data. It exists to turn piles of unstructured documents into trustworthy, structured case data with rule outcomes attached, at volume, with as little manual correction as possible.

Success looks like: reviewers clear queues fast with high confidence the extracted data is correct; analysts trust the numbers and can stand behind them; and non-developer admins configure new document types and rules without fear of breaking the pipeline.

## Brand Personality

Three words: **sharp, trustworthy, approachable.**

- **Sharp & efficient** — dense where density helps, fast, keyboard-first. Respects the reviewer clearing their hundredth document of the day.
- **Trustworthy & rigorous** — the interface conveys "this value is correct and auditable." Confidence without flash; provenance and state are visible, nothing is silently wrong.
- **Approachable & clear** — plain language and friendly affordances so non-technical configurers act with confidence.

Emotional goal: quiet competence. The tool earns trust by getting out of the way, not by decorating itself.

## Anti-references

- **Generic SaaS / admin-kit templates** — identical card grids, icon + heading + text repeated endlessly, no point of view. Familiar is fine; characterless is not.
- **The trendy AI-app look** — purple gradients, glassmorphism, gradient text, chatbot-forward layouts. Doxiq uses AI; it should not cosplay as "an AI app."
- **Legacy enterprise clutter** — SAP / old-ERP density done badly: gray-on-gray, cramped toolbars, dated chrome. Density yes, clutter no.

## Design Principles

1. **The number must be trustworthy.** Extracted values carry visible provenance and confidence; surface uncertainty rather than hiding it. A wrong value shown confidently is the worst outcome.
2. **Disappear into the review.** The primary path is read → verify → correct → approve. Every screen on it minimizes clicks, supports the keyboard, and keeps source and extraction side by side. The tool is invisible when it works.
3. **Configuration without fear.** Doctype, rule, and knowledge-base authoring is high-stakes and done by non-developers. Make it legible, reversible, and validated before it reaches the pipeline.
4. **One vocabulary, every screen.** Ops, compliance, admin, and developer surfaces share one component language. The same control means the same thing everywhere; consistency is the feature, surprise is the bug.
5. **Earned restraint.** Avoid all three traps at once (template blandness, AI gloss, enterprise clutter). Quiet and confident, with a single teal point of view that carries identity, not decoration.

## Accessibility & Inclusion

- **Target: WCAG 2.1 AA.** Contrast ≥4.5:1 for body text, visible focus states, labelled controls, semantic structure throughout.
- **Keyboard-first.** Power reviewers need full keyboard navigation and shortcuts for the review / correct / approve loop, not mouse-only flows.
- **Reduced motion** honored as a baseline: motion conveys state (loading, transition, feedback), never decoration, and every animation has a `prefers-reduced-motion` alternative.
