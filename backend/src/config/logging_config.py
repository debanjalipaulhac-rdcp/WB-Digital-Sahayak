"""
src/config/logging_config.py
============================
Call setup_logging() ONCE at app startup (main.py).
After that, every logger.info/error/warning in the entire app
automatically goes to CloudWatch Logs.
"""

import logging
import watchtower
import boto3
from src.config.settings import settings

def setup_logging():
    """
    Route all loggers → CloudWatch Logs.
    Log group: /wb-sahayak/{ENV}
    Log stream: whatsapp / pipeline / webhook etc (by logger name)
    """

    cw_client = boto3.client(
        "logs",
        region_name=settings.AWS_REGION,
    )

    log_group = f"/wb-sahayak/{settings.ENV}"  # e.g. /wb-sahayak/production

    # CloudWatch handler
    cw_handler = watchtower.CloudWatchLogHandler(
        boto3_client=cw_client,
        log_group_name=log_group,
        log_stream_name="application",
        create_log_group=True,       # auto-creates group if not exists
        use_queues=True,             # async — never blocks your pipeline
        send_interval=5,             # flush every 5 seconds
    )

    # Formatter — structured so CloudWatch can filter easily
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    cw_handler.setFormatter(formatter)

    # Console handler (keep for local dev)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Root logger — catches EVERYTHING from all modules
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(cw_handler)
    root_logger.addHandler(console_handler)

    # Silence noisy AWS/botocore logs
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("twilio").setLevel(logging.WARNING)

    logging.info(f"✅ Logging initialized → CloudWatch group: {log_group}")