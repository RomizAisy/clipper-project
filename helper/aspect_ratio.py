import ffmpeg


def convert_aspect(input_path, output_path, ratio):
    inp = ffmpeg.input(input_path)

    video = inp.video
    audio = inp.audio

    if ratio == "landscape":   # 16:9
        video = (
            video
            .filter("scale", "iw", "ih")
            .filter("crop", "ih*16/9", "ih")
        )

    elif ratio == "portrait":  # 9:16 (center crop)
        video = (
            video
            .filter("scale", "iw", "ih")
            .filter("crop", "ih*9/16", "ih", "(iw-ih*9/16)/2", 0)
        )

    elif ratio == "square":    # 1:1 (if you add later)
        video = video.filter("crop", "min(iw,ih)", "min(iw,ih)")

    elif ratio == "original":
        # fast remux, keeps audio & video
        ffmpeg.output(inp, output_path, c="copy").run(overwrite_output=True)
        return

    ffmpeg.output(
        video,
        audio,
        output_path,
        vcodec="libx264",
        acodec="aac",
        preset="fast",
        crf=23
    ).run(overwrite_output=True)
