from faster_whisper import WhisperModel

model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)


def transcribe_audio(audio_path):
    print("2ND WHISPER AUTOSUB")
    # model.transcribe returns a generator
    segments_generator, info = model.transcribe(
        audio_path,
        word_timestamps=True,
        vad_filter=True
    )

    segments = list(segments_generator)  # ✅ convert generator to list

    results = [
        {
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
        }
        for seg in segments
    ]

    info_serialized = {
        "language": info.language,
        "duration": info.duration,
        "num_segments": len(segments)  # ✅ works now
    }

    return results, info_serialized