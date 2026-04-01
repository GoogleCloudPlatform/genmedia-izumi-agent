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

import logging
import os
import subprocess
import tempfile
import textwrap
from typing import Any

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.utils.media_tools import (
    get_ffmpeg_exe,
    get_media_metadata_from_file,
)

from .asset_service import AssetService
from .types import Asset, VideoClip, VideoTimeline

logger = logging.getLogger(__name__)


class VideoStitchingService:
    """A service for stitching together video and audio clips using ffmpeg.

    This service provides functionality to combine multiple video clips with transitions,
    mix audio tracks, and apply various effects like fades, based on a provided timeline.
    It handles asset management (downloading and saving) through an AssetService instance.
    """

    def __init__(self, asset_service: AssetService, config: MediagentKitConfig):
        """Initializes the VideoStitchingService.

        Args:
            asset_service: The AssetService instance.
            config: The service configuration.
        """
        self._asset_service = asset_service
        self._config = config

    def stitch_video(
        self, user_id: str, timeline: VideoTimeline, output_filename: str
    ) -> Asset:
        """
        Stitches video and audio clips together based on a timeline.

        This is the main method of the service. It orchestrates the entire video stitching process,
        from preparing inputs to running ffmpeg and saving the final output.

        Args:
            user_id: The ID of the user requesting the video stitching.
            timeline: A VideoTimeline object that describes the structure of the video,
                      including video clips, audio clips, and transitions.
            output_filename: The desired filename for the output video.

        Returns:
            An Asset object representing the newly created stitched video.

        Raises:
            ValueError: If video clips have different resolutions or frame rates.
            subprocess.CalledProcessError: If the ffmpeg command fails.
        """
        logger.info(f"Starting video stitching for timeline: {timeline.title}")

        with tempfile.TemporaryDirectory() as temp_dir:
            (
                video_input_params,
                video_files,
                video_metadata,
            ) = self._prepare_video_inputs(timeline, temp_dir, self._asset_service)

            if video_metadata:
                first_width, first_height, first_fps = (
                    video_metadata[0][1],
                    video_metadata[0][2],
                    video_metadata[0][3],
                )
                for i, (_duration, width, height, fps) in enumerate(video_metadata):
                    if width != first_width or height != first_height:
                        logger.warning(
                            f"Resolution mismatch for clip {i} ({width}x{height}) vs target ({first_width}x{first_height}). "
                            "Automatic padding (letterboxing/pillarboxing) will be applied."
                        )
                    if fps != first_fps:
                        # For FPS, we still warn but ffmpeg 'fps' filter will handle it.
                        logger.warning(
                            f"Frame rate mismatch for clip {i} ({fps}) vs target ({first_fps})."
                        )

            audio_input_params, audio_files = self._prepare_audio_inputs(
                timeline, temp_dir, self._asset_service
            )

            video_durations = [meta[0] for meta in video_metadata]
            filter_complex, video_output_stream, audio_output_stream = (
                self._build_filter_complex(
                    timeline,
                    video_files,
                    video_durations,
                    len(audio_files),
                    video_metadata,
                )
            )

            output_path = os.path.join(temp_dir, output_filename)
            self._run_ffmpeg(
                video_input_params,
                audio_input_params,
                filter_complex,
                video_output_stream,
                audio_output_stream,
                bool(video_files),
                output_path,
            )

            final_asset = self._save_output_asset(
                output_path, user_id, output_filename, self._asset_service
            )

            logger.info(f"Successfully stitched video: {timeline.title}")
            return final_asset

    def _create_placeholder_clip(
        self,
        clip: VideoClip,
        temp_dir: str,
        index: int,
        asset_service: AssetService,
        width: int,
        height: int,
    ) -> str:
        """
        Creates a placeholder video clip using ffmpeg.

        This is used when a video clip in the timeline does not have an associated asset.
        It generates a black screen with centered text.

        Args:
            clip: The VideoClip object that needs a placeholder.
            temp_dir: The temporary directory to store the generated clip.
            index: The index of the clip in the timeline, used for naming.
            asset_service: The AssetService instance (unused in this method but
                           kept for potential future use and consistency).
            width: The width of the placeholder video.
            height: The height of the placeholder video.

        Returns:
            The file path to the generated placeholder video.
        """
        placeholder_path = os.path.join(temp_dir, f"placeholder_{index}.mp4")
        text = clip.placeholder if clip.placeholder else f"Placeholder {index + 1}"
        duration = (
            clip.trim.duration_seconds
            if clip.trim and clip.trim.duration_seconds
            else 4
        )

        # Wrap text if it's too long
        font_size = 48
        char_width_approx = font_size * 0.6
        max_chars_per_line = int((width * 0.8) / char_width_approx)
        text = textwrap.fill(text, width=max_chars_per_line)

        # Escape ffmpeg special characters in the text
        text = (
            text.replace("\\", "\\\\")
            .replace("'", r"\'")
            .replace(":", r"\:")
            .replace("%", r"\%")
        )

        # Construct absolute path to the font file
        package_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        font_path = os.path.join(
            package_root, "assets", "fonts", "BitcountGridSingle.ttf"
        )
        logger.info(f"Using font path: {font_path}")

        command = [
            get_ffmpeg_exe(),
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s={width}x{height}:d={duration}",
            "-vf",
            f"drawtext=fontfile={font_path}:text='{text}':x=(w-text_w)/2:y=(h-text_h)/2:fontsize=48:fontcolor=white",
            "-y",
            placeholder_path,
        ]
        process = subprocess.run(
            command,
            check=True,
            capture_output=True,
        )

        if process.stdout:
            logger.info(f"ffmpeg stdout: {process.stdout.decode()}")
        if process.stderr:
            logger.warning(f"ffmpeg stderr: {process.stderr.decode()}")

        return placeholder_path

    def _create_static_video_from_image(
        self,
        image_path: str,
        clip: VideoClip,
        temp_dir: str,
        index: int,
        width: int,
        height: int,
        fps: float,
    ) -> str:
        """
        Creates a static video clip from an image asset.

        Args:
            image_path: Path to the source image.
            clip: The VideoClip object.
            temp_dir: Temporary directory to store the output.
            index: Index of the clip for naming.
            width: Target width.
            height: Target height.
            fps: Target frame rate.

        Returns:
            Path to the generated static video file.
        """
        output_path = os.path.join(temp_dir, f"static_video_{index}.mp4")
        duration = (
            clip.trim.duration_seconds
            if clip.trim and clip.trim.duration_seconds
            else 4
        )

        command = [
            get_ffmpeg_exe(),
            "-loop",
            "1",
            "-i",
            image_path,
            "-c:v",
            "libx264",
            "-t",
            str(duration),
            "-pix_fmt",
            "yuv420p",
            "-vf",
            f"scale=w={width}:h={height}:force_original_aspect_ratio=decrease,pad=w={width}:h={height}:x=(ow-iw)/2:y=(oh-ih)/2",
            "-r",
            str(fps),
            "-y",
            output_path,
        ]
        subprocess.run(command, check=True, capture_output=True)
        return output_path

    def _prepare_video_inputs(
        self, timeline: VideoTimeline, temp_dir: str, asset_service: AssetService
    ) -> tuple[list[str], list[str], list[tuple[float, int, int, float]]]:
        """
        Prepares video inputs for ffmpeg.

        This involves:
        - Downloading the video assets from storage.
        - Creating placeholder videos for clips without assets.
        - Getting metadata for each video (duration, resolution, etc.).
        - Constructing the input file parameters for the ffmpeg command, including
          any trim (`-ss`, `-t`) options.

        Args:
            timeline: The VideoTimeline object.
            temp_dir: The temporary directory to store downloaded and generated files.
            asset_service: The AssetService instance for fetching assets.

        Returns:
            A tuple containing:
            - A list of ffmpeg input parameters for each video file.
            - A list of file paths for the video files.
            - A list of metadata tuples for each video.
        """
        logger.info("Preparing video inputs...")
        video_input_params = []
        video_files = []
        video_metadata = []

        # --- Download all assets and gather their metadata ---
        downloaded_assets: dict[int, Any] = {}
        for i, clip in enumerate(timeline.video_clips):
            if clip.asset:
                blob = asset_service.get_asset_blob(asset_id=clip.asset.id)
                safe_file_name = os.path.basename(clip.asset.file_name)
                video_path = os.path.join(temp_dir, f"video_{i}_{safe_file_name}")
                with open(video_path, "wb") as f:
                    f.write(blob.content)

                metadata = get_media_metadata_from_file(video_path)
                if (
                    metadata.width is None
                    or metadata.height is None
                    or metadata.fps is None
                ):
                    raise ValueError(
                        f"Failed to extract video metadata for asset '{clip.asset.file_name}'. "
                        "Ensure the file is a valid video."
                    )

                duration = metadata.duration
                width = metadata.width
                height = metadata.height
                fps = metadata.fps

                downloaded_assets[i] = (video_path, duration, width, height, fps)

        # --- Determine target resolution and FPS for placeholders ---
        target_width = 1280
        target_height = 720
        target_fps = 24.0

        if downloaded_assets:
            # Get metadata from the first downloaded asset in timeline order
            first_downloaded_index = sorted(downloaded_assets.keys())[0]
            _, _, width, height, fps = downloaded_assets[first_downloaded_index]
            target_width = width
            target_height = height
            target_fps = fps

        # --- Process all clips ---
        for i, clip in enumerate(timeline.video_clips):
            if clip.asset:
                video_path, duration, width, height, fps = downloaded_assets[i]

                # Convert image to static video if needed
                if clip.asset.mime_type.startswith("image/"):
                    logger.info(
                        f"Converting image asset {clip.asset.file_name} to static video."
                    )
                    video_path = self._create_static_video_from_image(
                        video_path,
                        clip,
                        temp_dir,
                        i,
                        target_width,
                        target_height,
                        target_fps,
                    )
                    duration = (
                        clip.trim.duration_seconds
                        if clip.trim and clip.trim.duration_seconds
                        else 4
                    )
                    width, height, fps = target_width, target_height, target_fps

                video_files.append(video_path)
                video_metadata.append((duration, width, height, fps))

                params = []
                if clip.trim and clip.trim.offset_seconds > 0:
                    params.extend(["-ss", str(clip.trim.offset_seconds)])
                if clip.trim and clip.trim.duration_seconds:
                    params.extend(["-t", str(clip.trim.duration_seconds)])
                params.extend(["-i", video_path])
                video_input_params.extend(params)
            else:
                placeholder_path = self._create_placeholder_clip(
                    clip, temp_dir, i, asset_service, target_width, target_height
                )
                video_files.append(placeholder_path)
                duration = (
                    clip.trim.duration_seconds
                    if clip.trim and clip.trim.duration_seconds
                    else 4
                )
                video_metadata.append(
                    (duration, target_width, target_height, target_fps)
                )
                video_input_params.extend(["-i", placeholder_path])

        return video_input_params, video_files, video_metadata

    def _prepare_audio_inputs(
        self, timeline: VideoTimeline, temp_dir: str, asset_service: AssetService
    ) -> tuple[list[str], list[str]]:
        """
        Prepares audio inputs for ffmpeg.

        This involves:
        - Downloading audio assets from storage.
        - Constructing the input file parameters for the ffmpeg command, including
          any trim (`-ss`) options.

        Args:
            timeline: The VideoTimeline object.
            temp_dir: The temporary directory to store downloaded files.
            asset_service: The AssetService instance for fetching assets.

        Returns:
            A tuple containing:
            - A list of ffmpeg input parameters for each audio file.
            - A list of file paths for the audio files.
        """
        logger.info("Preparing audio inputs...")
        audio_input_params = []
        audio_files = []
        if timeline.audio_clips:
            for i, audio_clip in enumerate(timeline.audio_clips):
                if audio_clip.asset:
                    blob = asset_service.get_asset_blob(asset_id=audio_clip.asset.id)
                    safe_file_name = os.path.basename(audio_clip.asset.file_name)
                    audio_path = os.path.join(
                        temp_dir, f"audio_{i}_{safe_file_name}"
                    )
                    with open(audio_path, "wb") as f:
                        f.write(blob.content)
                    audio_files.append(audio_path)

                    params = []
                    if audio_clip.trim and audio_clip.trim.offset_seconds > 0:
                        params.extend(["-ss", str(audio_clip.trim.offset_seconds)])
                    params.extend(["-i", audio_path])
                    audio_input_params.extend(params)
        return audio_input_params, audio_files

    def _build_filter_complex(
        self,
        timeline: VideoTimeline,
        video_files: list[str],
        video_durations: list[float],
        num_audio_files: int,
        video_metadata: list,
    ) -> tuple[str, str, str]:
        """
        Builds the ffmpeg filter_complex string for video and audio processing.

        This is the core of the stitching logic, creating a filter graph to:
        - Normalize and chain video clips with transitions.
        - Apply timeline-level fade effects.
        - Process and mix audio clips with correct timing and effects.

        Args:
            timeline: The VideoTimeline object.
            video_files: A list of paths to the video files.
            video_durations: A list of durations for the original video files.
            num_audio_files: The number of audio files.
            video_metadata: A list of metadata tuples for each video.

        Returns:
            A tuple containing:
            - The complete filter_complex string.
            - The name of the final video output stream from the filter graph.
            - The name of the final audio output stream from the filter graph.
        """
        video_filters = []
        audio_filters = []
        video_output_stream = ""
        audio_output_stream = ""

        num_video_files = len(video_files)

        if num_video_files > 0:
            width, height, fps = (
                video_metadata[0][1],
                video_metadata[0][2],
                video_metadata[0][3],
            )

            # Normalize all video streams to a common timebase, framerate, and resolution
            normalized_streams = []
            for i in range(num_video_files):
                normalized_streams.append(f"[norm_v{i}]")

                clip_speed = timeline.video_clips[i].speed
                speed_filter = f"setpts=PTS/{clip_speed}," if clip_speed != 1.0 else ""

                video_filters.append(
                    f"[{i}:v]{speed_filter}fps={fps},"
                    f"scale=w={width}:h={height}:force_original_aspect_ratio=decrease,"
                    f"pad=w={width}:h={height}:x=(ow-iw)/2:y=(oh-ih)/2,"
                    f"format=yuv420p,settb=AVTB{normalized_streams[i]}"
                )

            clip_durations = []
            for i, clip in enumerate(timeline.video_clips):
                duration = 0.0
                if clip.trim and clip.trim.duration_seconds:
                    duration = clip.trim.duration_seconds
                else:
                    duration = video_durations[i]

                if clip.speed != 1.0:
                    duration = duration / clip.speed

                clip_durations.append(duration)

            clip_start_times = [0.0] * num_video_files
            accumulated_duration = 0.0
            for i in range(num_video_files):
                clip_start_times[i] = accumulated_duration
                transition_duration = 0.0
                if (
                    i < num_video_files - 1
                    and i < len(timeline.transitions)
                    and (transition := timeline.transitions[i]) is not None
                ):
                    transition_duration = transition.duration_seconds
                accumulated_duration += clip_durations[i] - transition_duration

            if num_video_files > 1:
                last_v_stream = normalized_streams[0]
                for i in range(num_video_files - 1):
                    transition = timeline.transitions[i]
                    next_v_stream = normalized_streams[i + 1]
                    output_v_stream = f"[v{i + 1}]"

                    if (
                        transition
                        and transition.type.value != "none"
                        and transition.duration_seconds > 0
                    ):
                        offset = clip_start_times[i + 1]
                        video_filters.append(
                            f"{last_v_stream}{next_v_stream}xfade=transition={transition.type.value}:"
                            f"duration={transition.duration_seconds}:offset={offset}{output_v_stream}"
                        )
                    else:
                        video_filters.append(
                            f"{last_v_stream}{next_v_stream}concat=n=2:v=1:a=0{output_v_stream}"
                        )

                    last_v_stream = output_v_stream
                video_output_stream = last_v_stream
            else:  # num_video_files == 1
                video_output_stream = normalized_streams[0]

            if timeline.transition_in:
                video_filters.append(
                    f"{video_output_stream}fade=t=in:st=0:d={timeline.transition_in.duration_seconds}[v_fadein]"
                )
                video_output_stream = "[v_fadein]"
            if timeline.transition_out:
                video_filters.append(
                    f"{video_output_stream}fade=t=out:st={accumulated_duration - timeline.transition_out.duration_seconds}:d={timeline.transition_out.duration_seconds}[v_fadeout]"
                )
                video_output_stream = "[v_fadeout]"

        if num_audio_files > 0:
            audio_outputs = []
            audio_file_index = 0
            for i, audio_clip in enumerate(timeline.audio_clips):
                if audio_clip.asset:
                    video_clip_start_time = clip_start_times[
                        audio_clip.start_at.video_clip_index
                    ]
                    start_time = (
                        video_clip_start_time + audio_clip.start_at.offset_seconds
                    )

                    audio_stream_index = len(video_files) + audio_file_index
                    audio_file_index += 1

                    chain = []
                    current_stream = f"[{audio_stream_index}:a]"

                    # 1. Trim
                    if audio_clip.trim and audio_clip.trim.duration_seconds:
                        trimmed_stream = f"[a{i}_trimmed]"
                        chain.append(
                            f"{current_stream}atrim=duration={audio_clip.trim.duration_seconds}{trimmed_stream}"
                        )
                        current_stream = trimmed_stream

                    # 2. Speed (atempo)
                    if audio_clip.speed != 1.0:
                        tempo_stream = f"[a{i}_tempo]"
                        chain.append(
                            f"{current_stream}atempo={audio_clip.speed}{tempo_stream}"
                        )
                        current_stream = tempo_stream

                    # 3. Fade in
                    if audio_clip.fade_in_duration_seconds > 0:
                        fadein_stream = f"[a{i}_fadein]"
                        chain.append(
                            f"{current_stream}afade=t=in:st=0:d={audio_clip.fade_in_duration_seconds}{fadein_stream}"
                        )
                        current_stream = fadein_stream

                    # 3. Fade out
                    if (
                        audio_clip.fade_out_duration_seconds > 0
                        and audio_clip.trim
                        and audio_clip.trim.duration_seconds
                    ):
                        fadeout_stream = f"[a{i}_fadeout]"
                        fade_out_start = (
                            audio_clip.trim.duration_seconds
                            - audio_clip.fade_out_duration_seconds
                        )
                        if fade_out_start >= 0:
                            chain.append(
                                f"{current_stream}afade=t=out:st={fade_out_start}:d={audio_clip.fade_out_duration_seconds}{fadeout_stream}"
                            )
                            current_stream = fadeout_stream

                    # 4. Delay
                    delayed_stream = f"[a{i}_delayed]"
                    delay_ms = int(start_time * 1000)
                    chain.append(
                        f"{current_stream}adelay={delay_ms}|{delay_ms}{delayed_stream}"
                    )
                    current_stream = delayed_stream

                    if chain:
                        audio_filters.extend(chain)

                    audio_outputs.append(current_stream)

            if len(audio_outputs) > 1:
                audio_filters.append(
                    f"{''.join(audio_outputs)}amix=inputs={len(audio_outputs)}:duration=longest[audio_mix]"
                )
                audio_output_stream = "[audio_mix]"
            elif len(audio_outputs) == 1:
                audio_filters.append(f"{audio_outputs[0]}acopy[audio_mix]")
                audio_output_stream = "[audio_mix]"

        return (
            ";".join(video_filters + audio_filters),
            video_output_stream,
            audio_output_stream,
        )

    def _run_ffmpeg(
        self,
        video_input_params: list[str],
        audio_input_params: list[str],
        filter_complex: str,
        video_output_stream: str,
        audio_output_stream: str,
        has_video: bool,
        output_path: str,
    ) -> None:
        """
        Constructs and executes the ffmpeg command.

        It logs the stdout and stderr from the ffmpeg process for debugging.

        Args:
            video_input_params: List of ffmpeg input parameters for video files.
            audio_input_params: List of ffmpeg input parameters for audio files.
            filter_complex: The ffmpeg filter_complex string.
            video_output_stream: The name of the final video output stream from the filter.
            audio_output_stream: The name of the final audio output stream from the filter.
            has_video: A boolean indicating if there are any video inputs.
            output_path: The path to write the output file to.

        Raises:
            subprocess.CalledProcessError: If the ffmpeg command returns a non-zero exit code.
        """
        ffmpeg_command = [get_ffmpeg_exe(), *video_input_params, *audio_input_params]

        if filter_complex:
            ffmpeg_command.extend(["-filter_complex", filter_complex])

        if has_video:
            ffmpeg_command.extend(["-map", video_output_stream])

        if audio_output_stream:
            ffmpeg_command.extend(["-map", audio_output_stream])

        # Optimization for constrained environments (Agent Engine)
        ffmpeg_command.extend(
            [
                "-threads",
                "1",  # Minimize thread overhead memory
                "-preset",
                "ultrafast",  # Minimize encoding complexity/memory
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-y",
                output_path,
            ]
        )

        logger.info(f"Executing ffmpeg command: {' '.join(ffmpeg_command)}")

        # Force garbage collection before running heavy subprocess
        import gc

        gc.collect()

        # Use a temporary file for ffmpeg output to avoid memory issues (SIGKILL 9)
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".log", delete=True
        ) as log_file:
            try:
                process = subprocess.run(
                    ffmpeg_command,
                    check=True,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                )
                if process.stdout:
                    logger.info(f"ffmpeg stdout: {process.stdout.decode()}")
                if process.stderr:
                    logger.warning(f"ffmpeg stderr: {process.stderr.decode()}")
            except subprocess.CalledProcessError:
                # Read the last part of the log if it failed
                log_file.seek(0)
                error_output = log_file.read()
                logger.error(f"ffmpeg failed. Log: {error_output}")
                raise

            # Optional: log the success output if needed, but might be very large
            # log_file.seek(0)
            # logger.info(f"ffmpeg output: {log_file.read()}")

    def _save_output_asset(
        self,
        output_path: str,
        user_id: str,
        output_filename: str,
        asset_service: AssetService,
    ) -> Asset:
        """
        Saves the final stitched video to storage and creates an asset record.

        Args:
            output_path: The path to the final video file.
            user_id: The ID of the user.
            output_filename: The desired filename for the output video.
            asset_service: The AssetService instance.

        Returns:
            The newly created Asset.
        """
        logger.info(f"Saving output asset from {output_path}")

        return asset_service.save_asset_from_file(
            user_id=user_id,
            file_name=output_filename,
            file_path=output_path,
            mime_type="video/mp4",
        )
