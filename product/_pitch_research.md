# Owliver — Pitch Deck Research Digest

> Citable statistics for the Owliver hackathon pitch. Each data point: **figure · source · year · URL · pitch use**.
> Verification status noted per item. Compiled 2026-06-21. Prefer 2024–2026 data.
>
> Legend: ✅ verified from primary/verbatim source · ⚠️ partially verified (reputable secondary citing the primary) · ❌ UNVERIFIED — do not cite as fact.

---

## PILLAR A — Mexican government / Mexico cybersecurity (the civic hook)

### A1. Guacamaya Leaks / SEDENA hack (Sept 2022)
- **Figure:** **6 terabytes** of data exfiltrated from SEDENA (Mexican Ministry of National Defense) — ≈4 million internal emails/documents spanning 2010–2022. The largest hack in Mexican history. ✅
- **What leaked:** Military email servers, revealing army–cartel links, surveillance of journalists/activists/opposition (incl. Pegasus spyware), spying on parents of the 43 disappeared Ayotzinapa students, classification of feminist groups as "subversive," and internal sexual-abuse cover-ups. Confirmed by President López Obrador in a Sept 30, 2022 press conference.
- **Attack vector:** ProxyShell (2021 Microsoft Exchange Server vulnerability chain) — ⚠️ reported in news/security coverage, cite as "reported," not official.
- **Source:** Distributed Denial of Secrets (DDoSecrets), primary distributor — catalogs it as "Secretaría de la Defensa Nacional México (6 TBs)"; corroborated by Latinus (journalist Carlos Loret de Mola announced it on-air Sept 29, 2022). Year: **2022**.
- **URL:** https://ddosecrets.substack.com/p/sedena-mexico-secretaria-defensa-nacional · https://en.wikipedia.org/wiki/Guacamaya_(hacktivist_group)
- **Pitch use:** "The largest hack in Mexican history hit the Ministry of Defense itself — 6 TB exfiltrated through an unpatched Exchange flaw. If SEDENA can be breached, every `.gob.mx` site is in scope."

### A2. Mexico as a top cyberattack target in Latin America
- **HEADLINE figure:** **324 billion** attempted cyberattacks on Mexico in 2024. ✅
  - **Source:** Fortinet FortiGuard Labs, *Global Threat Report 2025* (reported via Mexico Business News, May 6, 2025). Year: **2024 data / 2025 report**.
  - **URL:** https://mexicobusiness.news/cybersecurity/news/mexico-hit-324-billion-attempted-cyberattacks-fortinet-labs
- **Multi-year trend (all Fortinet / FortiGuard Labs):**
  - **2022 (1H): 85 billion** attempts — **#1 in Latin America**, ahead of Brazil (31.5B) and Colombia (6.3B); +40% YoY. Source: Mexico News Daily, Dec 27, 2022 (Fortinet + AMECI). URL: https://mexiconewsdaily.com/news/mexico-top-victim-of-cyberattacks/ ✅
  - **2023 (1H): 14 billion** attempts — #2 in LatAm behind Brazil (23B); region total 63B. Source: Fortinet 1H-2023 Global Threat Landscape. URL: https://www.fortinet.com/content/dam/fortinet/assets/threat-reports/threat-report-1h-2023.pdf ✅
  - **2024 (full year): 324 billion** (see headline). ✅
  - **2025 (1H): 40.6 billion** attempts, #2 in region. Source: Mexico Business News. URL: https://mexicobusiness.news/cybersecurity/news/mexico-records-406-billion-cyberattacks-attempts-1h25 ⚠️ (not deep-verified — confirm before headlining)
- **Pitch use:** "Mexico is the #1–#2 cyberattack target in Latin America every single year — 324 billion attack attempts in 2024 alone (Fortinet)."

