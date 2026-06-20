import asyncio
import json
from dataclasses import dataclass, field
from uuid import uuid4

from src.common.application.logging import get_logger
from doxiq_shared.infrastructure.lambdas import build_lambda_name, invoke_lambda
from doxiq_shared.infrastructure.s3_bucket import S3Bucket
from src.common.settings import settings
from doxiq_shared.domain.entities.layout import LayoutPage
from src.workflows.domain.services.document_text_extractor import DocumentTextExtractor
from src.workflows.presentation.workflows.activities.read_s3_json import split_s3_uri

logger = get_logger(__name__)


@dataclass
class LambdaSampleTextExtractor(DocumentTextExtractor):
    source_bucket_name: str | None = field(default=None)
    lambda_function_name: str | None = field(default=None)
    lambda_extractor_type: str | None = field(default=None)

    def __post_init__(self) -> None:
        self.source_bucket_name = self.source_bucket_name or settings.AWS_STORAGE_BUCKET_NAME
        self.lambda_function_name = (
                self.lambda_function_name or build_lambda_name(
            prefix=settings.VNEXT_LAMBDA_PREFIX,
            function_name="extract_text",
            stage=str(settings.STAGE),
        )
        )
        self.lambda_extractor_type = self.lambda_extractor_type or settings.EXTRACTION_LAMBDA_EXTRACTOR

    async def extract(self, s3_key: str, **kwargs) -> str:
        job_id = str(uuid4())
        pages = await asyncio.to_thread(self._extract_sync, job_id, s3_key)
        return "\n\n".join(page.formatted_text for page in pages if page.formatted_text)

    def _extract_sync(self, job_id: str, s3_key: str) -> list[LayoutPage]:
        output_uri = self._invoke_lambda(job_id, s3_key)
        if not output_uri:
            return []
        return self._read_pages(output_uri, job_id)

    def _invoke_lambda(self, job_id: str, s3_key: str) -> str | None:
        source_uri = f"s3://{self.source_bucket_name}/{s3_key.lstrip('/')}"
        payload = {
            "job_id": job_id,
            "source_uri": source_uri,
            "extractor": self.lambda_extractor_type,
            "inline_response": False,
            "features": [],
            "force_extraction": False,
        }
        logger.info(
            "lambda_extractor.invoking",
            job_id=job_id,
            function=self.lambda_function_name,
            extractor=self.lambda_extractor_type,
            source_uri=source_uri,
        )
        body = invoke_lambda(self.lambda_function_name, payload)
        logger.info("lambda_extractor.response", job_id=job_id, body=body)

        output_uri = body.get("output_uri")
        if not output_uri:
            logger.warning("lambda_extractor.empty_output_uri", job_id=job_id, body=body)
        return output_uri

    def _read_pages(self, output_uri: str, job_id: str) -> list[LayoutPage]:
        bucket, key = split_s3_uri(output_uri)
        data: dict = json.loads(S3Bucket(bucket).read(key))
        pages: list[dict] = data.get("layouts", {}).get("pages") or []
        if not pages:
            logger.warning("lambda_extractor.empty_pages", job_id=job_id, top_keys=list(data.keys()))
        else:
            logger.info("lambda_extractor.pages_read", job_id=job_id, page_count=len(pages))

        return [LayoutPage.model_validate(page) for page in pages]
