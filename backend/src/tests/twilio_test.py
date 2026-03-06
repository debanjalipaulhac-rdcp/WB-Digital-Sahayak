from src.config.twilio_client import get_twilio_client
from src.config.settings import settings


import base64
from src.config.sarvam_client import get_sarvam_client
client = get_sarvam_client()

audio = client.text_to_speech.convert(
    text="I think, this was final. Jai bangla.!",
    model="bulbul:v3",
    target_language_code="bn-IN",
    speaker="kavitha",
    pace=1.0,
    speech_sample_rate=16000
)
from src.storage.s3 import upload_audio
combined_audio = "".join(audio.audios)
b64_file = base64.b64decode(combined_audio)
from src.voice.audio_converter import wav_to_ogg
audio = wav_to_ogg(b64_file)
url = upload_audio(audio, "test3.ogg")
print(url)
def _wa_number(phone: str) -> str:
    """Ensure number is in whatsapp:+91XXXXXXXXXX format."""
    if not phone.startswith("whatsapp:"):
        return f"whatsapp:{phone}"
    return phone
try:
    client = get_twilio_client()
    client.messages.create(
        from_=_wa_number(settings.TWILIO_WHATSAPP_NUMBER),
        to=_wa_number("+919382122857"),
        media_url=[url]
    )
    # logger.info(f"[send_audio] → {phone}: {audio_url}")
except Exception as e:
    # import traceback
    # traceback.print_exc()
    print(f"Response SID: {e.response.sid if hasattr(e, 'response') else 'N/A'}")
    # logger.error(f"[send_audio] Failed for {phone}: {e}")