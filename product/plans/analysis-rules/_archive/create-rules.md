---
feature: analysis-rules
type: plan
status: obsolete
coverage: 5
audited: 2026-06-16
superseded_by: backend DDD re-arch (ver docs/backend/)
---

Flujo Completo: Creación y Guardado de Business Rules                               
                                                                                    
---                                                                                    
FASE 1 — Creación de Reglas (5 caminos)
                                                                                     
Archivo: frontend/src/components/BusinessRulesConfig.tsx                               
                                                                                     
A. Creación Manual                                                                     
                                                                                     
- handleAdd() (~línea 755)                                                             
- Crea BusinessRule con:
- id: crypto.randomUUID()                                                            
- name: "Nueva Regla ${rules.length + 1}"                                            
- text: vacío                                                                        
- isActive: true                                                                     
- createdAt / updatedAt: ISO timestamp                                               
- Propaga con onChange([...rules, newRule])                                            
                                                                                     
B. Edición de Regla Existente                                                          
                                                                                     
- Componente RuleEditor (~línea 221)                                                   
- Estado draft local para edición no destructiva          
- Campos editables:                                                                    
- Nombre (input text)                                                                
- Lógica via AutocompleteEditor — con sugerencias de campos (@DOC_TYPE.field) y      
variables ({{today}})                                                                  
- Knowledge Bases asociados — toggle de KB docs via toggleKb()
- Validación: botón "Guardar" deshabilitado si !draft.text.trim()                      
- Al guardar: onSave(updatedRule) con nuevo updatedAt                                  
                                                                                     
C. Importación desde JSON                                                              
                                                                                     
- Componente ImportRulesModal (~línea 328)                                             
- Input: archivo JSON con formato:
[{ "rule_name": "...", "logica": "..." }, ...]                                         
- Proceso:                                                                             
a. FileReader lee el archivo → setText()                                             
b. Parseo y validación del JSON                                                      
c. Mapea cada item a BusinessRule (UUID, name, text, isActive=true)                  
d. Toast "Reglas importadas ✅"                                                      ─
e. onImport(newRules) → onChange([...rules, ...newRules]) (merge)                    
                                                                                     
D. Exportación a JSON                                     
                                                                                     
- Botón download (~línea 820)                             
- Genera JSON con { rule_name, logica } por regla
- Descarga como archivo via blob URL                                                   
                                                                                     
E. Sugerencia con IA                                                                   
                                                                                     
- Componente SuggestRulesModal (~línea 463)                                            
- API Call: POST ${API_BASE}/kb/suggest-rules             
{ "kb_ids": [...], "doc_schema": {...}, "hint": "instrucción opcional" }               
- Backend genera sugerencias basadas en los KB docs + esquema de campos                
- UI de selección:                                                                     
- Lista expandible de sugerencias (nombre + texto editable)                          
- insertVariable() para inyectar referencias a campos                                
- Checkboxes para multi-selección                                                    
- Al confirmar: onAdd(selectedRules) → merge en lista principal                        
                                                                                     
---                                                                                    
FASE 2 — Validación de Referencias                                                     
                                                        
Archivo: BusinessRulesConfig.tsx (~línea 789)

- hasBrokenReferences() verifica que las referencias @DOC_TYPE.field en el texto de la 
regla apunten a doc types y campos existentes
- Si hay referencia rota → badge rojo "Referencia Inválida"                            
- Se valida contra currentDocKeys y schemas (props del padre)                          
                                                                                     
---                                                                                    
FASE 3 — Propagación al Padre                                                          
                                                                                     
Todas las operaciones (add, edit, delete, import, suggest, toggle) llaman:
                                                                                     
onChange(newRules: BusinessRule[])                        
                                                                                     
Esto sube al componente padre WorkflowBuilder, que mantiene el WorkflowDefinition      
completo.                                                                              
                                                                                     
---                                                       
FASE 4 — Persistencia
                                                                                     
Archivo: frontend/src/lib/workflowStorage.ts
                                                                                     
onChange(newRules)                                        
  ↓                                                                                  
WorkflowBuilder actualiza WorkflowDefinition.businessRules
  ↓                                                                                  
saveWorkflow(workflowDefinition)
  ↓                                                                                  
localStorage.setItem("llamitai_wf_{workflowType}", JSON.stringify(allWorkflows))
                                                                                     
Detalles clave:                                                                        
- Storage: localStorage del navegador (client-side only)                               
- Key: llamitai_wf_${workflowType.toLowerCase()} (ej: llamitai_wf_real_state)          
- Las reglas NO se guardan por separado — van embebidas dentro del WorkflowDefinition
- No hay persistencia en backend — el servidor es stateless respecto a reglas          
                                                                                     
