from clipper.audio import extract_audio
from autosubtitle.whisper import transcribe_audio
from autosubtitle.sub_style import write_ass
from autosubtitle.burn_sub import burn_subtitles

import os

def add_auto_subtitle_fast(
    video_path,
    clip_start,
    clip_end,
    segments,
    job_dir,
    style="default"
):

    clip_segments = slice_segments_for_clip(
        segments,
        clip_start,
        clip_end
    )

    ass_path = os.path.join(job_dir, "subs.ass")

    write_ass(clip_segments, ass_path, style)

    output_path = video_path.replace(".mp4", "_subtitled.mp4")

    burn_subtitles(video_path, ass_path, output_path)

    return output_path



def add_auto_subtitle(video_path, job_dir, style="default"):
    """
    Adds subtitles to ONE video file.
    Returns path to subtitled video.
    """

    audio_path = extract_audio(video_path, job_dir)

    segments, info = transcribe_audio(audio_path)

    ass_path = os.path.join(
        job_dir,
        f"{os.path.splitext(os.path.basename(video_path))[0]}.ass"
    )

    write_ass(segments, ass_path, style)

    output_path = video_path.replace(".mp4", "_subtitled.mp4")

    burn_subtitles(video_path, ass_path, output_path)

    return output_path

def slice_segments_for_clip(segments, clip_start, clip_end):
    clipped = []

    for seg in segments:
        if seg["end"] < clip_start:
            continue
        if seg["start"] > clip_end:
            break

        clipped.append({
            "start": max(seg["start"], clip_start) - clip_start,
            "end": min(seg["end"], clip_end) - clip_start,
            "text": seg["text"]
        })

    return clipped
