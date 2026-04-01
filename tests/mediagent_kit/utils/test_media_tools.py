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
import os
import subprocess
import unittest.mock
import pytest

from mediagent_kit.utils import media_tools


def test_get_ffmpeg_exe_from_path():
    """Verifies get_ffmpeg_exe checks shutil.which first."""
    with unittest.mock.patch("shutil.which", return_value="/usr/bin/ffmpeg"):
        assert media_tools.get_ffmpeg_exe() == "/usr/bin/ffmpeg"


def test_get_ffprobe_exe_from_path():
    """Verifies get_ffprobe_exe checks shutil.which first."""
    with unittest.mock.patch("shutil.which", return_value="/usr/bin/ffprobe"):
        assert media_tools.get_ffprobe_exe() == "/usr/bin/ffprobe"


def test_get_ffprobe_exe_derived_from_ffmpeg():
    """Verifies get_ffprobe_exe derives from ffmpeg path if not in path."""
    with unittest.mock.patch("shutil.which", side_effect=[None, None]): # Not for ffprobe, not for ffmpeg in path
        with unittest.mock.patch.object(media_tools, "get_ffmpeg_exe", return_value="/custom/path/ffmpeg"):
            with unittest.mock.patch("os.path.exists", return_value=True):
                assert media_tools.get_ffprobe_exe() == "/custom/path/ffprobe"


def test_get_media_metadata_from_file_success_ffprobe():
    """Verifies get_media_metadata_from_file parses JSON correctly from ffprobe."""
    mock_ffprobe_output = {
        "format": {"duration": "10.5"},
        "streams": [{"codec_type": "video", "width": 1280, "height": 720, "r_frame_rate": "30/1"}]
    }
    
    # Mock subprocess.run to return the JSON above
    mock_run = unittest.mock.MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = json.dumps(mock_ffprobe_output).encode()
    
    with unittest.mock.patch("shutil.which", return_value="/usr/bin/ffprobe"):
        with unittest.mock.patch("subprocess.run", return_value=mock_run):
            meta = media_tools.get_media_metadata_from_file("dummy.mp4")
            
            assert meta.duration == 10.5
            assert meta.width == 1280
            assert meta.height == 720
            assert meta.fps == 30.0


def test_get_media_metadata_from_file_ffmpeg_fallback():
    """Verifies get_media_metadata_from_file falls back to ffmpeg parsing text output."""
    # First call to run will be ffprobe (fails or raises)
    # Second call will be ffmpeg fallback (simulates stderr output)
    
    # Simulating ffprobe failure or not found
    # Let's mock get_ffprobe_exe to return None to force fallback
    with unittest.mock.patch.object(media_tools, "get_ffprobe_exe", return_value=None):
        # Now mock subprocess.run for ffmpeg -i
        mock_run_ffmpeg = unittest.mock.MagicMock()
        mock_run_ffmpeg.returncode = 1 # expected for ffmpeg -i without output
        mock_run_ffmpeg.stderr = "Duration: 00:01:23.45, start: 0.000000, bitrate: 123 kb/s\n Stream #0:0: Video: h264, yuv420p, 1920x1080 [SAR 1:1 DAR 16:9], 24 fps, ..."
        
        with unittest.mock.patch("subprocess.run", return_value=mock_run_ffmpeg):
            meta = media_tools.get_media_metadata_from_file("dummy.mp4")
            
            assert meta.duration == 83.45 # 1m 23.45s = 60 + 23.45
            assert meta.width == 1920
            assert meta.height == 1080
            assert meta.fps == 24.0


def test_convert_wav_blob_to_mp3_blob():
    """Verifies convert_wav_blob_to_mp3_blob calls ffmpeg and returns bytes."""
    mock_run = unittest.mock.MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = b"success"
    mock_run.stderr = b"logs"
    
    # We also need to mock tempfile.NamedTemporaryFile and open
    with unittest.mock.patch("subprocess.run", return_value=mock_run) as mock_run_func:
        with unittest.mock.patch("os.path.exists", return_value=True):
            # We need to mock open to return simulated bytes
            m_open = unittest.mock.mock_open(read_data=b"fake_mp3_bytes")
            with unittest.mock.patch("builtins.open", m_open):
                result = media_tools.convert_wav_blob_to_mp3_blob(b"fake_wav_bytes")
                
                assert result == b"fake_mp3_bytes"
                # Check that ffmpeg was called
                called_args = mock_run_func.call_args[0][0]
                assert "-acodec" in called_args
                assert "libmp3lame" in called_args
