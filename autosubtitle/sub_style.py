from faster_whisper import WhisperModel


model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)


SUBTITLE_STYLES = {
    "default_movie": {
        "Fontname": "Arial",
        "Fontsize": 12,
        "PrimaryColour": "&H00FFFFFF",
        "OutlineColour": "&H00000000",
        "BackColour": "&H64000000",
        "Bold": 0,
        "Outline": 2,
        "Shadow": 1,
        "Alignment": 2,
        "MarginV": 40,
        "BorderStyle": 1 
    },
    "default_portrait": {
        "Fontname": "Arial",
        "Fontsize": 12,
        "PrimaryColour": "&H00FFFFFF",
        "OutlineColour": "&H00000000",
        "BackColour": "&H64000000",
        "Bold": 0,
        "Outline": 2,
        "Shadow": 1,
        "Alignment": 2,
        "MarginV": 40,
        "BorderStyle": 1 
    },

    "pop": {
        "Fontname": "Arial Black",
        "Fontsize": 22,
        "PrimaryColour": "&H00FFFFFF",
        "OutlineColour": "&H00000000",
        "BackColour": "&H00000000",
        "Bold": 1,
        "Outline": 4,
        "Shadow": 0,
        "Alignment": 2,
        "MarginV":40,
        "BorderStyle": 1 
    },
    "boxed": {
        "Fontname": "Roboto",
        "Fontsize": 18,
        "PrimaryColour": "&H00000000",
        "OutlineColour": "&H00E0E0E0",
        "BackColour": "&H00E0E0E0",   # khusus borderbackground Outline dan BackColor harus sama, kalau tidak ntar default
        "Bold": 1,
        "Outline": 4,                 # box padding
        "Shadow": 0,
        "Alignment": 2,
        "MarginV": 40,
        "BorderStyle": 4
    },

    "tiktok": {
        "Fontname": "Arial Black",
        "Fontsize": 22,
        "PrimaryColour": "&H00FFFFFF",
        "OutlineColour": "&H00000000",
        "BackColour": "&H00000000",
        "Bold": 1,
        "Outline": 4,
        "Shadow": 0,
        "Alignment": 2,
        "MarginV":40,
        "BorderStyle": 1 
    }
}


def format_ass_time(seconds):

    if seconds is None:
        seconds = 0

    seconds = float(seconds)

    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60

    return f"{h}:{m:02}:{s:05.2f}"

def build_ass_style(name, style):
    margin_v = style.get("MarginV", 40)
    border = style.get("BorderStyle", 1)
    return (
        f"Style: {name},"
        f"{style['Fontname']},"
        f"{style['Fontsize']},"
        f"{style['PrimaryColour']},"
        f"&H00FFFFFF,"
        f"{style['OutlineColour']},"
        f"{style['BackColour']},"
        f"{style['Bold']},0,0,0,"
        f"100,100,0,0,{border},"
        f"{style['Outline']},"
        f"{style['Shadow']},"
        f"{style['Alignment']},"
        f"40,40,{margin_v},1\n"
    )
# +++++++++++++++++++++++ DEFAULT PORTRAIT STYLE +++++++++++++++++++++++
def default_portrait(segment, max_words=3):
    frames = []
    words = get_attr(segment, "words", [])

    if not words:
        return frames

    for i in range(0, len(words), max_words):
        chunk = words[i:i + max_words]

        start = get_attr(chunk[0], "start")
        end   = get_attr(chunk[-1], "end")

        if start is None or end is None:
            continue

        line = " ".join(
            get_attr(w, "word", "")
                .strip("{}")
                .replace(".", "")
                .replace(",", "")
            for w in chunk
        )

        frames.append({
            "start": start,
            "end": end,
            "text": line
        })

    return frames


