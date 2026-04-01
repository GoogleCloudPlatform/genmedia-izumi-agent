# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MediaMetadata:
    duration: float
    width: int | None = None
    height: int | None = None
    fps: float | None = None


def get_ffmpeg_exe() -> str:
    """Returns the path to the ffmpeg executable."""
    # 1. Check if 'ffmpeg' is in PATH
    exe = shutil.which("ffmpeg")
    if exe:
        return exe

    # 2. Try imageio_ffmpeg
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass

    # 3. Try moviepy (which might have its own config)
    try:
        from moviepy.config import get_setting

        exe = get_setting("FFMPEG_BINARY")
        if exe and os.path.exists(exe):
            return exe
    except ImportError:
        pass

    # Fallback to 'ffmpeg'
    return "ffmpeg"


def get_ffprobe_exe() -> str | None:
    """Returns the path to the ffprobe executable, or None if not found."""
    # 1. Check if 'ffprobe' is in PATH
    exe = shutil.which("ffprobe")
    if exe:
        return exe

    # 2. Derive from ffmpeg path if possible
    ffmpeg_exe = get_ffmpeg_exe()
    if ffmpeg_exe and "ffmpeg" in ffmpeg_exe:
        ffprobe_exe = ffmpeg_exe.replace("ffmpeg", "ffprobe")
        if os.path.exists(ffprobe_exe):
            return ffprobe_exe

    return None


def _get_media_metadata_with_ffmpeg_fallback(file_path: str) -> MediaMetadata:
    """Uses ffmpeg -i to parse metadata as a fallback for ffprobe."""
    logger.info(f"Using ffmpeg fallback for metadata of {file_path}")
    command = [get_ffmpeg_exe(), "-i", file_path]
    # ffmpeg -i without output file returns exit code 1, which is expected
    process = subprocess.run(command, capture_output=True, text=True)
    output = process.stderr

    # Parse duration: Duration: 00:00:04.04
    duration = 0.0
    match = re.search(r"Duration:\s+(\d+):(\d+):(\d+\.\d+)", output)
    if match:
        h, m, s = match.groups()
        duration = int(h) * 3600 + int(m) * 60 + float(s)

    # Parse width, height: 1280x720
    width = None
    height = None
    match = re.search(r",\s+(\d+)x(\d+)", output)
    if match:
        width = int(match.group(1))
        height = int(match.group(2))

    # Parse fps: 25 fps
    fps = None
    match = re.search(r",\s+(\d+(\.\d+)?)\s+fps", output)
    if match:
        fps = float(match.group(1))

    return MediaMetadata(duration=duration, width=width, height=height, fps=fps)


def _create_temp_file_from_blob(blob: bytes, file_extension: str) -> str:
    """
    Writes a blob to a temporary file and returns the file path.
    Ensures the file extension starts with a dot.
    """
    if not file_extension.startswith("."):
        file_extension = f".{file_extension}"

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
        temp_file.write(blob)
        return temp_file.name


def get_media_metadata_from_file(file_path: str) -> MediaMetadata:
    """
    Gets the duration, width, height, and frame rate of a media file using ffprobe.

    Args:
        file_path: The path to the media file.

    Returns:
        MediaMetadata object containing the metadata.
    """
    ffprobe_exe = get_ffprobe_exe()
    if not ffprobe_exe:
        return _get_media_metadata_with_ffmpeg_fallback(file_path)

    command = [
        ffprobe_exe,
        "-v",
        "error",
        "-show_entries",
        "stream=width,height,codec_type,r_frame_rate",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        file_path,
    ]
    try:
        process = subprocess.run(
            command,
            check=True,
            capture_output=True,
        )

        data = json.loads(process.stdout)
        duration = float(data["format"]["duration"])
        width = None
        height = None
        fps = None

        for stream in data["streams"]:
            if stream["codec_type"] == "video":
                width = int(stream["width"])
                height = int(stream["height"])
                if "r_frame_rate" in stream and stream["r_frame_rate"] != "0/0":
                    num, den = map(int, stream["r_frame_rate"].split("/"))
                    if den > 0:
                        fps = num / den
                break

        return MediaMetadata(duration=duration, width=width, height=height, fps=fps)
    except Exception as e:
        logger.warning(f"ffprobe failed ({e}), falling back to ffmpeg")
        return _get_media_metadata_with_ffmpeg_fallback(file_path)


