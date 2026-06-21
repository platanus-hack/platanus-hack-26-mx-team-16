# Owliver 🦉: Corporate AI Under the Microscope

**Automated AI-orchestrated pentesting that breaks your AI live and grades it from A to F.**

🔗 Live demo: https://owliver.chuspita.com

## The Hook

Every company is racing to bolt a chatbot onto their website. Almost none of them tested whether that chatbot can be tricked into leaking its instructions, its data, or its keys. Owliver does — automatically, in minutes, with proof.

## The Problem

Traditional pentesting is manual, slow, and expensive, and it ends in static reports nobody reads. Worse, there's a brand-new attack surface everyone is ignoring: the **agentic surface**. Companies are shipping chatbots and LLMs that are wide open to prompt-injection and jailbreaks — and traditional scanners (OWASP-style tools) are completely blind to them.

## The Solution

The user just enters a target URL and an attack level. Behind the scenes, a team of orchestrated AI agents (an **Opus orchestrator** + **two Sonnet sub-agents**) runs a real pentest across both the classic OWASP surface **and** the agentic surface. Minutes later, Owliver delivers a report that a non-technical person can actually read, with a clear **A–F grade**.

## Our Differentiator

Owliver doesn't just scan for vulnerabilities — it **breaks the AI and proves it with irrefutable evidence**. To kill false positives, it pairs an **LLM-based judge** with a **canary token**: if we get the chatbot to reveal its hidden system-prompt, we document the attack as a total success. No guesswork, no noise — only confirmed, reproducible findings.

## Go-To-Market

We combine **public pressure** with a **B2B product**:

- **Public ranking:** viral-ready grade cards ranking the security of high-profile targets — starting with Mexican government sites (`.gob.mx`) and extending to banks and e-commerce.
- **Private Watchlist (SaaS):** continuous security monitoring with automated alerts via email or Slack the moment a target's grade drops.

The public exposure drives adoption of the core SaaS — turning attention into a continuous-monitoring revenue engine.
