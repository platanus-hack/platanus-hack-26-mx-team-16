# Backend debugging

## Prerrequisitos

- Docker corriendo con el stack levantado al menos una vez (`make up`)
- VS Code con la extensión **Python** instalada, o PyCharm Professional

---

## 1. Levantar en modo debug

Desde `backend/`:

```bash
make debugpy
```

Esto levanta el stack normal más un override que:

- expone el puerto **5678** → proceso `uvicorn` (API HTTP)
- expone el puerto **5679** → proceso `arq` (worker de tareas en background)

Ambos procesos arrancan con `python -Xfrozen_modules=off -m debugpy --listen 0.0.0.0:<port>` y quedan esperando un debugger antes de ejecutar código.

---

## 2. Conectar VS Code

Agrega esto a `.vscode/launch.json` (créalo si no existe):

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "API (uvicorn) :5678",
      "type": "debugpy",
      "request": "attach",
      "connect": { "host": "localhost", "port": 5678 },
      "pathMappings": [
        { "localRoot": "${workspaceFolder}/backend", "remoteRoot": "/app" }
      ]
    },
    {
      "name": "Worker (arq) :5679",
      "type": "debugpy",
      "request": "attach",
      "connect": { "host": "localhost", "port": 5679 },
      "pathMappings": [
        { "localRoot": "${workspaceFolder}/backend", "remoteRoot": "/app" }
      ]
    }
  ]
}
```

Luego en VS Code: **Run → Start Debugging** (o `F5`) y elige la configuración según lo que quieras depurar.

---

## 3. Conectar PyCharm

Requiere **PyCharm Professional** (Community no soporta remote debugging).

1. **Run → Edit Configurations → + → Python Remote Debug**
2. Rellena los campos:

| Campo | Valor |
|---|---|
| Name | `API (uvicorn) :5678` |
| Host | `localhost` |
| Port | `5678` |

3. En **Path mappings** agrega:

| Local path | Remote path |
|---|---|
| `/ruta/absoluta/a/doxiq/backend` | `/app` |

4. Repite para el worker con puerto `5679` si lo necesitas.
5. Ejecuta `make debugpy` primero — el contenedor arranca y queda bloqueado esperando.
6. Luego haz click en **Debug** en PyCharm — el IDE se conecta al proceso ya en espera.

---

## 4. Flujo típico

1. Poner un breakpoint en el archivo fuente local (e.g. `src/workflows/...`)
2. Ejecutar `make debugpy` — el contenedor queda en pausa hasta que conectes
3. Conectar con `F5` → el proceso continúa y se detiene en el breakpoint
4. Inspeccionar variables, stack frames, evaluar expresiones en el Debug Console

---

## Notas

- `pathMappings` es imprescindible: mapea tu workspace local (`backend/`) al path dentro del contenedor (`/app`), de lo contrario VS Code no puede resolver los archivos fuente.
- Si el proceso no espera (arranca y pasa de largo), verifica que el override `docker-compose.debug.yml` se esté aplicando — el log debe mostrar `[debug] starting ... with debugpy on :XXXX`.
- Para depurar solo la API sin el worker, o viceversa, puedes comentar la línea correspondiente en `docker-compose.debug.yml` temporalmente.
