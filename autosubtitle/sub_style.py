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
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

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
#+++++++++++++++++++++++DEFAULT POTRAIT STYLE+++++++++++++++++++++++++++++++++++++#
def default_portrait(segment, max_words=3):
    frames = []
    words = segment.words

    for i in range(0, len(words), max_words):
        chunk = words[i:i + max_words]

        start = chunk[0].start
        end   = chunk[-1].end

        line = " ".join(
            w.word.strip("{}").replace(".", "").replace(",", "")
            for w in chunk
        )

        frames.append({
            "start": start,
            "end": end,
            "text": line
        })

    return frames

#+++++++++++++++++++++++TIKTOK STYLE+++++++++++++++++++++++++++++++++++++#
def tiktok_style(segment, max_words=3):
    frames = []
    words = segment.words

    for i in range(0, len(words), max_words):
        chunk = words[i:i + max_words]

        start = chunk[0].start
        end   = chunk[-1].end

        current_time = 0
        line = ""

        for w in chunk:
            dur_ms = int((w.end - w.start) * 1000)

            pop_time = min(120, dur_ms // 3)

            text = w.word.strip("{}").upper().replace(".", "").replace(",", "")

            anim = (
                f"\\t({current_time},{current_time+1},\\c&HFFFFFF&)"   # switch to ---- instantly
                f"\\t({current_time},{current_time+pop_time},\\fscx100\\fscy100\\c&H00FF00&))"
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
    words = segment.words

    for i in range(0, len(words), max_words):
        chunk = words[i:i + max_words]

        start = chunk[0].start
        end   = chunk[-1].end

        current_time = 0
        line = ""

        for w in chunk:
            dur_ms = int((w.end - w.start) * 1000)

            pop_time = min(120, dur_ms // 3)
            settle_time = pop_time + 160

            text = w.word.strip("{}").upper().replace(".", "").replace(",", "")

            anim = (
                f"\\t({current_time},{current_time+1},\\c&H00FFFF&)"   # switch to yellow instantly
                f"\\t({current_time},{current_time+pop_time},\\fscx115\\fscy115)"
                f"\\t({current_time+pop_time},{current_time+settle_time},\\fscx100\\fscy100\\c&HFFFFFF&)"
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
def ass_rect(w, h, color):
    return f"{{\\p1\\c{color}}}m 0 0 l {w} 0 {w} {h} 0 {h}{{\\p0}}"

def boxed_style(segment, max_words=3):
    frames = []
    words = segment.words

    for i in range(0, len(words), max_words):
        chunk = words[i:i + max_words]

        start = chunk[0].start
        end   = chunk[-1].end

        current_time = 0
        line = ""

        for w in chunk:
            dur_ms = int((w.end - w.start) * 1000)
            pop_time = min(120, dur_ms // 3)

            text = w.word.strip("{}").replace(".", "").replace(",", "")

            anim = (
                f"\\c&H00B0B0B0&"  # active word 
                f"\\t({current_time},{current_time+pop_time},\\fscx100\\fscy100,\\c&H00000000&)"
                f"\\t({current_time+pop_time},{current_time+pop_time+120},\\fscx100\\fscy100)"
                f"\\t({current_time+pop_time+120},{current_time+pop_time+121})"
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
            words = get_attr(s, "words")

            # If no word timestamps → fallback to normal subtitles
            if not words:
                start = format_ass_time(get_attr(s, "start"))
                end   = format_ass_time(get_attr(s, "end"))
                text  = get_attr(s, "text", "")

                if text:
                    f.write(
                        f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{text}\n"
                    )
                continue

            # TikTok = karaoke
            if style_name == "tiktok":
                frames = tiktok_style(s, max_words=2)

                for frame in frames:
                    start = format_ass_time(frame["start"])
                    end   = format_ass_time(frame["end"])

                    f.write(
                        f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{frame['text']}\n"
                    )

            elif style_name == "default_portrait":
                frames = default_portrait(s, max_words=3)

                for frame in frames:
                    start = format_ass_time(frame["start"])
                    end   = format_ass_time(frame["end"])

                    f.write(
                        f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{frame['text']}\n"
                    )

            # pop
            elif style_name == "pop":

                frames = pop_style(s, max_words=2)

                for frame in frames:
                    start = format_ass_time(frame["start"])
                    end   = format_ass_time(frame["end"])

                    f.write(
                        f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{frame['text']}\n"
                    )

            #boxed
            elif style_name == "boxed":

                frames = boxed_style(s, max_words=3)

                for frame in frames:
                    start = format_ass_time(frame["start"])
                    end   = format_ass_time(frame["end"])

                    f.write(
                        f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{frame['text']}\n"
                    )

            # Default styles = plain subtitles
            else:
                start = format_ass_time(get_attr(s, "start"))
                end   = format_ass_time(get_attr(s, "end"))
                text  = get_attr(s, "text", "")

                f.write(
                    f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{text}\n"
                )






