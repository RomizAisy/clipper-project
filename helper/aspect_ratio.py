import ffmpeg


def convert_aspect(input_path, output_path, ratio):
    inp = ffmpeg.input(input_path)

    video = inp.video
    audio = inp.audio

    if ratio == "landscape":  # 16:9
        video = video.filter(
            "crop",
            "min(iw,ih*16/9)",
            "min(ih,iw*9/16)",
            "(iw-min(iw,ih*16/9))/2",
            "(ih-min(ih,iw*9/16))/2"
        )

    elif ratio == "portrait":  # 9:16
        video = video.filter(
            "crop",
            "min(iw,ih*9/16)",
            "ih",
            "(iw-min(iw,ih*9/16))/2",
            0
        )

    elif ratio == "square":
        video = video.filter(
            "crop",
            "min(iw,ih)",
            "min(iw,ih)"
        )

    elif ratio == "original":
        ffmpeg.output(inp, output_path, c="copy").run(overwrite_output=True)
        return

    (
        ffmpeg
        .output(
            video,
            audio,
            output_path,
            vcodec="libx264",
            acodec="aac",
            preset="fast",
            crf=23,
            **{
                "fps_mode": "cfr",     # ✅ replaces vsync
                "fflags": "+genpts",
                "movflags": "+faststart",
                "g": "48",             # frequent keyframes
                "keyint_min": "48"
            }
        )
        .run(overwrite_output=True)
    )
