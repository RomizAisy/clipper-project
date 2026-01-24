from faster_whisper import WhisperModel


model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)


SUBTITLE_STYLES = {
    "default": {
        "Fontname": "Arial",
        "Fontsize": 12,
        "PrimaryColour": "&H00FFFFFF",
        "OutlineColour": "&H00000000",
        "BackColour": "&H64000000",
        "Bold": 0,
        "Outline": 2,
        "Shadow": 1,
        "Alignment": 2,
        "MarginV": 40
    },

    "bold_center": {
        "Fontname": "Montserrat",
        "Fontsize": 24,
        "PrimaryColour": "&H00FFFFFF",
        "OutlineColour": "&H00000000",
        "BackColour": "&H00000000",
        "Bold": 1,
        "Outline": 3,
        "Shadow": 0,
        "Alignment": 2,
        "MarginV": 40
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
    "MarginV":40
}
}


def format_ass_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def build_ass_style(name, style):
    margin_v = style.get("MarginV", 40)
    return (
        f"Style: {name},"
        f"{style['Fontname']},"
        f"{style['Fontsize']},"
        f"{style['PrimaryColour']},"
        f"&H00FFFFFF,"
        f"{style['OutlineColour']},"
        f"{style['BackColour']},"
        f"{style['Bold']},0,0,0,"
        f"100,100,0,0,1,"
        f"{style['Outline']},"
        f"{style['Shadow']},"
        f"{style['Alignment']},"
        f"40,40,{margin_v},1\n"
    )

def frames_from_word_timestamps(segment, max_words=1):
    frames = []
    words = segment.words

    for i in range(0, len(words), max_words):
        chunk = words[i:i + max_words]

        start = chunk[0].start
        end   = chunk[-1].end
        text  = " ".join(w.word for w in chunk)

        frames.append({
            "start": start,
            "end": end,
            "text": text
        })

    return frames

def build_karaoke_line(words):
    """
    words = list of word objects with .word .start .end
    """
    line = ""

    for w in words:
        duration_cs = int((w.end - w.start) * 50)
        duration_cs = max(duration_cs, 8)  # safety

        text = w.word.upper().replace("{", "").replace("}", "")
        line += f"{{\\k{duration_cs}}}{text} "

    return line.strip()

def karaoke_frames_from_words(segment, max_words=2):
    frames = []
    words = segment.words

    for i in range(0, len(words), max_words):
        chunk = words[i:i + max_words]

        start = chunk[0].start
        end   = chunk[-1].end
        text  = build_karaoke_line(chunk)

        frames.append({
            "start": start,
            "end": end,
            "text": text
        })

    return frames

def build_pop_karaoke(words):
    line = ""

    for w in words:
        duration_ms = int((w.end - w.start) * 1000)
        duration_cs = max(int(duration_ms / 10), 6)

        pop_time = min(70, int(duration_ms * 0.25))

        text = w.word.upper().replace("{", "").replace("}", "")

        line += (
            "{"
            f"\\k{duration_cs}"              # sequential timing
            "\\c&H0000FFFF&"                 # active yellow
            "\\fscx130\\fscy130"             # pop start
            f"\\t(0,{pop_time},\\fscx100\\fscy100)"
            "}"
            f"{text} "
        )

    return line.strip()


def pop_frames_from_words(segment, max_words=3):
    frames = []
    words = segment.words

    for i in range(0, len(words), max_words):
        chunk = words[i:i + max_words]

        start = chunk[0].start
        end   = chunk[-1].end

        text = build_pop_karaoke(chunk)

        frames.append({
            "start": start,
            "end": end,
            "text": text
        })

    return frames

def write_ass(segments, ass_path, style_name="default"):
    style = SUBTITLE_STYLES.get(style_name, SUBTITLE_STYLES["default"])

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

        for s in segments:
            if not s.words:
                continue

            # 🔥 TikTok = karaoke + pop
            if style_name == "tiktok":
                frames = pop_frames_from_words(s, max_words=3)

                for frame in frames:
                    start = format_ass_time(frame["start"])
                    end   = format_ass_time(frame["end"])
                    text  = frame["text"]

                    f.write(
                        f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{text}\n"
                    )

            # 🧘 Default styles = plain subtitles
            else:
                start = format_ass_time(s.start)
                end   = format_ass_time(s.end)
                text  = s.text

                f.write(
                    f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{text}\n"
                )






