# Codex - Project Configuration

Este directorio contiene la configuración específica del proyecto para Codex.

## Estructura

```
.codex/
├── config.toml          # Configuración principal (MCP servers, project settings)
├── skills/              # Custom skills del proyecto (copiados de .claude/skills/)
├── rules/               # Reglas específicas del proyecto
└── README.md            # Este archivo
```

## MCP Servers Configurados

- **codegraph** - Knowledge graph del código (tree-sitter parsed)
- **pencil** - Design tool integration
- **shadcn** - shadcn/ui component registry
- **playwright** - Browser automation
- **next-devtools** - Next.js development tools
- **context7** - Library documentation
- **tailwindcss-server** - Tailwind CSS utilities

## Skills Disponibles

Los skills se cargan desde `.codex/skills/`:

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

## Reglas del Proyecto

Definidas en `.codex/rules/project-rules.md`:
- Arquitectura backend/frontend
- Patrones de desarrollo obligatorios (BFF routes)
- Sistema de diseño (PRODUCT.md, DESIGN.md)
- Comandos de desarrollo
- Guías de estilo

## Configuración Global

Codex también lee `~/.codex/config.toml` donde este proyecto está registrado con `trust_level = "trusted"`.

## Uso

Codex detecta automáticamente la configuración del proyecto al ejecutarse desde el directorio raíz.