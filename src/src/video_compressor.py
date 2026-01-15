import os
import subprocess
import tempfile
import imageio_ffmpeg

def _probe_duration_seconds(input_path: str) -> float:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    ffprobe = ffmpeg.replace("ffmpeg", "ffprobe") if "ffmpeg" in ffmpeg else ffmpeg
    try:
        cmd = [
            ffprobe, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            input_path
        ]
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode().strip()
        return float(out)
    except Exception:
        return 10.0

def compress_video_to_target_mb(input_path: str, target_mb: float) -> str:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    target_bytes = int(target_mb * 1024 * 1024)
    duration = max(_probe_duration_seconds(input_path), 1.0)

    audio_bps = 96_000
    total_bps = (target_bytes * 8) / duration
    video_bps = max(int(total_bps - audio_bps), 150_000)

    fd, out_path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)

    cmd = [
        ffmpeg, "-y",
        "-i", input_path,
        "-c:v", "libx264",
        "-b:v", str(video_bps),
        "-maxrate", str(video_bps),
        "-bufsize", str(video_bps * 2),
        "-preset", "veryfast",
        "-c:a", "aac",
        "-b:a", str(audio_bps),
        "-movflags", "+faststart",
        out_path
    ]
    subprocess.check_call(cmd)
    return out_path
