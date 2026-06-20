---
feature: processing-jobs
type: plan
status: implemented
coverage: 80
audited: 2026-06-16
---

# Spec: Orquestacion con Temporal

## Contexto

El pipeline de procesamiento de documentos consta de 4 pasos encadenados:

```
extract_text → classify_pages → extract_fields (x N) → validate_extraction (x N)
```

Cada paso esta implementado como un Lambda independiente. Los resultados intermedios
se almacenan en S3 (`s3://vnext-assets-{stage}/jobs/{job_id}/`) y se referencian
via el campo `source` entre pasos.

## Objetivo

Orquestar el pipeline usando Temporal Framework, invocando los Lambdas existentes
como Activities. Temporal se encarga de la secuencia, reintentos, timeouts, y el
fan-out por cada documento clasificado.

## Enfoque: Activities invocan Lambdas via boto3

Cada Activity invoca un Lambda con `boto3.client("lambda").invoke()`. Los Lambdas
escriben resultados a S3 y retornan `source` (referencia al archivo). El siguiente
Activity pasa esa referencia como input.

### Ventajas

- Reutiliza los Lambdas existentes sin cambios
- Cada Lambda escala independientemente
- Deploy independiente de cada paso
- El flujo S3 ya esta implementado y testeado

## Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                   Temporal Server                        │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │         DocumentProcessingWorkflow                │  │
│  │                                                   │  │
│  │  1. activity: invoke extract_text                 │  │
│  │     └─ retorna { source, metadata }               │  │
│  │                                                   │  │
│  │  2. activity: invoke classify_pages               │  │
│  │     └─ retorna { source, metadata }               │  │
│  │                                                   │  │
│  │  3. for each document (fan-out):                  │  │
│  │     a. activity: invoke extract_fields            │  │
│  │        └─ retorna { source, metadata }            │  │
│  │                                                   │  │
│  │     b. activity: invoke validate_extraction       │  │
│  │        └─ retorna { source, metadata }            │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │              Temporal Worker                       │  │
│  │                                                   │  │
│  │  activities:                                      │  │
│  │    - invoke_lambda(function_name, payload)         │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
   │ extract  │  │ classify │  │ extract  │  │ validate │
   │ _text    │  │ _pages   │  │ _fields  │  │_extract. │
   │ Lambda   │  │ Lambda   │  │ Lambda   │  │ Lambda   │
   └──────────┘  └──────────┘  └──────────┘  └──────────┘
         │              │              │              │
         └──────────────┴──────────────┴──────────────┘
                               │
                        ┌──────────────┐
                        │  S3 Bucket   │
                        │  jobs/{id}/  │
                        └──────────────┘
```

## Workflow Input

```python
@dataclass
class DocumentProcessingInput:
    object_key: str
    extractor: str  # "textract_layout", "documentai", etc.
    document_types: list[dict]  # [{uuid, name, description, fields, validation_rules}]
    job_id: str | None = None  # auto-generado si no se envia
```

## Workflow Output

```python
@dataclass
class DocumentProcessingOutput:
    job_id: str
    documents: list[DocumentResult]

@dataclass
class DocumentResult:
    document_index: int
    document_type: dict
    extraction_source: str  # s3:// ref
    validation_source: str  # s3:// ref
    extracted_values: dict
    validation_results: list[dict]
```

## Activity: invoke_lambda

Una sola Activity generica que invoca cualquier Lambda:

```python
@activity.defn
async def invoke_lambda(input: InvokeLambdaInput) -> dict:
    lambda_client = boto3.client("lambda", region_name="us-east-1")

    response = lambda_client.invoke(
        FunctionName=input.function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(input.payload),
    )

    result = json.loads(response["Payload"].read())

    if result.get("status") == "error":
        raise ApplicationError(f"Lambda {input.function_name} failed: {result}")

    return result
```

```python
@dataclass
class InvokeLambdaInput:
    function_name: str
    payload: dict
```

## Workflow Implementation

```python
STAGE = os.environ.get("STAGE", "dev")
LAMBDA_PREFIX = f"vnext-tools"

