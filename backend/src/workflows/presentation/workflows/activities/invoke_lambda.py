"""Activity that invokes a vnext-tools Lambda synchronously and returns
its `data` payload.

The underlying boto3 client is sync; to keep the activity fully async
(and not block the worker's event loop for the duration of a Lambda call,
which can be minutes), the I/O is offloaded to a worker thread via
`asyncio.to_thread`.
"""

from __future__ import annotations

import asyncio
import json

import boto3
from botocore.client import BaseClient
from temporalio import activity
from temporalio.exceptions import ApplicationError

from src.common.domain.entities.workflows.document_processing import InvokeLambdaInput
from src.workflows.domain.constants import NON_RETRYABLE_CODES


class InvokeLambdaActivity:
    def __init__(self, boto3_client: BaseClient | None = None) -> None:
        self._client = boto3_client or boto3.client("lambda")

    @activity.defn(name="invoke_lambda")
    async def invoke_lambda(self, input: InvokeLambdaInput) -> dict:
        data = InvokeLambdaInput.model_validate(input)

        response, body_bytes = await asyncio.to_thread(self._invoke_blocking, data.function_name, data.payload)

        if "FunctionError" in response:
            raise ApplicationError(
                f"Lambda infrastructure error: {response['FunctionError']}",
                non_retryable=False,
            )

        body = json.loads(body_bytes)

        if body.get("status") == "error":
            error_code = body.get("error_code", "unhandled.error")
            message = body.get("message", "Unknown error")
            raise ApplicationError(
                f"[{error_code}] {message}",
                error_code,
                non_retryable=error_code in NON_RETRYABLE_CODES,
            )

        return body.get("data", body)

    def _invoke_blocking(self, function_name: str, payload: dict) -> tuple[dict, bytes]:
        """Sync wrapper that runs in a worker thread; returns the boto3
        response dict (without the streaming body) plus the read bytes."""
        response = self._client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )
        body_bytes = response["Payload"].read()
        return response, body_bytes
