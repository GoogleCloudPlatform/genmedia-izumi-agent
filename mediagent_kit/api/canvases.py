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

import io
from html.parser import HTMLParser
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

import mediagent_kit
from mediagent_kit.api.types import Canvas, CanvasInfo, CanvasUpdate
from mediagent_kit.services import AssetService, CanvasService
from mediagent_kit.services import types as service_types

router = APIRouter()


def get_canvas_service() -> CanvasService:
    return mediagent_kit.services.get_canvas_service()


def get_asset_service() -> AssetService:
    return mediagent_kit.services.get_asset_service()


@router.get(
    "/users/{user_id}/canvases", response_model=list[CanvasInfo], tags=["Canvases"]
)
def list_canvases(
    user_id: str,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> list[CanvasInfo]:
    """
    Lists all canvases for a specific user.
    """
    canvases = canvas_service.list_canvases(user_id=user_id)
    canvases_info = []
    for canvas in canvases:
        canvas_type = "video_timeline" if canvas.video_timeline else "html"
        canvases_info.append(
            CanvasInfo(
                id=canvas.id,
                title=canvas.title or "Untitled",
                user_id=canvas.user_id,
                canvas_type=canvas_type,
            )
        )
    return canvases_info


@router.get(
    "/users/{user_id}/canvases/{canvas_id}", response_model=Canvas, tags=["Canvases"]
)
def get_canvas(
    user_id: str,
    canvas_id: str,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> Canvas:
    """
    Retrieves a specific canvas by its ID.
    """
    canvas = canvas_service.get_canvas(canvas_id)
    if not canvas or canvas.user_id != user_id:
        raise HTTPException(status_code=404, detail="Canvas not found")
    return canvas


@router.patch(
    "/users/{user_id}/canvases/{canvas_id}", response_model=Canvas, tags=["Canvases"]
)
def update_canvas(
    user_id: str,
    canvas_id: str,
    update_data: CanvasUpdate,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> Canvas:
    """
    Updates a canvas.
    """
    update_args = update_data.model_dump(exclude_unset=True)

    if "title" in update_args:
        if update_args["title"] is None:
            raise HTTPException(status_code=422, detail="Title cannot be null")
        if not update_args["title"].strip():
            raise HTTPException(status_code=422, detail="Title cannot be empty")

    canvas = canvas_service.get_canvas(canvas_id)
    if not canvas or canvas.user_id != user_id:
        raise HTTPException(status_code=404, detail="Canvas not found")

    if not update_args:
        raise HTTPException(status_code=400, detail="No update data provided")

    # Convert Pydantic models to service-layer dataclasses where necessary
    if update_args.get("video_timeline"):
        video_timeline_dict = update_args["video_timeline"]
        update_args["video_timeline"] = service_types.VideoTimeline(
            **video_timeline_dict
        )

    if update_args.get("html"):
        html_dict = update_args["html"]
        update_args["html"] = service_types.Html(**html_dict)

    updated_canvas = canvas_service.update_canvas(canvas_id, **update_args)
    if updated_canvas is None:
        raise HTTPException(status_code=404, detail="Canvas not found")
    return updated_canvas


@router.delete(
    "/users/{user_id}/canvases/{canvas_id}", status_code=204, tags=["Canvases"]
)
def delete_canvas(
    user_id: str,
    canvas_id: str,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
) -> None:
    """
    Deletes a canvas.
    """
    canvas = canvas_service.get_canvas(canvas_id)
    if not canvas or canvas.user_id != user_id:
        # Even if it doesn't exist, from a user perspective, the canvas is gone.
        # So we don't raise an error.
        pass
    else:
        canvas_service.delete_canvas(canvas_id)


class AssetResolvingParser(HTMLParser):
    def __init__(self, user_id: str, asset_service: AssetService):
        super().__init__()
        self._user_id = user_id
        self._asset_service = asset_service
        self._output = io.StringIO()
        self._user_assets: dict[str, service_types.Asset] | None = None

    def get_output(self) -> str:
        return self._output.getvalue()

    def _get_user_assets(self) -> dict[str, service_types.Asset]:
        if self._user_assets is None:
            self._user_assets = {
                asset.file_name: asset
                for asset in self._asset_service.list_assets(user_id=self._user_id)
            }
        return self._user_assets

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._output.write(f"<{tag}")
        for attr, value in attrs:
            if value and value.startswith("asset://"):
                if attr in ("src", "srcset", "data"):
                    uri = value[len("asset://") :]
                    parts = uri.split("/")
                    file_name = parts[0]
                    version = parts[1] if len(parts) > 1 else None
                    asset = self._get_user_assets().get(file_name)
                    if asset:
                        view_url = f"/users/{self._user_id}/assets/{asset.id}/view"
                        if version:
                            view_url += f"?version={version}"
                        value = view_url
            self._output.write(f' {attr}="{value}"')
        self._output.write(">")

    def handle_endtag(self, tag: str) -> None:
        self._output.write(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self._output.write(data)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._output.write(f"<{tag}")
        for attr, value in attrs:
            if value and value.startswith("asset://"):
                if attr in ("src", "srcset", "data"):
                    uri = value[len("asset://") :]
                    parts = uri.split("/")
                    file_name = parts[0]
                    version = parts[1] if len(parts) > 1 else None
                    asset = self._get_user_assets().get(file_name)
                    if asset:
                        view_url = f"/users/{self._user_id}/assets/{asset.id}/view"
                        if version:
                            view_url += f"?version={version}"
                        value = view_url
            self._output.write(f' {attr}="{value}"')
        self._output.write(" />")


@router.get(
    "/users/{user_id}/canvases/{canvas_id}/view",
    response_class=HTMLResponse,
    tags=["Canvases"],
)
def view_canvas(
    user_id: str,
    canvas_id: str,
    canvas_service: Annotated[CanvasService, Depends(get_canvas_service)],
    asset_service: Annotated[AssetService, Depends(get_asset_service)],
) -> HTMLResponse:
    """
    Retrieves and renders a canvas's HTML content, resolving asset URLs.
    """
    canvas = canvas_service.get_canvas(canvas_id)
    if not canvas or canvas.user_id != user_id or not canvas.html:
        raise HTTPException(
            status_code=404, detail="Canvas not found or has no HTML content"
        )

    html_content = canvas.html.content
    parser = AssetResolvingParser(user_id, asset_service)
    parser.feed(html_content)
    resolved_html = parser.get_output()

    return HTMLResponse(content=resolved_html)
