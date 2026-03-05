from src.storage.s3 import upload_audio

with open("output1.opus", "rb") as f:
    upload_audio(f.read(), "test.ogg")