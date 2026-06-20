# PDF Viewer Component

Componente reusable para previsualizar documentos PDF en aplicaciones Next.js siguiendo el patrón DDD.

## Ubicación en la Arquitectura DDD

- **Capa**: Presentación (`/src/presentation/components/ui`)
- **Tipo**: Componente UI reutilizable
- **Dependencias**: `react-pdf`, `pdfjs-dist`, componentes UI base

## Características

- ✅ Navegación entre páginas (anterior/siguiente)
- ✅ Controles de zoom (50% - 300%)
- ✅ Carga dinámica (solo en cliente, evita SSR)
- ✅ Estados de carga y error
- ✅ Renderizado de capas de texto y anotaciones
- ✅ Configuración flexible mediante props
- ✅ Integración con sistema de diseño existente

## Instalación de Dependencias

```bash
pnpm add react-pdf pdfjs-dist
```

## Uso Básico

```tsx
import { PDFViewer } from "@/src/presentation/components/ui/pdf-viewer";

export function MyComponent() {
  return (
    <PDFViewer
      file="/docs/my-document.pdf"
      onLoadSuccess={(numPages) => console.log(`Loaded ${numPages} pages`)}
      onLoadError={(error) => console.error("Error:", error)}
    />
  );
}
```

## Props

| Prop | Tipo | Default | Descripción |
|------|------|---------|-------------|
| `file` | `string` | **required** | URL o ruta del PDF |
| `className` | `string` | `""` | Clase CSS adicional |
| `showControls` | `boolean` | `true` | Mostrar controles de navegación |
| `showZoom` | `boolean` | `true` | Mostrar controles de zoom |
| `initialScale` | `number` | `1.0` | Escala inicial (0.5 - 3.0) |
| `onLoadSuccess` | `(numPages: number) => void` | - | Callback al cargar exitosamente |
| `onLoadError` | `(error: Error) => void` | - | Callback al fallar la carga |

## Ejemplo Avanzado: Carga Dinámica con Next.js

Para evitar problemas de SSR (Server-Side Rendering), usa `dynamic` de Next.js:

```tsx
import dynamic from "next/dynamic";

// Carga el componente solo en el cliente
const PDFViewer = dynamic(
  () => import("@/src/presentation/components/ui/pdf-viewer").then((mod) => ({
    default: mod.PDFViewer,
  })),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm text-muted-foreground">Loading PDF viewer...</p>
      </div>
    )
  }
);

export function MyPage() {
  return <PDFViewer file="/docs/document.pdf" />;
}
```

## Ejemplo Completo: Con Upload de Archivos

```tsx
"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { Button } from "@/src/presentation/components/ui/button";

const PDFViewer = dynamic(
  () => import("@/src/presentation/components/ui/pdf-viewer").then((mod) => ({
    default: mod.PDFViewer,
  })),
  { ssr: false }
);

export function DocumentViewer() {
  const [pdfUrl, setPdfUrl] = useState<string>("/docs/default.pdf");

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type === "application/pdf") {
      const url = URL.createObjectURL(file);
      setPdfUrl(url);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-2 border-b">
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileUpload}
          className="hidden"
          id="pdf-upload"
        />
        <Button onClick={() => document.getElementById("pdf-upload")?.click()}>
          Upload PDF
        </Button>
      </div>

      <div className="flex-1">
        <PDFViewer
          file={pdfUrl}
          onLoadError={(error) => console.error("PDF Error:", error)}
        />
      </div>
    </div>
  );
}
```

## Configuración de Next.js

Agrega la siguiente configuración a `next.config.ts`:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {}, // Para Next.js 16+
  webpack: (config) => {
    config.resolve.alias.canvas = false;
    return config;
  },
};

export default nextConfig;
```

## Integración con Patrón DDD

### Capa de Dominio
```typescript
// src/domain/entities/document.ts
export interface DocumentPreview {
  id: string;
  url: string;
  name: string;
  pages?: number;
}
```

### Capa de Aplicación
```typescript
// src/application/stores/document-viewer-store.ts
import { create } from "zustand";

interface DocumentViewerState {
  currentDocument: DocumentPreview | null;
  setDocument: (doc: DocumentPreview) => void;
}

export const useDocumentViewerStore = create<DocumentViewerState>((set) => ({
  currentDocument: null,
  setDocument: (doc) => set({ currentDocument: doc }),
}));
```

### Capa de Presentación
```typescript
// src/presentation/features/documents/document-viewer-page.tsx
"use client";

import { PDFViewer } from "@/src/presentation/components/ui/pdf-viewer";
import { useDocumentViewerStore } from "@/src/application/stores/document-viewer-store";

export function DocumentViewerPage() {
  const { currentDocument, setDocument } = useDocumentViewerStore();

  return (
    <PDFViewer
      file={currentDocument?.url || "/docs/default.pdf"}
      onLoadSuccess={(pages) => {
        if (currentDocument) {
          setDocument({ ...currentDocument, pages });
        }
      }}
    />
  );
}
```

## Troubleshooting

### Error: "DOMMatrix is not defined"
**Solución**: Usa `dynamic` import con `ssr: false`:

```tsx
const PDFViewer = dynamic(
  () => import("@/src/presentation/components/ui/pdf-viewer").then(mod => ({ default: mod.PDFViewer })),
  { ssr: false }
);
```

### Error: "Failed to load PDF worker"
**Solución**: El worker se carga automáticamente desde unpkg CDN. Si necesitas una versión local:

```tsx
pdfjs.GlobalWorkerOptions.workerSrc = `/pdf.worker.min.mjs`;
```

### PDF no se carga
**Verificar**:
1. La ruta del archivo es correcta
2. El archivo está en la carpeta `public/`
3. El archivo es un PDF válido
4. Los permisos CORS si es un URL externo

## Mejoras Futuras

- [ ] Búsqueda de texto en el PDF
- [ ] Selección y copia de texto
- [ ] Miniaturas de páginas
- [ ] Modo pantalla completa
- [ ] Rotación de páginas
- [ ] Anotaciones y marcado
- [ ] Descarga del PDF
- [ ] Impresión

## Referencias

- [react-pdf Documentation](https://github.com/wojtekmaj/react-pdf)
- [PDF.js Mozilla](https://mozilla.github.io/pdf.js/)
- [Next.js Dynamic Import](https://nextjs.org/docs/app/building-your-application/optimizing/lazy-loading)
