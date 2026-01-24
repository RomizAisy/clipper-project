import ffmpeg
import os

def extract_audio(input_path:str, job_dir:str)->str:

    audio_path = os.path.join(job_dir, "audio.wav")

    try:
        (
            ffmpeg
            .input(input_path)
            .output(
                audio_path, 
                format="wav",
                acodec="pcm_s16le",
                    ac=1,
                    ar="16000"
            )
            .overwrite_output()
            .run(quiet=True)
        )

    except ffmpeg.Error as e:
        raise RuntimeError(f"FFmpeg audio extraction failed: {e.stderr.decode()}")

    return audio_path
