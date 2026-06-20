import json

import boto3

from src.common.settings import settings


# TODO: move to doxiq-shared once the shared package exists — these utilities
# are general-purpose AWS Lambda helpers not specific to this service.
def build_lambda_name(prefix: str, function_name: str, stage: str) -> str:
    return f"{prefix}-{function_name}-{stage}"


def invoke_lambda(function_name: str, payload: dict) -> dict:
    client = boto3.client("lambda", region_name=settings.AWS_S3_REGION_NAME)
    response = client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )
    return json.loads(response["Payload"].read().decode("utf-8"))
