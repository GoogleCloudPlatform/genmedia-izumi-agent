import os
from unittest.mock import patch, mock_open
from mediagent_kit.config import MediagentKitConfig

# MEDIAGENT_CONFIG_PATH is emptied rather than left alone so the result does
# not depend on whether the developer has the override set. An empty value is
# falsy, so config resolution skips it and moves on to the remaining
# candidates, which os.path.exists decides.


def test_config_defaults():
    with patch.dict(os.environ, {"MEDIAGENT_CONFIG_PATH": ""}):
        with patch("mediagent_kit.config.os.path.exists", return_value=False):
            config = MediagentKitConfig()
            assert config.models["text"]["default"] == "gemini-4-argon"
            assert config.models["text"]["repair"] == "gemini-4-argon"
            assert config.models["tts"]["default"] == "gemini-3.8-flash-tts"


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
    with patch.dict(os.environ, {"MEDIAGENT_CONFIG_PATH": ""}):
        with patch("mediagent_kit.config.os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=mock_json)):
                config = MediagentKitConfig()
                assert config.models["text"]["default"] == "custom-text-model"
                # Verify that defaults are still there if not overridden
                assert config.models["text"]["repair"] == "gemini-4-argon"
                assert (
                    config.models["image_gemini"]["default"] == "gemini-nano-banana-2.1"
                )