### A3. `.gob.mx` / INE / citizen-data breaches
- **INE voter database — 93.4 million records exposed (2016).** Names, addresses, DOB, occupations, voter IDs on an unsecured public AWS server (illegal under Mexican law). Found by researcher Chris Vickery; INE filed a criminal complaint. Source: SecurityWeek, Apr 2016. URL: https://www.securityweek.com/93-million-mexican-voter-records-leaked-online/ ✅
- **INE padrón resale — 91 million voters for sale (2021).** Full DB (names, DOB, sex, address, CURP) offered on a forum for ~US$750; 99,983-record sample posted. INE confirmed verifiable data matched a 2018 cut. Source: Xataka México, Jul 19, 2021. URL: https://www.xataka.com.mx/seguridad/ine-encontro-que-parece-ser-copia-padron-electoral-mexico-alguien-vende-15-000-pesos-mercado-negro ✅
- **INE 2024 padrón — "Sc0rp10n" group claim (Oct 2025).** Hackers claimed server access + a persistent backdoor installed ~1 year prior; a 2024-registry sample's CURPs were independently validated by analyst Nicolás Azuara. **INE officially denied the breach.** Sources: Infobae (Oct 26, 2025) https://www.infobae.com/mexico/2025/10/26/ine-desmiente-hackeo-en-su-sistema-garantiza-seguridad-de-sistemas-informaticos/ ; El Universal. ⚠️ PARTIALLY VERIFIED — claimed + third-party CURP validation, but disputed by INE. Frame as "alleged/disputed."
- **Pitch use:** "Even Mexico's electoral authority has faced repeated padrón leaks — 93 million citizen records exposed in 2016, tens of millions sold openly online since — while agencies deny breaches they can't even see. That blind spot is exactly what Owliver closes."

---

## PILLAR B — Cost & scale of breaches

### B1. IBM Cost of a Data Breach 2024 — global average
- **Figure:** **USD 4.88 million** global average total cost (up 10% YoY from $4.45M in 2023 — largest jump since the pandemic). Based on 604 orgs, 16 countries, 17 industries. ✅
- **Source:** IBM Cost of a Data Breach Report 2024 (Ponemon/IBM). Year: **2024**.
- **URL:** https://newsroom.ibm.com/2024-07-30-ibm-report-escalating-data-breach-disruption-pushes-costs-to-new-highs
- **Pitch use:** "The average breach now costs $4.88M — a record. One incident can dwarf a year of an entire security budget."

### B2. IBM Cost of a Data Breach 2025 — global decline, US record
- **Global: USD 4.44 million** — down 9% from $4.88M; **first decline in five years** (faster detection via AI/automation). ✅
- **United States: USD 10.22 million** — record high, +~9% YoY (US moving opposite to the global trend). ✅
- **Source:** IBM Cost of a Data Breach Report 2025. Year: **2025**.
- **URL:** https://www.ibm.com/reports/data-breach · https://www.helpnetsecurity.com/2025/08/04/ibm-cost-data-breach-report-2025/
- **Pitch use:** "Globally, costs dipped to $4.44M as defenders got faster — but in the US they hit a record $10.22M. The differentiator is detection speed."

