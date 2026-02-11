import subprocess
import json
import math


def get_video_duration(video_path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            video_path
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise Exception(result.stderr)

    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def calculate_required_tokens(video_path):
    duration = get_video_duration(video_path)
    return math.ceil(duration / 60)
