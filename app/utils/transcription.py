from typing import BinaryIO


def transcribe_audio(file: BinaryIO) -> str:
    """Stub Urdu speech-to-text.

    The real implementation should load a pretrained Urdu Whisper model and
    decode the uploaded audio. This placeholder lets the `/transcribe` endpoint
    respond immediately during early integration.
    """
    # Read a few bytes just to confirm a file arrived.
    file.read(1)
    file.seek(0)
    return "یہاں اردو تقریر کا متن آئے گا"
