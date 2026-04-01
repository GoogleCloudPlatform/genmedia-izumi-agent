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

import dataclasses
import uuid
from typing import Any

from firebase_admin import firestore

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services import types
from mediagent_kit.services.asset_service import AssetService
from mediagent_kit.services.base_service import BaseService


class CanvasService(BaseService):
    """Service for managing canvases in Firestore."""

    def __init__(
        self,
        db: firestore.Client,
        asset_service: AssetService,
        config: MediagentKitConfig,
    ):
        """Initializes the CanvasService.

        Args:
            db: The Firestore client.
            asset_service: The AssetService.
            config: The service configuration.
        """
        super().__init__(db)
        self._config = config
        self.canvases_collection = self._get_collection("canvases")
        self._asset_service = asset_service

    def create_canvas(
        self,
        user_id: str,
        title: str,
        video_timeline: types.VideoTimeline | None = None,
        html: types.Html | None = None,
    ) -> types.Canvas:
        """Creates a new canvas in Firestore.

        Args:
            user_id: The ID of the user creating the canvas.
            title: The title of the canvas.
            video_timeline: The video timeline for the canvas.
            html: The HTML content for the canvas.

        Returns:
            The created canvas.
        """
        canvas_id = str(uuid.uuid4())
        canvas = types.Canvas(
            id=canvas_id,
            user_id=user_id,
            title=title,
            video_timeline=video_timeline,
            html=html,
        )
        self.canvases_collection.document(canvas_id).set(canvas.to_firestore())
        return canvas

    def get_canvas(self, canvas_id: str) -> types.Canvas | None:
        """Gets a canvas from database.

        Args:
            canvas_id: The ID of the canvas to get.

        Returns:
            The canvas, or None if it does not exist.
        """
        canvas_doc = self.canvases_collection.document(canvas_id).get()
        if canvas_doc.exists:
            return types.Canvas.from_firestore(
                canvas_doc.to_dict(), asset_service=self._asset_service
            )
        return None

    def list_canvases(self, user_id: str) -> list[types.Canvas]:
        """Lists all canvases for a user.

        Args:
            user_id: The ID of the user to list canvases for.

        Returns:
            A list of canvases.
        """
        canvases = []
        for doc in self.canvases_collection.where(
            filter=firestore.FieldFilter("user_id", "==", user_id)
        ).stream():
            canvases.append(
                types.Canvas.from_firestore(
                    doc.to_dict(), asset_service=self._asset_service
                )
            )
        return canvases

    def update_canvas(self, canvas_id: str, **kwargs: Any) -> types.Canvas | None:
        """Updates a canvas in Firestore.

        Args:
            canvas_id: The ID of the canvas to update.
            **kwargs: The fields to update.

        Returns:
            The updated canvas.
        """
        update_data = {**kwargs}
        if (
            "video_timeline" in update_data
            and update_data["video_timeline"] is not None
        ):
            update_data["video_timeline"] = update_data["video_timeline"].to_firestore()
        if "html" in update_data and update_data["html"] is not None:
            update_data["html"] = dataclasses.asdict(update_data["html"])

        canvas_ref = self.canvases_collection.document(canvas_id)
        canvas_ref.update(update_data)
        return self.get_canvas(canvas_id)

    def delete_canvas(self, canvas_id: str) -> None:
        """Deletes a canvas from database.

        Args:
            canvas_id: The ID of the canvas to delete.
        """
        self.canvases_collection.document(canvas_id).delete()
