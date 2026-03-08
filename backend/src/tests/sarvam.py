# import base64
# from sarvamai import SarvamAI
# from src.config.sarvam_client import get_sarvam_client
# client = get_sarvam_client()

# audio = client.text_to_speech.convert(
#     text="Welcome to Sarvam AI!",
#     model="bulbul:v3",
#     target_language_code="en-IN",
#     speaker="kavitha",
#     pace=1.0,
#     speech_sample_rate=16000
# )

# combined_audio = "".join(audio.audios)
# b64_file = base64.b64decode(combined_audio)
# print(b64_file[:4])

