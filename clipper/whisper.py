from faster_whisper import WhisperModel

# Load once (GOOD — keep this)
model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)

def transcribe_audio(audio_path):
    print("✅ NEW TRANSCRIBE FUNCTION LOADED")
    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        word_timestamps=True
    )

    results = []

    for seg in segments:
        results.append({
            "start": float(seg.start),
            "end": float(seg.end),
            "text": seg.text.strip(),
            "words": [
                {
                    "word": w.word,
                    "start": float(w.start),
                    "end": float(w.end),
                    "probability": float(w.probability)
                }
                for w in (seg.words or [])
            ]
        })

    return results