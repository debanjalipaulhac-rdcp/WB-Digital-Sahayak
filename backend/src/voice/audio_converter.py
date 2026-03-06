"""
src/voice/audio_converter.py
Converts WAV bytes (Sarvam TTS output) -> OGG/Vorbis bytes for WhatsApp.

WhatsApp requires: OGG container + Vorbis codec (audio/ogg)
Sarvam TTS returns: WAV (b'RIFF' header)

ffmpeg path resolution:
  Lambda:  /opt/bin/ffmpeg  (from Lambda layer)
  Local:   ffmpeg from system PATH (winget install ffmpeg)
"""

import os
import shutil
import logging
import subprocess
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)


def _get_ffmpeg() -> str:
    """
    Resolve ffmpeg path.
    Lambda layer puts it at /opt/bin/ffmpeg.
    Local dev: must be installed and in PATH.
    """
    if os.path.exists("/opt/bin/ffmpeg"):
        return "/opt/bin/ffmpeg"

    system_path = shutil.which("ffmpeg")
    if system_path:
        return system_path

    raise FileNotFoundError(
        "ffmpeg not found.\n"
        "  Local:  winget install ffmpeg  (then restart terminal)\n"
        "  Lambda: attach ffmpeg layer to your function"
    )


def wav_to_ogg(wav_bytes: bytes) -> Optional[bytes]:
    """
    Convert WAV bytes -> OGG/Vorbis bytes for WhatsApp delivery.
    Returns OGG bytes on success, None on failure.

    OGG + Vorbis confirmed working on WhatsApp.
    OGG + Opus was rejected silently by WhatsApp.
    """
    tmp_wav = None
    tmp_ogg = None

    try:
        ffmpeg = _get_ffmpeg()

        # Write input to temp file
        fd, tmp_wav = tempfile.mkstemp(suffix=".wav")
        os.write(fd, wav_bytes)
        os.close(fd)

        tmp_ogg = tmp_wav.replace(".wav", ".ogg")

        subprocess.run(
            [
                ffmpeg,
                "-y",               # overwrite without prompting
                "-i",   tmp_wav,    # input WAV
                "-c:a", "libopus",
                "-b:a", "24k",
                "-ar", "16000",
                "-ac", "1",
                tmp_ogg
            ],
            check=True,
            capture_output=True     # hide ffmpeg banner from logs
        )

        with open(tmp_ogg, "rb") as f:
            ogg_bytes = f.read()

        # Sanity check — all valid OGG files start with OggS
        if ogg_bytes[:4] != b"OggS":
            logger.error("wav_to_ogg: output is not valid OGG — check ffmpeg install")
            return None

        logger.debug(
            f"wav_to_ogg: {len(wav_bytes):,}B WAV -> "
            f"{len(ogg_bytes):,}B OGG/Vorbis "
            f"({100 * len(ogg_bytes) // len(wav_bytes)}% of original size)"
        )
        return ogg_bytes

    except FileNotFoundError as e:
        logger.error(f"wav_to_ogg: {e}")
        return None

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", errors="ignore")[:300]
        logger.error(f"wav_to_ogg: ffmpeg error: {stderr}")
        return None

    except Exception as e:
        logger.error(f"wav_to_ogg failed: {e}")
        return None

    finally:
        # Always clean up — even if exception thrown
        if tmp_wav and os.path.exists(tmp_wav):
            os.remove(tmp_wav)
        if tmp_ogg and os.path.exists(tmp_ogg):
            os.remove(tmp_ogg)