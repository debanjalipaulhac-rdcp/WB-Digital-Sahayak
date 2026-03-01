"""
config/aws_clients.py
======================
Single place to create all AWS service clients.

Why centralise here:
  - One place to configure region, credentials, timeouts
  - Easy to mock in tests (just patch these functions)
  - In Lambda, boto3 uses IAM role credentials automatically
  - Locally, it uses .env.local keys via settings

Usage:
    from config.aws_clients import get_dynamodb, get_s3, get_bedrock
    table = get_dynamodb()
    bucket = get_s3()
"""

import boto3
import logging
from .settings import settings

logger = logging.getLogger(__name__)


def get_dynamodb_resource():
    """
    Returns a DynamoDB resource (high-level API).
    Use this for most operations — cleaner syntax.

    Example:
        resource = get_dynamodb_resource()
        table = resource.Table(settings.DYNAMODB_TABLE_NAME)
        table.put_item(Item={"phone": "+91...", "name": "Sulata"})
    """
    return boto3.resource(
        "dynamodb",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
    )


def get_dynamodb_table():
    """
    Returns the main DynamoDB table directly.
    Shortcut — skips the .Table() call.

    Example:
        table = get_dynamodb_table()
        table.put_item(Item={...})
        response = table.get_item(Key={"phone": "+91..."})
    """
    resource = get_dynamodb_resource()
    return resource.Table(settings.DYNAMODB_TABLE_NAME)


def get_dynamodb_client():
    """
    Returns a DynamoDB low-level client.
    Use this only when you need raw API calls (e.g. create_table in setup scripts).

    Example:
        client = get_dynamodb_client()
        client.create_table(...)
    """
    return boto3.client(
        "dynamodb",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
    )


def get_s3_client():
    """
    Returns an S3 client.

    Example:
        s3 = get_s3_client()
        s3.upload_file("local.ogg", settings.S3_BUCKET_NAME, "audio-cache/name_mismatch_bn.ogg")
        s3.download_file(settings.S3_BUCKET_NAME, "audio-cache/name_mismatch_bn.ogg", "/tmp/out.ogg")
    """
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
    )


def get_bedrock_client():
    """
    Returns an Amazon Bedrock runtime client.
    Used by bedrock.py to call Claude Haiku for AI explanations.

    NOTE: Bedrock model access must be enabled in the AWS console first.
    Go to: AWS Console → Bedrock → Model Access → Request Claude Haiku access

    Example:
        client = get_bedrock_client()
        response = client.invoke_model(
            modelId=settings.BEDROCK_MODEL_ID,
            body=json.dumps({...})
        )
    """
    return boto3.client(
        "bedrock-runtime",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
    )


def get_cloudwatch_client():
    """
    Returns a CloudWatch client for logging custom metrics.
    Used for: tracking how many users ran eligibility checks,
    error rates, scheme popularity, etc.

    Example:
        cw = get_cloudwatch_client()
        cw.put_metric_data(
            Namespace="WBSahayak",
            MetricData=[{"MetricName": "EligibilityChecks", "Value": 1}]
        )
    """
    return boto3.client(
        "cloudwatch",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
    )