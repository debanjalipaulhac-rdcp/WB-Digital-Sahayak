import boto3
import time
import functools
import logging
from .settings import settings

logger = logging.getLogger(__name__)

# ── CloudWatch Client ─────────────────────────────────────────────────────────
cw = boto3.client(
    "cloudwatch",
    region_name=settings.AWS_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)

NAMESPACE = "WBSahayak"  # Your custom metrics namespace


# ── 1. SEND CUSTOM METRIC ─────────────────────────────────────────────────────
def put_metric(metric_name: str, value: float, unit: str = "Count", dimensions: dict = {}):
    """
    Send any custom metric to CloudWatch.
    Call this from anywhere in your code.
    """
    try:
        cw.put_metric_data(
            Namespace=NAMESPACE,
            MetricData=[{
                "MetricName": metric_name,
                "Value": value,
                "Unit": unit,
                "Dimensions": [
                    {"Name": k, "Value": v}
                    for k, v in dimensions.items()
                ]
            }]
        )
    except Exception as e:
        # Never crash your app because of monitoring
        logger.warning(f"CloudWatch metric failed: {e}")


# ── 2. DECORATOR — AUTO TRACK LATENCY + ERRORS ────────────────────────────────
def track(metric_name: str):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            logger.info(f"[{metric_name}] START")  # ← add
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                put_metric(f"{metric_name}.latency", duration_ms, "Milliseconds")
                put_metric(f"{metric_name}.success", 1)
                logger.info(f"[{metric_name}] OK | {duration_ms:.0f}ms")  # ← add
                return result
            except Exception as e:
                put_metric(f"{metric_name}.error", 1)
                logger.error(f"[{metric_name}] FAILED | {e}", exc_info=True)  # ← add
                raise
        return wrapper
    return decorator


# ── 3. KEY BUSINESS METRICS — CALL THESE MANUALLY ────────────────────────────
def track_whatsapp_message_received(phone_number: str):
    put_metric("whatsapp.message.received", 1, dimensions={"channel": "whatsapp"})

def track_voice_note_received():
    put_metric("voice.note.received", 1)

def track_eligibility_check_completed(scheme: str, score: int):
    put_metric("eligibility.completed", 1, dimensions={"scheme": scheme})
    put_metric("eligibility.score", score, "None", dimensions={"scheme": scheme})

def track_name_mismatch_detected():
    """This is your KILLER FEATURE — track every time it fires"""
    put_metric("mismatch.name.detected", 1)

def track_sarvam_stt_call(duration_seconds: float):
    put_metric("sarvam.stt.duration", duration_seconds, "Seconds")

def track_bedrock_call(tokens_used: int):
    put_metric("bedrock.tokens.used", tokens_used, "Count")

def track_session_started(channel: str):
    """channel = 'whatsapp' or 'web'"""
    put_metric("session.started", 1, dimensions={"channel": channel})