@workflow.defn
class DocumentProcessingWorkflow:

    @workflow.run
    async def run(self, input: DocumentProcessingInput) -> DocumentProcessingOutput:
        job_id = input.job_id or str(uuid4())
        s3_store = S3JobResultStore(bucket=f"vnext-assets-{STAGE}")

        # 1. Extract text (OCR)
        extract_result = await workflow.execute_activity(
            invoke_lambda,
            InvokeLambdaInput(
                function_name=f"{LAMBDA_PREFIX}-extract_text-{STAGE}",
                payload={
                    "object_key": input.object_key,
                    "extractor": input.extractor,
                    "job_id": job_id,
                    "inline_response": False,
                },
            ),
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        # 2. Classify pages
        classify_result = await workflow.execute_activity(
            invoke_lambda,
            InvokeLambdaInput(
                function_name=f"{LAMBDA_PREFIX}-classify_pages-{STAGE}",
                payload={
                    "source": extract_result["source"],
                    "document_types": input.document_types,
                    "job_id": job_id,
                    "inline_response": False,
                },
            ),
            start_to_close_timeout=timedelta(minutes=3),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        # 3 + 4. For each document: extract fields + validate
        total_documents = classify_result["metadata"]["total"]
        documents = []

        for doc_index in range(total_documents):
            # 3. Extract fields
            extract_fields_result = await workflow.execute_activity(
                invoke_lambda,
                InvokeLambdaInput(
                    function_name=f"{LAMBDA_PREFIX}-extract_fields-{STAGE}",
                    payload={
                        "source": classify_result["source"],
                        "document_index": doc_index,
                        "job_id": job_id,
                        "inline_response": False,
                    },
                ),
                start_to_close_timeout=timedelta(minutes=3),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )

            # 4. Validate extraction
            validate_result = await workflow.execute_activity(
                invoke_lambda,
                InvokeLambdaInput(
                    function_name=f"{LAMBDA_PREFIX}-validate_extraction-{STAGE}",
                    payload={
                        "source": extract_fields_result["source"],
                        "job_id": job_id,
                        "inline_response": False,
                    },
                ),
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )

            # Leer resultados completos desde S3
            validation_data = s3_store.read(validate_result["source"])

            documents.append(DocumentResult(
                document_index=doc_index,
                document_type=validation_data["document_type"],
                extraction_source=extract_fields_result["source"],
                validation_source=validate_result["source"],
                extracted_values=validation_data["extracted_values"],
                validation_results=validation_data["validation_results"],
            ))

        return DocumentProcessingOutput(job_id=job_id, documents=documents)
```

## Timeouts y Reintentos

| Lambda | Timeout | Reintentos | Razon |
|--------|---------|------------|-------|
| extract_text | 5 min | 2 | OCR async puede ser lento |
| classify_pages | 3 min | 2 | LLM call |
| extract_fields | 3 min | 2 | LLM call |
| validate_extraction | 5 min | 2 | Multiples agentes especialistas |

## Fan-out: Secuencial vs Paralelo

El ejemplo anterior procesa documentos secuencialmente. Para paralelizar:

```python
# Paralelo: todos los extract_fields al mismo tiempo
extract_tasks = [
    workflow.execute_activity(
        invoke_lambda,
        InvokeLambdaInput(
            function_name=f"{LAMBDA_PREFIX}-extract_fields-{STAGE}",
            payload={
                "source": classify_result["source"],
                "document_index": i,
                "job_id": job_id,
                "inline_response": False,
            },
        ),
        start_to_close_timeout=timedelta(minutes=3),
    )
    for i in range(total_documents)
]
extract_results = await asyncio.gather(*extract_tasks)
```

Recomendacion: empezar secuencial, paralelizar si el volumen lo justifica.

## Worker Setup

```python
async def main():
    client = await Client.connect("temporal-server:7233")

    worker = Worker(
        client,
        task_queue="document-processing",
        workflows=[DocumentProcessingWorkflow],
        activities=[invoke_lambda],
    )

    await worker.run()
```

## Consideraciones

### Variables de entorno del Worker

El worker solo necesita:
- `AWS_REGION` — para boto3
- `STAGE` — para construir los nombres de Lambda
- Credenciales AWS con permiso `lambda:InvokeFunction`

No necesita las credenciales de Google, Textract, etc. — esas estan en los Lambdas.

### Idempotencia

Los Lambdas escriben a S3 con rutas deterministas (`jobs/{job_id}/extract_text.json`).
Si Temporal reintenta un Activity, el Lambda sobreescribe el mismo archivo. Esto es
seguro y mantiene la consistencia.

### Monitoreo

- **Temporal UI**: visualiza el progreso del workflow, historial de activities
- **CloudWatch**: logs y metricas de cada Lambda (via Powertools)
- **S3**: resultados intermedios accesibles para debugging

### Escalamiento futuro

Si se migra al enfoque B (logica directa en el worker), los use cases ya estan
desacoplados de Lambda:

```python
# Enfoque B: usar use cases directamente en activities
@activity.defn
async def extract_fields_activity(input: ExtractFieldsInput) -> dict:
    return FieldExtractor(
        pages=input.pages,
        document_type_id=input.document_type_id,
        fields_schema=input.fields_schema,
        extraction_service=AgnoTextExtractionService.with_gemini(...),
    ).execute()
```

Los use cases (`FieldExtractor`, `ExtractionValidator`, `DocumentClassifier`, `ExtractDocument`)
no dependen de Lambda, S3, ni Powertools. Solo reciben datos y retornan datos.

## Plan de implementacion

### Fase 1: Infraestructura
1. Agregar dependencia `temporalio` al proyecto
2. Crear modulo `src/temporal/` con worker, workflow, y activities
3. Configurar conexion a Temporal Server

### Fase 2: Activity
4. Implementar `invoke_lambda` activity
5. Testear invocando cada Lambda individualmente

### Fase 3: Workflow
6. Implementar `DocumentProcessingWorkflow`
7. Testear el flujo completo con un documento de prueba

### Fase 4: Deploy
8. Dockerizar el worker
9. Deploy del worker (ECS, EC2, o Kubernetes)
10. Configurar Temporal namespace y task queue
