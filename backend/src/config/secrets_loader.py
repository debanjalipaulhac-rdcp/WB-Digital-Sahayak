# src/config/secrets_loader.py
import boto3
import json
import os
import logging

logger = logging.getLogger(__name__)

def load_secrets():
    """Fetch secrets from Secrets Manager and inject into env at runtime."""
    secret_name = os.environ.get("SECRETS_NAME", "sahayak/secrets")
    region = os.environ.get("AWS_REGION_NAME", "ap-south-1")

    try:
        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=secret_name)
        secrets = json.loads(response["SecretString"])
        print(secrets.items())
        # Inject into environment
        for key, value in secrets.items():
            os.environ[key] = value

        logger.info("Secrets loaded successfully")
    except Exception as e:
        logger.warning(f"Could not load secrets: {e}")