### B3. Latin America regional figure
- **Figure:** **USD 2.76 million** LatAm average (up 12% vs 2023 — fastest-rising region). Brazil-specific: R$7.19M (2025). ⚠️ PARTIALLY VERIFIED (reputable secondary citing IBM's regional cut).
- **Source:** IBM Cost of a Data Breach 2024, via Convergencia Latina. Year: **2024**.
- **URL:** https://www.convergencialatina.com/Section-Analysis/360682-3-8-IBM_Average_cost_of_data_breach_is_US2_76_million_up_12_from_last_year
- **Pitch use:** "In Latin America the average breach is $2.76M and climbing 12% a year — the fastest-rising region in the world."

### B4. Industry — most expensive + public sector
- **Healthcare = most expensive industry, 14th year running: USD 9.77 million (2024)**, ~2x the average (fell to $7.42M in 2025 but still #1). Source: IBM 2024 newsroom (verbatim). URL: https://newsroom.ibm.com/2024-07-30-ibm-report-escalating-data-breach-disruption-pushes-costs-to-new-highs ✅
- **Public sector: USD 2.55 million (2024)** — the lowest of all industries studied. ⚠️ PARTIALLY VERIFIED via Morgan Lewis citing IBM. URL: https://www.morganlewis.com/blogs/sourcingatmorganlewis/2025/05/study-finds-average-cost-of-data-breaches-significantly-increased-globally-in-2024
- **Pitch use:** "Healthcare breaches cost ~$9.8M — twice the average. Government breaches average $2.55M in *direct* cost, but the real price is public trust — which no dollar figure captures."

### B5. Breach lifecycle (time to identify + contain)
- **2024: 258 days** (mean time to identify + contain) — a 7-year low (down from 277 in 2023). ✅ Source: IBM 2024 newsroom. URL: https://newsroom.ibm.com/2024-07-30-ibm-report-escalating-data-breach-disruption-pushes-costs-to-new-highs
- **2025: 241 days** — lowest in 9 years. ✅ Source: IBM 2025 via Help Net Security. URL: https://www.helpnetsecurity.com/2025/08/04/ibm-cost-data-breach-report-2025/
- **Pitch use:** "Even with AI, organizations take ~241 days to find and contain a breach — eight months of undetected exposure. Continuous monitoring closes that window."

### B6. Human element (Verizon DBIR)
- **DBIR 2024: 68% of breaches involved the human element** (error or social engineering). Dataset: 30,458 incidents / 10,626 confirmed breaches, 94 countries. ✅ Source: Verizon 2024 DBIR. URL: https://www.verizon.com/business/resources/reports/2024-dbir-data-breach-investigations-report.pdf
- **DBIR 2025: ~60% human element**; third-party involvement doubled 15%→30%. ✅ Source: Verizon 2025 DBIR. URL: https://www.verizon.com/business/resources/T16f/reports/2025-dbir-data-breach-investigations-report.pdf
- **Pitch use:** "~2 in 3 breaches involve a human mistake — and 1 in 3 now involve a third party. Automated, continuous testing catches what people miss."

---

## PILLAR C — Pentesting is expensive / slow / doesn't scale + talent shortage

### C1. Cost & duration of a manual pentest
- **Cost: USD 5,000–50,000 per web-app test** (overall pentest range $2,500–$50,000; SaaS/API $5,000–$30,000). Source: Astra Security pricing guide, 2026. URL: https://www.getastra.com/blog/security-audit/penetration-testing-cost/ ✅
- **Average ~USD 18,300 per engagement** (range $5K–$100K+; standard commercial $10K–$35K). Source: penetrationtestingcost.com aggregate, 2026. URL: https://penetrationtestingcost.com/ ⚠️ (independent aggregator)
- **Analyst validation:** MarketsandMarkets (Mar 2026) explicitly names **"High cost of advanced penetration testing engagements"** AND **"shortage of skilled security professionals"** as market *restraints*. URL: https://www.marketsandmarkets.com/Market-Reports/penetration-testing-market-13422019.html ✅ — strongest third-party confirmation that cost + talent are *the* adoption blockers.
- **Duration: ~4–6 weeks end-to-end** (active testing 1–2 weeks). Source: Triaxiom Security. URL: https://www.triaxiomsecurity.com/blog/typical-timeline-for-a-penetration-test/ ✅ (EliteSec corroborates 2–4 weeks avg: https://elitesec.io/blog/how-long-does-pen-test-take/)
- **Pitch use:** "A single manual pentest costs $5K–$50K and takes weeks — and you get one point-in-time snapshot. Owliver runs an automated scan in minutes."

### C2. Global cybersecurity workforce gap — ISC2 (PRIMARY)
- **Figure:** **4.8 million** unfilled cybersecurity roles globally — a record, **+19% YoY**; active workforce flat at ~5.5M. For the first time, "lack of budget" was the #1 cause of staffing shortages. ✅
- **Source:** ISC2 2024 Cybersecurity Workforce Study (published Sept 11, 2024). Year: **2024** (this is the most recent official *gap* number — the Dec 2025 study pivoted to skills and did NOT publish a single gap figure; the older "~4M" is the 2023 number). URL: https://www.isc2.org/Insights/2024/09/ISC2-Publishes-2024-Cybersecurity-Workforce-Study-First-Look
- **Pitch use:** "ISC2: 4.8 million unfilled cybersecurity jobs globally (2024, +19% YoY). There will never be enough humans to test every site — automation is the only way to scale coverage."

### C3. Penetration testing market size & growth
- **Pentest market: USD 1.98B (2025) → USD 4.39B (2031), CAGR 14.2%.** Manual testing = 75.4% of market. Source: MarketsandMarkets, Mar 2026 (verified from report page). URL: https://www.marketsandmarkets.com/Market-Reports/penetration-testing-market-13422019.html ✅
- **Alt estimate: USD 1.82B (2023) → USD 5.24B (2030), CAGR 16.6%.** Source: Grand View Research, 2024. URL: https://www.grandviewresearch.com/industry-analysis/penetration-testing-market-report ⚠️ (direct page blocked; figure consistent across snippets)
- **Broader security-testing market: USD 10.96B (2025) → USD 40.99B (2031), CAGR 24.6%.** Source: MarketsandMarkets press release, 2025. URL: https://www.prnewswire.com/news-releases/security-testing-market-worth-40-99-billion-by-2031--marketsandmarkets-302699349.html ✅
- **Pitch use:** "Pentest-specific market ~$2B today growing ~14–17% CAGR (SAM); the broader security-testing market is $11B → $41B by 2031 at 24.6% CAGR (TAM). And 75% of it is still manual."

---

## PILLAR D — The agentic surface (THE differentiator)

### D1. OWASP Top 10 for LLM Applications (2025) — Prompt Injection = #1 ✅ CONFIRMED
- **Figure:** **LLM01:2025 Prompt Injection** is ranked **#1** in the OWASP Top 10 for Large Language Model Applications, 2025 version — top spot for the second consecutive edition.
- **Source:** OWASP Gen AI Security Project (authoritative primary). Year: **2025**.
- **URL:** https://genai.owasp.org/llmrisk/llm01-prompt-injection/ · PDF: https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf
- **Pitch use:** "The world's leading application-security authority ranks Prompt Injection as the #1 risk to every LLM application — LLM01:2025. Owliver tests for exactly this on the agentic surface that traditional pentests completely ignore."

### D2. Enterprise adoption — AI / chatbots / GenAI ✅ CONFIRMED
- **78% of organizations use AI in ≥1 business function; 71% regularly use generative AI** (up from 55% AI adoption a year earlier). Source: McKinsey, *The State of AI* (survey early 2025, pub. Mar 2025). URL: https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai-how-organizations-are-rewiring-to-capture-value ✅
- **85% of customer-service leaders will explore or pilot customer-facing conversational GenAI in 2025.** Source: Gartner press release, Dec 9, 2024. URL: https://www.gartner.com/en/newsroom/press-releases/2024-12-09-gartner-survey-reveals-85-percent-of-customer-service-leaders-will-explore-or-pilot-customer-facing-conversational-genai-in-2025 ✅
- **Pitch use:** "78% of organizations already run AI in production and 85% of customer-service teams are deploying customer-facing GenAI chatbots — and every one of those bots is a new, untested attack surface."

### D3. Real-world prompt-injection / chatbot incidents (cautionary tales) ✅ ALL CONFIRMED
- **Air Canada chatbot (2024).** *Moffatt v. Air Canada*, 2024 BCCRT 149 (BC Civil Resolution Tribunal, Feb 14, 2024). Passenger Jake Moffatt; chatbot gave wrong bereavement-fare advice. Tribunal found negligent misrepresentation, **rejected the "the chatbot is a separate legal entity" defense**, and ordered **CAD $812.02** total. Source: McCarthy Tétrault / ABA. URLs: https://www.mccarthy.ca/en/insights/blogs/techlex/moffatt-v-air-canada-misrepresentation-ai-chatbot · https://www.americanbar.org/groups/business_law/resources/business-law-today/2024-february/bc-tribunal-confirms-companies-remain-liable-information-provided-ai-chatbot/
  - *Pitch use:* "A tribunal held a company legally liable for what its chatbot said. Your agentic surface is now a legal liability, not just a technical one." (Cite **$812.02**, not "$650.")
- **Chevrolet dealer chatbot (Dec 2023).** Chevrolet of Watsonville ran a ChatGPT-powered bot (Fullpath). A user injected instructions and got it to "agree" to sell a 2024 Chevy Tahoe for **$1** with "that's a legally binding offer – no takesies backsies." Source: GM Authority / AI Incident Database #622. URLs: https://gmauthority.com/blog/2023/12/gm-dealer-chat-bot-agrees-to-sell-2024-chevy-tahoe-for-1/ · https://incidentdatabase.ai/cite/622/
  - *Pitch use:* "A textbook prompt injection: a customer reprogrammed a dealer's bot to sell a $76K SUV for $1. This is LLM01 in the wild." (Attribute to "a user"; MSRP ~$76K is safest.)
- **DPD chatbot (Jan 2024).** UK parcel firm DPD disabled its AI chat after customer Ashley Beauchamp coaxed it into swearing and writing a **poem disparaging DPD** ("DPD is the worst delivery firm in the world"). DPD blamed a Jan 18 system update; viral (1.1M+ views). Source: SCMP/Reuters / Guardian / BBC / ITV. URLs: https://www.scmp.com/tech/tech-trends/article/3249284/uk-delivery-firm-dpd-suspends-ai-chat-function-after-bot-swears-customer-and-writes-poem-disparaging · https://www.itv.com/news/2024-01-19/dpd-disables-ai-chatbot-after-customer-service-bot-appears-to-go-rogue
  - *Pitch use:* "One frustrated customer turned DPD's support bot into a brand-trashing poet. Reputational damage in a single prompt."

### D4. Gartner agentic-AI projections (through 2026–2028) ✅ CONFIRMED
- **By 2028: 33% of enterprise software applications will include agentic AI, up from <1% in 2024.** ✅
- **By 2028: ≥15% of day-to-day work decisions made autonomously via agentic AI, up from 0% in 2024.** ✅
  - Source: Gartner press release, Jun 25, 2025. URL: https://www.gartner.com/en/newsroom/press-releases/2025-06-25-gartner-predicts-over-40-percent-of-agentic-ai-projects-will-be-canceled-by-end-of-2027
- **By 2026: 40% of enterprise apps will have task-specific AI agents, up from <5% in 2025.** ✅ Source: Gartner press release, Aug 26, 2025. URL: https://www.gartner.com/en/newsroom/press-releases/2025-08-26-gartner-predicts-40-percent-of-enterprise-apps-will-feature-task-specific-ai-agents-by-2026-up-from-less-than-5-percent-in-2025
- **Pitch use:** "Gartner: by 2026, 40% of enterprise apps ship AI agents; by 2028, a third run agentic AI and 15% of work decisions are autonomous. The agentic surface is exploding — and almost nobody is pentesting it."

---

## PILLAR E — AI can now do offensive security (why now / validation)

### E1. XBOW tops the HackerOne leaderboard ✅ CONFIRMED (primary)
- **Figure:** An autonomous AI penetration tester (XBOW) reached **#1 on HackerOne's US leaderboard** (Q2 2025) — a first in bug-bounty history. It submitted **~1,060 vulnerabilities** (all fully automated): **130 resolved**, **303 triaged** (confirmed real/actionable); findings spanned RCE, SQLi, XSS, info disclosure.
- **Source:** XBOW blog (primary), "The road to Top 1," Jun 24, 2025. Year: **2025**. URL: https://xbow.com/blog/top-1-how-xbow-did-it · follow-up (hit #1 globally before Black Hat): https://xbow.com/blog/xbow-on-hackerone-whats-next
- **Corroboration:** Dark Reading https://www.darkreading.com/vulnerabilities-threats/ai-based-pen-tester-top-bug-hunter-hackerone · TechRepublic https://www.techrepublic.com/article/news-ai-xbow-tops-hackerone-us-leaderboad/ · raised $75M (Jul 2025).
- **Pitch use:** "In 2025 an autonomous AI — XBOW — submitted ~1,060 real vulnerabilities and became the #1 bug-hunter on HackerOne's US leaderboard, beating every human researcher. Autonomous offensive AI isn't theory; it's already winning."

### E2. Other proof autonomous AI finds REAL vulnerabilities
- **Google "Big Sleep" — first AI-found real-world 0-day.** Found a previously unknown, exploitable stack-buffer-underflow 0-day in **SQLite** — "the first public example of an AI agent finding a previously unknown exploitable memory-safety issue in widely used real-world software." Fixed the same day, before it shipped. Big Sleep = Google Project Zero + DeepMind, on Gemini. Source: Project Zero blog (primary), Oct/Nov 2024. URL: https://googleprojectzero.blogspot.com/2024/10/from-naptime-to-big-sleep.html ✅
  - *Pitch use:* "Google's Big Sleep AI agent found a real 0-day in SQLite that fuzzers missed — and it was fixed before it ever shipped."
- **Academic — GPT-4 autonomously exploited 87% of real one-day CVEs** (15 real-world vulns, given the CVE description) vs 0% for GPT-3.5/open-source LLMs/scanners (ZAP, Metasploit); agent was ~91 lines of code. Source: Fang, Bindu, Gupta, Daniel Kang (UIUC), arXiv:2404.08144, Apr 2024. URL: https://arxiv.org/abs/2404.08144 ✅
  - *Pitch use:* "Peer-reviewed research: GPT-4 autonomously exploited 87% of real one-day CVEs. Autonomous exploitation is already here."
- **DARPA AI Cyber Challenge (AIxCC) finals, Aug 2025.** AI cyber-reasoning systems scanned **54 million lines of code** across 63 challenges; **discovered 54 of 63 synthetic vulns (86%) and patched 68%**; also found **18 real, non-synthetic 0-days** in live open-source projects (responsibly disclosed). Winner: Team Atlanta. Source: DARPA (primary), Aug 8, 2025. URL: https://www.darpa.mil/news/2025/aixcc-results ✅ (Prize split — $4M/$3M/$1.5M — per CyberScoop, not the DARPA page: https://cyberscoop.com/darpa-ai-cyber-challenge-winners-def-con-2025/)
  - *Pitch use:* "DARPA's 2025 AIxCC proved AI finds AND patches vulnerabilities at scale — 86% of planted bugs found, plus 18 real 0-days across 54M lines of code."

---

## TOP 8 PUNCHIEST STATS (ranked by pitch impact)

1. **324 billion** attempted cyberattacks on Mexico in 2024 — #1–#2 target in Latin America. *(Fortinet, 2024)* — the civic hook, makes the `.gob.mx` ranking feel urgent.
2. **6 TB** stolen from Mexico's Ministry of Defense (SEDENA) in the 2022 Guacamaya hack — largest in national history. *(DDoSecrets, 2022)* — "if SEDENA falls, every .gob.mx is exposed."
3. An autonomous AI (**XBOW**) hit **#1 on HackerOne's US leaderboard** with ~1,060 real vulns in 2025. *(XBOW, 2025)* — proves "AI does offensive security" is real, today.
4. **Prompt Injection = #1 risk** in OWASP Top 10 for LLM Apps (LLM01:2025). *(OWASP, 2025)* — authoritative backing for the agentic-surface differentiator.
5. **$4.88M** average data-breach cost (2024 record); **$10.22M** in the US (2025 record). *(IBM, 2024/2025)* — the stakes, in dollars.
6. **4.8 million** unfilled cybersecurity jobs globally, +19% YoY. *(ISC2, 2024)* — "humans can't scale; automation must."
7. **$5K–$50K and weeks** per manual pentest — analyst-named adoption blocker. *(Astra / MarketsandMarkets, 2026)* — the problem Owliver automates away.
8. Gartner: **40% of enterprise apps ship AI agents by 2026**; **33% run agentic AI by 2028**. *(Gartner, 2025)* — the agentic attack surface is exploding precisely as Owliver launches.