# +++++++++++++++++++++++ TIKTOK STYLE +++++++++++++++++++++++
def tiktok_style(segment, max_words=3):
    frames = []
    words = get_attr(segment, "words", [])

    if not words:
        return frames

    for i in range(0, len(words), max_words):
        chunk = words[i:i + max_words]

        start = get_attr(chunk[0], "start")
        end   = get_attr(chunk[-1], "end")

        if start is None or end is None:
            continue

        current_time = 0
        line = ""

        for w in chunk:
            w_start = get_attr(w, "start")
            w_end   = get_attr(w, "end")
            word    = get_attr(w, "word", "")

            if w_start is None or w_end is None:
                continue

            dur_ms = int((w_end - w_start) * 1000)
            pop_time = min(120, dur_ms // 3)

            text = (
                word.strip("{}")
                    .upper()
                    .replace(".", "")
                    .replace(",", "")
            )

            anim = (
                f"\\t({current_time},{current_time+1},\\c&HFFFFFF&)"
                f"\\t({current_time},{current_time+pop_time},\\fscx100\\fscy100\\c&H00FF00&)"
            )

            line += (
                "{\\c&HFFFFFF&\\fscx100\\fscy100}"
                f"{{{anim}}}{text} "
            )

            current_time += dur_ms

        frames.append({
            "start": start,
            "end": end,
            "text": line.strip()
        })

    return frames


#+++++++++++++++++++++++SEQUENTIAL POP+++++++++++++++++++++++++++++++++++++#
def pop_style(segment, max_words=3):
    frames = []
    words = get_attr(segment, "words", [])

    if not words:
        return frames

    for i in range(0, len(words), max_words):
        chunk = words[i:i + max_words]

        start = get_attr(chunk[0], "start")
        end   = get_attr(chunk[-1], "end")

        current_time = 0
        line = ""

        for w in chunk:
            w_start = get_attr(w, "start")
            w_end   = get_attr(w, "end")
            raw_word = get_attr(w, "word", "")

            if w_start is None or w_end is None:
                continue

            dur_ms = int((w_end - w_start) * 1000)

            pop_time = min(120, dur_ms // 3)
            settle_time = pop_time + 160

            text = (
                raw_word
                .strip("{}")
                .upper()
                .replace(".", "")
                .replace(",", "")
            )

            anim = (
                f"\\t({current_time},{current_time+1},\\c&H00FFFF&)"
                f"\\t({current_time},{current_time+pop_time},\\fscx115\\fscy115)"
                f"\\t({current_time+pop_time},{current_time+settle_time},"
                f"\\fscx100\\fscy100\\c&HFFFFFF&)"
            )

            line += (
                "{\\c&HFFFFFF&\\fscx100\\fscy100}"
                f"{{{anim}}}{text} "
            )

            current_time += dur_ms

        frames.append({
            "start": start,
            "end": end,
            "text": line.strip()
        })

    return frames

#+++++++++++++++++++++++BOXED+++++++++++++++++++++++++++++++++++++#

def boxed_style(segment, max_words=3):
    frames = []
    words = get_attr(segment, "words", [])

    if not words:
        return frames

    for i in range(0, len(words), max_words):
        chunk = words[i:i + max_words]

        start = get_attr(chunk[0], "start")
        end   = get_attr(chunk[-1], "end")

        if start is None or end is None:
            continue

        current_time = 0
        line = ""

        for w in chunk:
            w_start = get_attr(w, "start")
            w_end   = get_attr(w, "end")
            word    = get_attr(w, "word", "")

            if w_start is None or w_end is None:
                continue

            dur_ms = int((w_end - w_start) * 1000)
            pop_time = min(120, dur_ms // 3)

            text = (
                word.strip("{}")
                    .replace(".", "")
                    .replace(",", "")
            )

            anim = (
                f"\\c&H00B0B0B0&"
                f"\\t({current_time},{current_time+pop_time},\\fscx100\\fscy100\\c&H00000000&)"
                f"\\t({current_time+pop_time},{current_time+pop_time+120},\\fscx100\\fscy100)"
            )

            line += f" {{{anim}}}{text}"

            current_time += dur_ms

        frames.append({
            "start": start,
            "end": end,
            "text": line.strip()
        })

    return frames


def get_attr(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

def write_ass(segments, ass_path, style_name="default_portrait"):
    style = SUBTITLE_STYLES.get(style_name, SUBTITLE_STYLES["default_portrait"])

    # ✅ filter invalid segments ONCE
    segments = [
        s for s in segments
        if get_attr(s, "start") is not None
        and get_attr(s, "end") is not None
    ]

    

    with open(ass_path, "w", encoding="utf-8") as f:

        f.write("[Script Info]\nScriptType: v4.00+\n\n")
        f.write("[V4+ Styles]\n")
        f.write("Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,"
                "OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,"
                "ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
                "Alignment,MarginL,MarginR,MarginV,Encoding\n")

        f.write(build_ass_style(style_name, style))
        f.write("\n[Events]\n")
        f.write("Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n")

        # ✅ SINGLE LOOP ONLY
        for s in segments:
            words = get_attr(s, "words")

            # fallback subtitles
            if not words:
                start_sec = get_attr(s, "start")
                end_sec   = get_attr(s, "end")
                text      = get_attr(s, "text", "")

                start = format_ass_time(float(start_sec))
                end   = format_ass_time(float(end_sec))

                if text:
                    f.write(
                        f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{text}\n"
                    )
                continue

            # ---------- STYLE SYSTEM ----------
            if style_name == "tiktok":
                frames = tiktok_style(s, max_words=2)

            elif style_name == "default_portrait":
                frames = default_portrait(s, max_words=3)

            elif style_name == "pop":
                frames = pop_style(s, max_words=2)

            elif style_name == "boxed":
                frames = boxed_style(s, max_words=3)

            elif style_name == "default_movie":
                # ---------- DEFAULT MOVIE STYLE ----------
                start_sec = get_attr(s, "start")
                end_sec   = get_attr(s, "end")
                text      = get_attr(s, "text", "")

                if start_sec is None or end_sec is None or not text:
                    continue

                start = format_ass_time(float(start_sec))
                end   = format_ass_time(float(end_sec))

                f.write(
                    f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{text}\n"
                )
                continue

            # ---------- WRITE FRAMES ----------
            for frame in frames:
                f.write(
                    f"Dialogue: 0,"
                    f"{format_ass_time(frame['start'])},"
                    f"{format_ass_time(frame['end'])},"
                    f"{style_name},,0,0,0,,{frame['text']}\n"
                )
