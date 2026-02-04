import subprocess
import os

def burn_subtitles(video_path, ass_path, output_path):
    ass_path = os.path.abspath(ass_path)

    # FFmpeg filter escaping (Windows)
    ass_path = ass_path.replace("\\", "/").replace(":", "\\:")

    cmd = [
    "ffmpeg",
    "-y",
    "-i", video_path,
    "-vf", f"subtitles=filename='{ass_path}'",
    "-c:v", "libx264",
    "-crf", "18",
    "-preset", "slow",
    "-c:a", "copy",
    output_path
]

    print("FFMPEG CMD:")
    print(" ".join(cmd))

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    print("FFMPEG STDERR:\n", result.stderr)

    if result.returncode != 0:
        raise RuntimeError("FFmpeg failed to burn subtitles")
