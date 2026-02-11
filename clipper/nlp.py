from sentence_transformers import SentenceTransformer, util

def merge_segments(segments, max_gap=0.6):
    merged = []
    current = None

    for seg in segments:
        if not current:
            current = {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"]
            }
            continue

        gap = seg["start"] - current["end"]

        if gap <= max_gap:
            current["end"] = seg["end"]
            current["text"] += " " + seg["text"]
        else:
            merged.append(current)
            current = {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"]
            }

    if current:
        merged.append(current)

    return merged



embedder = SentenceTransformer("all-MiniLM-L6-v2")

def detect_topic_changes(chunks, threshold=0.65):
    texts = [c["text"] for c in chunks]
    embeddings = embedder.encode(texts)

    clips = []
    current = chunks[0].copy()

    for i in range(1, len(chunks)):
        similarity = util.cos_sim(
            embeddings[i-1], embeddings[i]
        ).item()
        print(similarity)
        if similarity < threshold:
            clips.append(current)
            current = chunks[i].copy()
        else:
            current["end"] = chunks[i]["end"]
            current["text"] += " " + chunks[i]["text"]

    clips.append(current)
    return clips

def enforce_min_duration(clips, min_duration=30):
    if not clips:
        return []

    new_clips = []

    current_start = clips[0]["start"]
    current_end = clips[0]["end"]
    current_text = clips[0].get("text", "")

    for clip in clips[1:]:
        duration = current_end - current_start

        if duration < min_duration:
            # extend clip
            current_end = clip["end"]
            current_text += " " + clip.get("text", "")
        else:
            new_clips.append({
                "start": current_start,
                "end": current_end,
                "text": current_text.strip()
            })

            current_start = clip["start"]
            current_end = clip["end"]
            current_text = clip.get("text", "")

    # append last clip
    new_clips.append({
        "start": current_start,
        "end": current_end,
        "text": current_text.strip()
    })

    return new_clips


def split_by_max_duration(clips, max_duration=45.0):
    """
    Split long topic clips into multiple clips
    while keeping the same topic.
    """
    result = []

    for clip in clips:
        start = clip["start"]
        end = clip["end"]
        text = clip["text"]

        duration = end - start

        if duration <= max_duration:
            result.append(clip)
            continue

        current_start = start

        while current_start < end:
            current_end = min(current_start + max_duration, end)

            result.append({
                "start": current_start,
                "end": current_end,
                "text": text
            })

            current_start = current_end

    return result