def get_media_metadata_from_blob(blob: bytes, file_extension: str) -> MediaMetadata:
    """
    Gets metadata from a media blob by writing it to a temporary file.

    Args:
        blob: The media content in bytes.
        file_extension: The extension of the file (e.g., "mp4", "mp3").

    Returns:
        MediaMetadata object containing the metadata.
    """
    temp_file_path = ""
    try:
        temp_file_path = _create_temp_file_from_blob(blob, file_extension)
        return get_media_metadata_from_file(temp_file_path)
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def get_total_frames_from_video_file(file_path: str) -> int:
    """Gets the total number of frames in a video file using ffprobe (with ffmpeg fallback)."""
    ffprobe_exe = get_ffprobe_exe()
    if ffprobe_exe:
        command = [
            ffprobe_exe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-count_frames",
            "-show_entries",
            "stream=nb_read_frames",
            "-of",
            "default=nokey=1:noprint_wrappers=1",
            file_path,
        ]
        process = subprocess.run(
            command,
            check=False,
            capture_output=True,
        )

        if process.returncode == 0:
            try:
                return int(process.stdout.decode().strip())
            except ValueError:
                pass

    # Fallback: use metadata approximation
    logger.info("Using metadata approximation for total frames")
    meta = get_media_metadata_from_file(file_path)
    if meta.duration and meta.fps:
        return int(meta.duration * meta.fps)

    raise ValueError(f"Could not determine total frames for video file: {file_path}")


def trim_last_frames_from_video_file(
    file_path: str, output_path: str, num_frames: int
) -> None:
    """
    Trims the last X frames from a video file using ffmpeg.

    Args:
        file_path: Path to the input video file.
        output_path: Path to save the trimmed video.
        num_frames: Number of frames to trim from the end.
    """
    total_frames = get_total_frames_from_video_file(file_path)
    frames_to_keep = max(0, total_frames - num_frames)

    command = [
        get_ffmpeg_exe(),
        "-v",
        "error",
        "-i",
        file_path,
        "-frames:v",
        str(frames_to_keep),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "-y",
        output_path,
    ]

    logger.info(
        f"Trimming last {num_frames} frames. Keeping {frames_to_keep} frames. Command: {' '.join(command)}"
    )

    process = subprocess.run(
        command,
        check=True,
        capture_output=True,
    )

    if process.stderr:
        logger.warning(f"ffmpeg stderr: {process.stderr.decode()}")


def trim_last_frames_from_video_blob(
    blob: bytes, file_extension: str, num_frames: int
) -> bytes:
    """
    Trims the last X frames from a video blob.

    Args:
        blob: The video content in bytes.
        file_extension: The extension of the file (e.g., "mp4").
        num_frames: Number of frames to trim from the end.

    Returns:
        The trimmed video content in bytes.
    """
    input_temp_path = ""
    output_temp_path = ""

    # Ensure extension starts with dot for both input helper and output temp file
    if not file_extension.startswith("."):
        file_extension = f".{file_extension}"

    try:
        input_temp_path = _create_temp_file_from_blob(blob, file_extension)

        # For output, we need an empty temp file to write to
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=file_extension
        ) as output_temp:
            output_temp_path = output_temp.name

        trim_last_frames_from_video_file(input_temp_path, output_temp_path, num_frames)

        with open(output_temp_path, "rb") as f:
            return f.read()

    finally:
        if input_temp_path and os.path.exists(input_temp_path):
            os.remove(input_temp_path)
        if output_temp_path and os.path.exists(output_temp_path):
            os.remove(output_temp_path)


def convert_wav_blob_to_mp3_blob(wav_bytes: bytes) -> bytes:
    """Converts WAV audio bytes to MP3 format using ffmpeg."""
    temp_wav_path = ""
    temp_mp3_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav_file:
            temp_wav_file.write(wav_bytes)
            temp_wav_path = temp_wav_file.name

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_mp3_file:
            temp_mp3_path = temp_mp3_file.name

        # Run ffmpeg to convert WAV to MP3
        command = [
            get_ffmpeg_exe(),
            "-y",
            "-i",
            temp_wav_path,
            "-acodec",
            "libmp3lame",
            "-q:a",
            "2",
            temp_mp3_path,
        ]
        logger.info(f"Running ffmpeg command: {' '.join(command)}")
        process = subprocess.run(
            command,
            check=True,
            capture_output=True,
        )
        logger.info(f"ffmpeg stdout: {process.stdout.decode()}")
        logger.debug(f"ffmpeg stderr: {process.stderr.decode()}")

        with open(temp_mp3_path, "rb") as f:
            mp3_bytes = f.read()
        return mp3_bytes
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg conversion failed: {e.stderr.decode()}")
        raise
    finally:
        # Clean up temporary files
        if temp_wav_path and os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
        if temp_mp3_path and os.path.exists(temp_mp3_path):
            os.remove(temp_mp3_path)
