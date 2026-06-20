# Product

## Register

product

## Users

Doxiq is a multi-tenant SaaS boilerplate; out of the box it serves two roles inside a tenant:

- **Tenant admins** — set up the workspace, invite members, define roles and permissions, and manage tenant settings. Their context is occasional but high-stakes setup that everyone else depends on.
- **Members** — sign in, work inside the tenant, and use whatever product surfaces a builder adds on top of the boilerplate. Their context is everyday use of the authenticated app.

The center of gravity is everything a real product shares before it has features: signing in, belonging to a tenant, and managing who can do what.

## Product Purpose

Doxiq (by Llamitai) is a minimal multi-tenant SaaS starter. It exists to give a new product its foundations — authentication, users, tenants, roles/permissions, invitations, and a generic asynchronous background-job mechanism — so builders start from a clean, opinionated base instead of wiring the same plumbing again.

Success looks like: a developer can clone Doxiq, run it, sign in, create a tenant, invite a member, and enqueue a background job within minutes — then build their actual product on top without fighting the scaffolding.

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
