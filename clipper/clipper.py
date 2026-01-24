import ffmpeg
import os

def cut_topic_clips(video_path, clips, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    output_files = []

    for i, clip in enumerate(clips):
        out_path = os.path.join(output_dir, f"clip_{i+1}.mp4")

        (
            ffmpeg
            .input(video_path, ss=clip["start"], to=clip["end"])
            .output(out_path, c="copy", reset_timestamps=1)
            .overwrite_output()
            .run()
        )

        output_files.append({
            "file": out_path,
            "start": clip["start"],
            "end": clip["end"],
            "text": clip["text"]
        })

    return output_files
