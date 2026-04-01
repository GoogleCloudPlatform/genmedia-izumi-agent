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
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse, StreamingResponse

import mediagent_kit.services
import mediagent_kit.services.aio
from mediagent_kit.api.types import Asset, AssetUpdate
from mediagent_kit.services import AssetService
from mediagent_kit.services.aio import AsyncAssetService

router = APIRouter()


def get_asset_service() -> AssetService:
    return mediagent_kit.services.get_asset_service()


def get_async_asset_service() -> AsyncAssetService:
    return mediagent_kit.services.aio.get_asset_service()


@router.post("/users/{user_id}/assets", response_model=Asset, tags=["Assets"])
async def create_asset(
    user_id: str,
    file: Annotated[UploadFile, File()],
    file_name: Annotated[str, Form()],
    mime_type: Annotated[str, Form()],
    asset_service: Annotated[AsyncAssetService, Depends(get_async_asset_service)],
) -> Asset:
    """
    Creates a new asset by uploading a file. If an asset with the same file_name
    for the user already exists, a new version will be created.
    """
    content = await file.read()
    try:
        asset = await asset_service.save_asset(
            user_id=user_id,
            file_name=file_name,
            blob=content,
            mime_type=mime_type,
        )
        return asset
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/users/{user_id}/assets", response_model=list[Asset], tags=["Assets"])
def list_assets(
    user_id: str,
    asset_service: Annotated[AssetService, Depends(get_asset_service)],
) -> list[Asset]:
    """
    Lists all assets for a specific user.
    """
    return asset_service.list_assets(user_id=user_id)


@router.get("/users/{user_id}/assets/{asset_id}", response_model=Asset, tags=["Assets"])
def get_asset(
    user_id: str,
    asset_id: str,
    asset_service: Annotated[AssetService, Depends(get_asset_service)],
) -> Asset:
    """
    Retrieves a specific asset by its ID.
    """
    asset = asset_service.get_asset_by_id(asset_id)
    if not asset or asset.user_id != user_id:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.patch(
    "/users/{user_id}/assets/{asset_id}", response_model=Asset, tags=["Assets"]
)
def update_asset(
    user_id: str,
    asset_id: str,
    update_data: AssetUpdate,
    asset_service: Annotated[AssetService, Depends(get_asset_service)],
) -> Asset:
    """
    Updates an asset's metadata (e.g., file_name).
    """
    asset = asset_service.get_asset_by_id(asset_id)
    if not asset or asset.user_id != user_id:
        raise HTTPException(status_code=404, detail="Asset not found")

    update_args = update_data.model_dump(exclude_unset=True)
    if not update_args:
        raise HTTPException(status_code=400, detail="No update data provided")

    updated_asset = asset_service.update_asset(asset_id, **update_args)
    if updated_asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return updated_asset


@router.delete("/users/{user_id}/assets/{asset_id}", status_code=204, tags=["Assets"])
def delete_asset(
    user_id: str,
    asset_id: str,
    asset_service: Annotated[AssetService, Depends(get_asset_service)],
) -> None:
    """
    Deletes an asset and all its versions.
    """
    asset = asset_service.get_asset_by_id(asset_id)
    if not asset or asset.user_id != user_id:
        raise HTTPException(status_code=404, detail="Asset not found")
    else:
        asset_service.delete_asset(asset_id)


@router.get("/users/{user_id}/assets/{asset_id}/download", tags=["Assets"])
def download_asset(
    user_id: str,
    asset_id: str,
    asset_service: Annotated[AssetService, Depends(get_asset_service)],
    version: int | None = None,
) -> StreamingResponse:
    """
    Downloads a specific version of an asset. If no version is specified,
    the latest version is downloaded.
    """
    asset = asset_service.get_asset_by_id(asset_id)
    if not asset or asset.user_id != user_id:
        raise HTTPException(status_code=404, detail="Asset not found")

    try:
        asset_blob = asset_service.get_asset_blob(asset_id, version)
        return StreamingResponse(
            io.BytesIO(asset_blob.content),
            media_type=asset_blob.mime_type,
            headers={
                "Content-Disposition": f"attachment; filename={asset_blob.file_name}"
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/users/{user_id}/assets/{asset_id}/view", response_model=None, tags=["Assets"]
)
def view_asset(
    user_id: str,
    asset_id: str,
    request: Request,
    asset_service: Annotated[AssetService, Depends(get_asset_service)],
    version: int | None = None,
) -> StreamingResponse | RedirectResponse:
    """
    Retrieves and displays a specific version of an asset in the browser.
    If no version is specified, it redirects to the URL with the latest version.
    This endpoint supports browser caching.
    """
    asset = asset_service.get_asset_by_id(asset_id)
    if not asset or asset.user_id != user_id:
        raise HTTPException(status_code=404, detail="Asset not found")

    if version is None:
        url = request.url.replace_query_params(version=asset.current_version)
        response = RedirectResponse(url=str(url))
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    try:
        asset_blob = asset_service.get_asset_blob(asset_id, version)
        return StreamingResponse(
            io.BytesIO(asset_blob.content),
            media_type=asset_blob.mime_type,
            headers={
                "Cache-Control": "public, max-age=86400",
                "Access-Control-Allow-Origin": "*",
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
