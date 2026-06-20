# Claude Code - Custom Skills

Este directorio contiene custom skills para Claude Code específicos de este proyecto.

## Skills Disponibles

### 📦 implement-crud

**Ubicación:** `.claude/skills/implement-crud/`

**Descripción:** Implementa operaciones CRUD completas (Create, Read, Update, Delete, List) para entidades del dominio siguiendo Clean Architecture, DDD y CQRS.

**Uso:**
```
Implementa un CRUD para [NombreEntidad]
```

Claude automáticamente:
1. Hará preguntas de clarificación sobre la entidad
2. Implementará todos los componentes necesarios
3. Validará el código

**Tiempo estimado:** 30-45 minutos por CRUD básico

**Documentación completa:** `./skills/implement-crud/README.md`

## Cómo Funciona

Claude Code automáticamente detecta los skills en este directorio y los activa cuando:
- El usuario menciona que necesita implementar un CRUD
- Claude determina que el skill es relevante para la tarea

Los skills se cargan automáticamente sin necesidad de configuración adicional.

## Agregar Nuevos Skills

Para agregar un nuevo skill:

1. Crear un directorio en `.claude/skills/[nombre-skill]/`
2. Crear un archivo `Skill.md` con:
   - YAML frontmatter (name, description, dependencies)
   - Instrucciones detalladas
3. Opcionalmente agregar `REFERENCE.md` para documentación extensa

Ejemplo de estructura:
```
.claude/skills/
└── mi-skill/
    ├── Skill.md          # Requerido
    ├── REFERENCE.md      # Opcional
    └── README.md         # Opcional
```

## Recursos

- [Documentación de Custom Skills](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills)
- [Agent Skills Specification](http://agentskills.io)
- [Ejemplos de Skills](https://github.com/anthropics/skills)