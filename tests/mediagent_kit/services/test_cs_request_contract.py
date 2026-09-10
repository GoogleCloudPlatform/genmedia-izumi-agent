# Copyright 2026 Google LLC
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

"""Tests for the request Creative Studio actually accepts.

Four ways a well-formed call went wrong at the Creative Studio boundary: a
credential carrying its scheme twice, a workspace quietly swapped for another
one, a null model where the DTO requires a string, and reference images the
caller attached that were never sent. None of them fail locally - they fail as
a 401, a 422, or an answer about a picture the model never saw - so they are
pinned here at the point where the request is assembled.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services import (
    CSAssetService,
    CSMediaGenerationService,
    CSStoryboardService,
    CSTimelineService,
)
from mediagent_kit.services.errors import ValidationError
from mediagent_kit.services.types.common import AssetRef
from mediagent_kit.utils.auth import bearer

# --------------------------------------------------------------------------
# Credentials
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "supplied",
    ["jwt-abc", "Bearer jwt-abc", "bearer jwt-abc", "  Bearer   jwt-abc  "],
)
def test_a_credential_carries_its_scheme_exactly_once(supplied):
    # A token read back from an incoming header arrives already prefixed.
    assert bearer(supplied) == "Bearer jwt-abc"


@pytest.mark.parametrize("empty", [None, "", "   ", "Bearer ", "bearer"])
def test_a_missing_credential_does_not_crash_the_header(empty):
    # Header assembly is not where a missing token should be reported; the
    # services raise for that before they get here. A value that is nothing
    # but the scheme is no credential either, and must not become the token.
    assert bearer(empty) == "Bearer "


@pytest.mark.parametrize(
    "service_cls",
    [CSAssetService, CSTimelineService, CSStoryboardService],
)
def test_services_send_an_undoubled_user_credential(service_cls, monkeypatch):
    monkeypatch.setattr(
        f"{service_cls.__module__}.get_google_id_token", lambda url: None
    )
    service = service_cls(workspace_id="42", user_auth_token="Bearer jwt-abc")

    headers = service._get_headers("Bearer jwt-abc", "https://cs.example/api")

    assert headers["X-User-Authorization"] == "Bearer jwt-abc"


def test_media_generation_sends_an_undoubled_user_credential(monkeypatch):
    module = CSMediaGenerationService.__module__
    monkeypatch.setattr(f"{module}.get_google_id_token", lambda url: None)
    service = CSMediaGenerationService(workspace_id="42", user_auth_token="x")

    headers = service._get_headers("Bearer jwt-abc", "https://cs.example/api")

    assert headers["X-User-Authorization"] == "Bearer jwt-abc"


def test_the_cloud_run_credential_is_a_separate_header(monkeypatch):
    # Two different identities: Cloud Run ingress, and the application user.
    module = CSStoryboardService.__module__
    monkeypatch.setattr(f"{module}.get_google_id_token", lambda url: "id-token-xyz")
    service = CSStoryboardService(workspace_id="42", user_auth_token="jwt-abc")

    headers = service._get_headers("jwt-abc", "https://cs.example/api")

    assert headers["Authorization"] == "Bearer id-token-xyz"
    assert headers["X-User-Authorization"] == "Bearer jwt-abc"


# --------------------------------------------------------------------------
# Workspace
# --------------------------------------------------------------------------


def test_an_explicit_workspace_wins_over_the_ambient_one():
    service = CSStoryboardService(workspace_id="99", user_auth_token="t")

    assert service._get_workspace_id("42") == "42"


def test_an_empty_explicit_workspace_is_refused_not_replaced():
    """The caller asked for a specific workspace and computed it wrongly.

    Falling back would write the campaign into whichever workspace the ambient
    context happens to hold, which is somebody else's.
    """
    service = CSStoryboardService(workspace_id="99", user_auth_token="t")

    with pytest.raises(ValidationError):
        service._get_workspace_id("")


def test_no_explicit_workspace_falls_back_to_the_configured_one():
    service = CSStoryboardService(workspace_id="99", user_auth_token="t")

    assert service._get_workspace_id(None) == "99"


# --------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------


def _payload_model(monkeypatch, method_name, **kwargs):
    """Runs one generate_* call far enough to capture the payload it builds."""
    captured = {}

    class _StubClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None, **kwargs):
            captured.update(json or {})
            raise _Stop()

    class _Stop(Exception):
        pass

    module = CSMediaGenerationService.__module__
    monkeypatch.setattr(f"{module}.get_google_id_token", lambda url: None)
    monkeypatch.setattr(f"{module}.httpx.AsyncClient", lambda **kw: _StubClient())

    service = CSMediaGenerationService(workspace_id="42", user_auth_token="t")
    service._config = MediagentKitConfig()

    import asyncio

    with pytest.raises(_Stop):
        asyncio.run(getattr(service, method_name)(**kwargs))
    return captured.get("generationModel")


def test_a_video_without_an_explicit_model_still_names_one(monkeypatch):
    # A null generationModel is rejected by the backend DTO as a 422.
    model = _payload_model(
        monkeypatch,
        "generate_video",
        workspace_id="42",
        prompt="a hero shot",
        aspect_ratio="16:9",
        duration_seconds=4,
        file_name="scene_1.mp4",
    )

    assert model == MediagentKitConfig().models["video"]["default"]


def test_an_explicit_video_model_is_left_alone(monkeypatch):
    model = _payload_model(
        monkeypatch,
        "generate_video",
        workspace_id="42",
        prompt="a hero shot",
        aspect_ratio="16:9",
        duration_seconds=4,
        file_name="scene_1.mp4",
        generation_model="veo-3.1-generate-001",
    )

    assert model == "veo-3.1-generate-001"


# --------------------------------------------------------------------------
# Reference images
#
# generate_text accepts reference_assets and the native path forwards them to
# Gemini. Creative Studio took them and generated from the prompt alone, so a
# call that asked about a picture was answered without one.
# --------------------------------------------------------------------------


def _text_service(monkeypatch, blobs, captured):
    """A CS media service whose Gemini call records what it was sent."""
    module = CSMediaGenerationService.__module__
    service = CSMediaGenerationService(workspace_id="42", user_auth_token="t")
    service._config = MediagentKitConfig()

    class _Models:
        def generate_content(self, model=None, contents=None):
            captured["contents"] = contents
            return SimpleNamespace(
                candidates=[
                    SimpleNamespace(
                        content=SimpleNamespace(parts=[SimpleNamespace(text="ok")])
                    )
                ],
                text="ok",
            )

    monkeypatch.setattr(
        f"{module}.genai.Client", lambda **kw: SimpleNamespace(models=_Models())
    )

    assets = AsyncMock()
    assets.download_asset_bytes.side_effect = blobs
    monkeypatch.setattr("mediagent_kit.services.aio.get_asset_service", lambda: assets)
    return service


async def test_a_reference_image_reaches_the_model(monkeypatch):
    captured = {}
    service = _text_service(monkeypatch, [b"\x89PNG-bytes"], captured)

    await service.generate_text(
        workspace_id="42",
        prompt="What is in this frame?",
        reference_assets=[AssetRef(id="1", asset_type="generated", workspace_id="42")],
    )

    contents = captured["contents"]
    assert isinstance(contents, list), "the prompt alone answers a different question"
    assert len(contents) == 2
    assert contents[-1] == "What is in this frame?"


async def test_a_call_without_references_is_unchanged(monkeypatch):
    captured = {}
    service = _text_service(monkeypatch, [], captured)

    await service.generate_text(workspace_id="42", prompt="Just text.")

    assert captured["contents"] == "Just text."


async def test_an_unloadable_reference_does_not_fail_the_call(monkeypatch):
    captured = {}
    service = _text_service(monkeypatch, RuntimeError("gone"), captured)

    result = await service.generate_text(
        workspace_id="42",
        prompt="What is in this frame?",
        reference_assets=[AssetRef(id="1", asset_type="generated", workspace_id="42")],
    )

    assert result == "ok"
    assert captured["contents"] == "What is in this frame?"
