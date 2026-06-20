# MCPs y skills: cheatsheet compacto

## Como pedirlo en prompts

- Nombra la capacidad y el objetivo: `Usa CodeGraph para encontrar quien llama a X`.
- Para skills, usa `$skill` o el nombre literal: `Usa $fastapi para revisar este endpoint`.
- Da contexto minimo: archivo, modulo, error, criterio de exito.
- No intentes invocar tools directo; pide la intencion y el agente elige llamadas.
- Si quieres evitar internet o cambios, dilo: `sin web`, `solo analiza`, `no edites`.

## Patrones rapidos

```text
Usa CodeGraph para ubicar el simbolo <X> y su impacto.
Usa context-mode para explorar sin volcar archivos grandes al contexto.
Usa context7 para consultar docs actuales de <libreria>.
Usa $python-testing para crear tests de <modulo>.
Usa $impeccable para pulir la UI de <pantalla>.
```

## MCPs

| MCP | Uso |
|---|---|
| CodeGraph | Grafo AST del repo: simbolos, callers, callees, impacto, contexto. |
| context-mode | Lectura/indexado compacto: `ctx_batch_execute`, `ctx_search`, `ctx_fetch_and_index`. |
| context7 | Docs actuales de librerias, frameworks, SDKs y cloud services. |
| openaiDeveloperDocs | Docs oficiales de OpenAI/Codex, modelos y APIs. |
| playwright | Pruebas e interaccion con apps web locales. |
| chrome-devtools | Inspeccion y control de Chrome/DevTools. |
| node_repl | JS persistente para scripts, browser control y calculos. |
| shadcn | Ayuda con componentes shadcn/ui. |
| tailwindcss-server | Ayuda con Tailwind CSS. |
| pencil | Lee/escribe `.pen` para diseno visual. |
| multi-agent | Delegar investigacion o tareas paralelas a subagentes. |

## Skills

Deduplicado: algunas skills existen en varios origenes locales/plugin.

| Skill | Uso |
|---|---|
| Agent Development | Crear o ajustar agentes. |
| Command Development | Crear slash commands. |
| Hook Development | Crear hooks de automatizacion. |
| MCP Integration | Configurar servidores MCP en plugins/proyectos. |
| Plugin Settings | Configuracion persistente de plugins. |
| Plugin Structure | Estructura y manifiesto de plugins. |
| Skill Development | Crear skills dentro de plugins. |
| Writing Hookify Rules | Reglas de hookify. |
| app-ui-design | UI mobile iOS/Android. |
| backend-patterns | Arquitectura backend Node/Next APIs. |
| brainstorming | Convertir ideas en diseno antes de implementar. |
| browser:control-in-app-browser | Controlar browser embebido. |
| chrome:control-chrome | Controlar Chrome del usuario. |
| clean-fastapi-ddd | FastAPI con Clean Architecture, DDD y CQRS. |
| computer-use:computer-use | Controlar apps locales de Mac. |
| design-system-patterns | Tokens, temas y sistemas de diseno. |
| docker-hardening | Auditar/endurecer Docker. |
| documents:documents | Crear/editar/verificar DOCX. |
| fastapi | Buenas practicas FastAPI/Pydantic. |
| fastmcp-server | Crear servidores MCP con FastMCP. |
| find-skills | Buscar skills instalables. |
| flutter-adaptive-ui | UI Flutter responsive/adaptiva. |
| flutter-animating-apps | Animaciones en Flutter. |
| frontend-design | UI web pulida y distintiva. |
| imagegen | Generar/editar imagenes raster. |
| impeccable | Auditar, pulir y mejorar interfaces. |
| next-best-practices | Buenas practicas Next.js. |
| paperclip | API de control Paperclip. |
| para-memory-files | Memoria local estilo PARA. |
| pdf:pdf | Leer/crear/verificar PDFs. |
| plugin-creator | Scaffolding de plugins Codex. |
| presentations:Presentations | Crear/editar PPTX. |
| pytest-coverage | Pytest con cobertura. |
| python-testing | Tests backend Doxiq. |
| release-changelog | Changelog de releases Paperclip. |
| skill-creator | Crear o mejorar skills Codex. |
| skill-installer | Instalar skills Codex. |
| spreadsheets:Spreadsheets | CSV/XLSX/Google Sheets-targeted. |
| sse-endpoints | SSE backend Doxiq. |
| tailwind-design-system | Design systems con Tailwind v4. |
| typescript-advanced-types | Tipos avanzados TypeScript. |
| vercel-composition-patterns | Patrones de composicion React. |
| vercel-react-best-practices | Performance React/Next. |
| web-design-guidelines | Auditoria UX/accesibilidad web. |
| webapp-testing | Validacion frontend con Playwright. |

## Ejemplos buenos

```text
Usa CodeGraph para explicar como una request autenticada llega al endpoint de tenants.
Usa $clean-fastapi-ddd y agrega un caso de uso para listar miembros por tenant.
Usa $webapp-testing para abrir localhost y verificar que el formulario no rompe en mobile.
```

## Reglas de oro

- Para arquitectura/call graph: CodeGraph.
- Para docs de terceros: context7 o MCPs oficiales disponibles.
- Para UI: leer `PRODUCT.md` y `DESIGN.md`, luego usar `impeccable`/`frontend-design`.
- Para browser/localhost: `webapp-testing`, Playwright o browser MCP.
- Para archivos grandes/web: context-mode primero.