---                                                                                    
FASE 5 — Carga al Abrir                                                                
                                                                                     
Cuando se abre el detalle de un caso:                     
                                                                                     
workflowStorage.readWorkflows(workflowType)                                            
  ↓                                                                                  
Encuentra workflow por workflowId                                                      
  ↓                                                                                  
WorkflowDefinition.businessRules → se pasa a BusinessRulesConfig como prop             
                                                                                     
---                                                                                    
FASE 6 — Uso en Runtime (Análisis)                                                     
                                                                                     
Las reglas viajan al backend solo al momento de evaluar:  
                                                                                     
POST /analyze-stream                                      
{                                                                                      
"rules": [ { id, name, text, isActive, kb_ids } ],      
"extracted_data": { ... }                                                            
}                                                                                      
                                                                                     
El backend no almacena las reglas — las recibe, evalúa, y devuelve resultados.         
                                                        
---                                                                                    
Diagrama Completo                                         

┌─────────────────────────────────────────────────────────────┐
│  CREACIÓN (5 caminos)                                        │
│                                                              │                       
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │                         
│  │  Manual   │ │  Import  │ │ AI Suggest│ │ Edit Existing │  │                       
│  │ handleAdd │ │  JSON ↑  │ │ POST /kb/ │ │  RuleEditor   │  │                       
│  └─────┬─────┘ └────┬─────┘ │suggest-  │ └──────┬────────┘  │                        
│        │             │       │rules     │        │           │                       
│        │             │       └────┬─────┘        │           │                       
│        ▼             ▼            ▼              ▼           │                       
│  ┌───────────────────────────────────────────────────────┐  │                        
│  │         onChange(newRules: BusinessRule[])              │  │                      
│  └──────────────────────┬────────────────────────────────┘  │                        
└─────────────────────────┼───────────────────────────────────┘                        
                        │                                                            
                        ▼                                                            
┌─────────────────────────────────────────────────────────────┐
│  WORKFLOW BUILDER (padre)                                    │                       
│                                                              │
│  WorkflowDefinition.businessRules = newRules                 │                       
│         │                                                    │                       
│         ▼                                                    │
│  saveWorkflow(workflowDefinition)                            │                       
│         │                                                    │
│         ▼                                                    │                       
│  localStorage["llamitai_wf_{type}"] = JSON                   │
│                                                              │                       
│  ┌─────────────────────────────────────────────────┐        │
│  │  WorkflowDefinition                              │        │                       
│  │  ├─ workflowId                                   │        │                       
│  │  ├─ name                                         │        │                       
│  │  ├─ selectedDocTypes[]                            │        │                      
│  │  ├─ perDocSchema {}                               │        │                      
│  │  ├─ businessRules[] ◄── AQUÍ SE GUARDAN          │        │                       
│  │  ├─ kbDocumentIds[]                               │        │                      
│  │  └─ timestamps                                    │        │                      
│  └─────────────────────────────────────────────────┘        │                        
└─────────────────────────────────────────────────────────────┘                        
                        │                                                            
                        │ (al analizar)                                              
                        ▼                                                            
┌─────────────────────────────────────────────────────────────┐
│  RUNTIME (Análisis)                                          │                       
│                                                              │                       
│  POST /analyze-stream                                        │
│  { rules: BusinessRule[], extracted_data: {} }               │                       
│         │                                                    │
│         ▼                                                    │                       
│  Backend evalúa (stateless, no persiste reglas)              │                       
│         │                                                    │                       
│         ▼                                                    │                       
│  SSE → resultados → case.analysisResults → IndexedDB         │                       
└─────────────────────────────────────────────────────────────┘                        
                                                                                     
Estructura de BusinessRule                                                             
                                                                                     
interface BusinessRule {                                  
  id: string;           // crypto.randomUUID()
  name?: string;        // "Nueva Regla 1"                                           
  text: string;         // "Verificar que @receta.medicamentos incluya..."
  isActive: boolean;    // toggle on/off                                             
  kb_ids?: string[];    // KBs asociados para contexto                               
  createdAt: string;    // ISO timestamp                                             
  updatedAt: string;    // ISO timestamp                                             
}                                                                                      
                                                        
Punto clave                                                                            

Las reglas viven exclusivamente en el frontend (localStorage). El backend es           
completamente stateless respecto a reglas — solo las recibe al momento de evaluar y no
las persiste.           