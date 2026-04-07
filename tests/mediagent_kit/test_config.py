import os
import json
from unittest.mock import patch, mock_open
from pathlib import Path
from mediagent_kit.config import MediagentKitConfig


def test_config_defaults():
    with patch.object(Path, "exists", return_value=False):
        config = MediagentKitConfig()
        assert config.models["text"]["default"] == "gemini-2.5-flash"
        assert config.models["text"]["repair"] == "gemini-2.5-flash"


def test_config_load_file():
    mock_json = """
    {
        "models": {
            "text": {
                "default": "custom-text-model"
            }
        }
    }
    """
    # We need to mock exists for the specific path or just global Path.exists if careful
    with patch.object(Path, "exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=mock_json)):
            config = MediagentKitConfig()
            assert config.models["text"]["default"] == "custom-text-model"
            # Verify that defaults are still there if not overridden
            assert config.models["text"]["repair"] == "gemini-2.5-flash"
            assert config.models["image_imagen"]["default"] == "imagen-4.0-generate-001"
