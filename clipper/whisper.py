from faster_whisper import WhisperModel


# Load once (IMPORTANT)
model = WhisperModel(
    "small",          # tiny / base / small / medium
    device="cpu",     # or "cuda"
    compute_type="int8"
)

def transcribe_audio(audio_path):
    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        word_timestamps=True
    )

    results = []
    for seg in segments:
        results.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
            "words": seg.words
        })

    return results
