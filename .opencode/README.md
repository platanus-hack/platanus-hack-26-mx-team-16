# OpenCode - Custom Configuration

Este directorio contiene la configuración personalizada de OpenCode para el proyecto Doxiq.

## Estructura

```
.opencode/
├── opencode.json          # Configuración principal (MCP, plugins, skills, commands, hooks)
├── skills/                # Custom skills del proyecto
├── commands/              # Slash commands personalizados
├── hooks/                 # Hooks de OpenCode
└── README.md              # Este archivo
```

## MCP Servers Configurados

- **codegraph** - Knowledge graph del código (tree-sitter parsed)
- **pencil** - Design tool integration
- **shadcn** - shadcn/ui component registry
- **chrome-devtools** - Chrome DevTools automation
- **playwright** - Browser automation
- **context7** - Library documentation (key vía `{env:CONTEXT7_API_KEY}`)
- **tailwindcss-server** - Tailwind CSS utilities

> Los servidores globales (`codegraph`, `pencil`, `context7`) viven en
> `~/.config/opencode/opencode.json` y aplican a todos los proyectos.

## Plugins Habilitados

- **pr-review-toolkit** - Pull request review automation
- **feature-dev** - Feature development workflow
- **understand-anything** - Code understanding
- **codebase-documenter** - Documentation generation
- **ui-ux-pro-max** - UI/UX design assistance

## Skills Disponibles

Los skills se cargan automáticamente desde `.opencode/skills/`:

- **brainstorming** - Exploración de requisitos y diseño antes de implementar
- **clean-fastapi-ddd** - FastAPI + Clean Architecture + DDD + CQRS
- **design-system-patterns** - Design tokens, theming, component architecture
- **docker-hardening** - Docker security hardening (CIS Benchmark)
- **fastapi** - FastAPI best practices
- **fastmcp-server** - MCP server development with FastMCP
- **find-skills** - Descubrimiento de skills instalables
- **frontend-design** - Production-grade frontend interfaces
- **impeccable** - UI design, redesign, audit, polish
- **pytest-coverage** - Pytest coverage analysis
- **python-testing** - Llamitai backend testing conventions
- **sse-endpoints** - Server-Sent Events implementation
- **vercel-react-best-practices** - React/Next.js performance optimization
- **vercel-composition-patterns** - React composition patterns
- **web-design-guidelines** - Auditoría de UI contra Web Interface Guidelines
- **typescript-advanced-types** - Sistema de tipos avanzado de TypeScript
- **next-best-practices** - Convenciones de Next.js App Router
- **tailwind-design-system** - Design systems con Tailwind CSS v4
- **mcp-integration** - Integración de servidores MCP
- **webapp-testing** - Testing de web apps con Playwright
- **slash-command-factory** - Generación de slash commands

## Commands Disponibles

- **commit** - Crear commits siguiendo Conventional Commits
- **brainstorm** - Desarrollar una spec iterativa pregunta a pregunta
- **bug-fix** - Flujo issue → branch → fix → PR para un bug
- **code-improve** - Refactor senior (KISS/SOLID/DRY/YAGNI)
- **understand-context** - Resumen del estado de trabajo actual
- **update-pr-description** - Ajustar la descripción del PR a la plantilla

## Hooks

Los hooks se definen en `.opencode/hooks/` y se ejecutan automáticamente según los eventos configurados.

## Uso

OpenCode detecta automáticamente esta configuración al ejecutarse desde el directorio del proyecto.

## Recursos

- [OpenCode Documentation](https://opencode.ai/docs)
- [MCP Servers](https://modelcontextprotocol.io)
- [Agent Skills Specification](http://agentskills.io)