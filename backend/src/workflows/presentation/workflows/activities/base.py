import json

import boto3
from botocore.client import BaseClient
from temporalio.exceptions import ApplicationError

from src.workflows.domain.activities.base import BaseActivity
from src.workflows.domain.constants import NON_RETRYABLE_CODES


class LambdaActivity(BaseActivity):
    def __init__(self, boto3_client: BaseClient | None = None) -> None:
        self._client = boto3_client or boto3.client("lambda")

    async def invoke_activity(self, payload: dict, function_name: str, *args, **kwargs) -> dict:
        response = self._client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )

        if "FunctionError" in response:
            raise ApplicationError(
                f"Lambda infrastructure error: {response['FunctionError']}",
                non_retryable=False,
            )

        body = json.loads(response["Payload"].read())

        if body.get("status") == "error":
            error_code = body.get("error_code", "unhandled.error")
            message = body.get("message", "Unknown error")
            raise ApplicationError(
                f"[{error_code}] {message}",
                error_code,
                non_retryable=error_code in NON_RETRYABLE_CODES,
            )

        return body["data"]
