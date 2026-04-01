# Copyright 2024 Google LLC
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
"""A session service that uses Google Cloud Firestore for persistence."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from firebase_admin import firestore
from firebase_admin.firestore import FieldFilter
from google.adk.events.event import Event
from google.adk.sessions.base_session_service import (
    BaseSessionService,
    GetSessionConfig,
    ListSessionsResponse,
)
from google.adk.sessions.session import Session
from google.genai import types as genai_types

from mediagent_kit.config import MediagentKitConfig

if TYPE_CHECKING:
    from mediagent_kit.services.aio.async_services import AsyncAssetService


def _event_to_dict(event: Event) -> dict[str, Any]:
    """Converts an Event object to a dictionary."""
    data = event.model_dump(exclude_none=True)
    data["timestamp"] = datetime.fromtimestamp(event.timestamp, tz=UTC)
    return data


def _event_from_dict(data: dict[str, Any]) -> Event:
    """Converts a dictionary to an Event object."""
    if "timestamp" in data and isinstance(data["timestamp"], datetime):
        data["timestamp"] = data["timestamp"].timestamp()
    return Event.model_validate(data)


def _extract_state_delta(
    state: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    """Extracts app, user, and session state deltas from a state dictionary."""
    deltas: dict[str, dict[str, Any]] = {"app": {}, "user": {}, "session": {}}
    if state:
        for key, value in state.items():
            if key.startswith("app."):
                deltas["app"][key.removeprefix("app.")] = value
            elif key.startswith("user."):
                deltas["user"][key.removeprefix("user.")] = value
            elif not key.startswith("temp."):
                deltas["session"][key] = value
    return deltas


class FirestoreSessionService(BaseSessionService):
    """A session service that uses Google Cloud Firestore for persistence."""

    def __init__(
        self,
        db: firestore.Client,
        asset_service: AsyncAssetService,
        config: MediagentKitConfig,
    ):
        """Initializes the Firestore client."""
        self._client = db
        self._asset_service = asset_service
        self._config = config
        self._sessions_collection = "adk_sessions"
        self._app_state_collection = "adk_app_state"
        self._user_state_collection = "adk_user_state"

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> Session:
        """Create a new document in the `adk_sessions` collection."""
        state_deltas = _extract_state_delta(state)
        app_state_delta = state_deltas["app"]
        user_state_delta = state_deltas["user"]
        session_state = state_deltas["session"]

        if session_id is None:
            session_id = str(uuid.uuid4())

        doc_id = f"{app_name}_{user_id}_{session_id}"
        session_ref = self._client.collection(self._sessions_collection).document(
            doc_id
        )

        # Check if session already exists
        session_doc = await asyncio.to_thread(session_ref.get)
        if session_doc.exists:
            logging.warning(
                f"Session with id '{session_id}' for user '{user_id}' already exists. Overwriting."
            )
            # If session already exists, delete its events subcollection
            events_ref = session_ref.collection("events")
            docs = await asyncio.to_thread(events_ref.stream)
            for doc in docs:
                await asyncio.to_thread(doc.reference.delete)

        session_data = {
            "app_name": app_name,
            "user_id": user_id,
            "session_id": session_id,
            "state": session_state,
            "create_time": firestore.SERVER_TIMESTAMP,
            "last_update_time": firestore.SERVER_TIMESTAMP,
        }
        await asyncio.to_thread(session_ref.set, session_data)

        if app_state_delta:
            app_state_ref = self._client.collection(
                self._app_state_collection
            ).document(app_name)
            await asyncio.to_thread(
                app_state_ref.set, {"state": app_state_delta}, merge=True
            )

        if user_state_delta:
            user_state_id = f"{app_name}_{user_id}"
            user_state_ref = self._client.collection(
                self._user_state_collection
            ).document(user_state_id)
            await asyncio.to_thread(
                user_state_ref.set, {"state": user_state_delta}, merge=True
            )

        # Fetch the created session to get the server timestamp
        created_session_doc = await asyncio.to_thread(session_ref.get)
        created_session_data = created_session_doc.to_dict()
        last_update_time = created_session_data["last_update_time"].timestamp()

        # Fetch the full state to return
        app_state_doc = await asyncio.to_thread(
            self._client.collection(self._app_state_collection).document(app_name).get
        )
        user_state_doc = await asyncio.to_thread(
            self._client.collection(self._user_state_collection)
            .document(f"{app_name}_{user_id}")
            .get
        )
        app_state = (
            app_state_doc.to_dict().get("state", {}) if app_state_doc.exists else {}
        )
        user_state = (
            user_state_doc.to_dict().get("state", {}) if user_state_doc.exists else {}
        )

        merged_state = {}
        merged_state.update(session_state)
        merged_state.update({f"app.{k}": v for k, v in app_state.items()})
        merged_state.update({f"user.{k}": v for k, v in user_state.items()})

        return Session(
            id=session_id,
            app_name=app_name,
            user_id=user_id,
            state=merged_state,
            events=[],
            last_update_time=last_update_time,
        )

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: GetSessionConfig | None = None,
    ) -> Session | None:
        """Fetch the session document and its related data."""
        doc_id = f"{app_name}_{user_id}_{session_id}"
        session_ref = self._client.collection(self._sessions_collection).document(
            doc_id
        )
        session_doc = await asyncio.to_thread(session_ref.get)

        if not session_doc.exists:
            return None

        session_data = session_doc.to_dict()

        # Fetch app and user state
        app_state_doc = await asyncio.to_thread(
            self._client.collection(self._app_state_collection).document(app_name).get
        )
        user_state_id = f"{app_name}_{user_id}"
        user_state_doc = await asyncio.to_thread(
            self._client.collection(self._user_state_collection)
            .document(user_state_id)
            .get
        )

        app_state = (
            app_state_doc.to_dict().get("state", {}) if app_state_doc.exists else {}
        )
        user_state = (
            user_state_doc.to_dict().get("state", {}) if user_state_doc.exists else {}
        )

        session_state = session_data.get("state", {})
        session_state.update({f"app.{k}": v for k, v in app_state.items()})
        session_state.update({f"user.{k}": v for k, v in user_state.items()})

        events = []
        events_ref = session_ref.collection("events").order_by(
            "timestamp", direction=firestore.Query.DESCENDING
        )

        if config and config.after_timestamp:
            events_ref = events_ref.where(
                filter=FieldFilter(
                    "timestamp",
                    ">=",
                    datetime.fromtimestamp(config.after_timestamp, tz=UTC),
                )
            )

        if config and config.num_recent_events:
            events_ref = events_ref.limit(config.num_recent_events)

        event_docs = await asyncio.to_thread(events_ref.stream)
        for event_doc in event_docs:
            events.append(_event_from_dict(event_doc.to_dict()))

        events.reverse()

        # Process events to load assets
        processed_events = []
        for event in events:
            if event.content and event.content.parts:
                modified_parts = []
                for part in event.content.parts:
                    if part.text and part.text.startswith("<asset://"):
                        asset_url = part.text
                        file_name = None  # Define file_name here to have it in scope for the except block
                        try:
                            # Extract filename from <asset://filename.ext>
                            file_name = asset_url.strip("<>").removeprefix("asset://")
                            user_id = session_data["user_id"]

                            # Step 1: Get asset metadata by file name
                            asset = await self._asset_service.get_asset_by_file_name(
                                user_id=user_id, file_name=file_name
                            )
                            if asset:
                                # Step 2: Get the asset blob using the asset ID
                                asset_blob = await self._asset_service.get_asset_blob(
                                    asset_id=asset.id
                                )
                                modified_parts.append(
                                    genai_types.Part(
                                        inline_data=genai_types.Blob(
                                            data=asset_blob.content,
                                            mime_type=asset_blob.mime_type,
                                        )
                                    )
                                )
                            else:
                                raise FileNotFoundError(
                                    f"Asset with file_name '{file_name}' not found."
                                )

                        except Exception as e:
                            logging.error(
                                f"FirestoreSessionService: Failed to load asset {file_name or asset_url}: {e}"
                            )
                            modified_parts.append(
                                genai_types.Part(
                                    text=f"System note: Failed to load asset '{file_name or asset_url}'. Error: {e}"
                                )
                            )
                    else:
                        modified_parts.append(part)

                # Create a new Event with modified content
                event.content = genai_types.Content(
                    parts=modified_parts, role=event.content.role
                )
            processed_events.append(event)

        return Session(
            id=session_id,
            app_name=app_name,
            user_id=user_id,
            state=session_state,
            events=processed_events,  # Use processed_events
            last_update_time=session_data["last_update_time"].timestamp(),
        )

    async def list_sessions(
        self, app_name: str | None = None, user_id: str | None = None
    ) -> ListSessionsResponse:
        """Query the `adk_sessions` collection."""
        query = self._client.collection(self._sessions_collection)

        if app_name:
            query = query.where(filter=FieldFilter("app_name", "==", app_name))

        if user_id:
            query = query.where(filter=FieldFilter("user_id", "==", user_id))

        query = query.order_by("last_update_time", direction=firestore.Query.DESCENDING)

        sessions = []
        docs = await asyncio.to_thread(query.stream)
        for doc in docs:
            session_data = doc.to_dict()
            last_update_time_dt = session_data.get("last_update_time")
            last_update_time_ts = (
                last_update_time_dt.timestamp() if last_update_time_dt else 0.0
            )
            sessions.append(
                Session(
                    id=session_data["session_id"],
                    app_name=session_data["app_name"],
                    user_id=session_data["user_id"],
                    state=session_data.get("state", {}),
                    last_update_time=last_update_time_ts,
                )
            )

        return ListSessionsResponse(sessions=sessions)

    async def delete_session(
        self, *, app_name: str, user_id: str, session_id: str
    ) -> None:
        """Delete the session document and its `events` sub-collection."""
        doc_id = f"{app_name}_{user_id}_{session_id}"
        session_ref = self._client.collection(self._sessions_collection).document(
            doc_id
        )
        await self._recursive_delete(session_ref)

    async def append_event(self, session: Session, event: Event) -> Event:
        """Add a new document to the `events` sub-collection and update session state."""
        if event.partial:
            return event

        # Intercept and handle blobs before saving the event
        if event.content and event.content.parts and event.author == "user":
            new_parts = []
            modified = False
            for part in event.content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    modified = True
                    blob = part.inline_data
                    mime_type = blob.mime_type
                    blob_data = blob.data
                    # display_name is not a standard attribute of Blob, so we handle its absence
                    file_name = getattr(blob, "display_name", None)

                    if not file_name:
                        file_extension = (
                            mime_type.split("/")[-1] if mime_type else "bin"
                        )
                        file_name = f"{uuid.uuid4()}.{file_extension}"

                    logging.info(
                        f"FirestoreSessionService: Intercepted blob of type {mime_type}. "
                        f"Saving as asset with name {file_name}"
                    )

                    try:
                        user_id = session.user_id
                        await self._asset_service.save_asset(
                            user_id=user_id,
                            mime_type=mime_type,
                            file_name=file_name,
                            blob=blob_data,
                        )
                        logging.info(
                            "FirestoreSessionService: Successfully saved blob as asset: %s",
                            file_name,
                        )

                        asset_reference_text = f"<asset://{file_name}>"
                        new_parts.append(genai_types.Part(text=asset_reference_text))

                    except Exception as e:
                        logging.error(
                            "FirestoreSessionService: Failed to save blob as asset: %s",
                            e,
                        )
                        error_message = f"System note: The user attempted to upload a file, but it failed to save. Error: {e}"
                        new_parts.append(genai_types.Part(text=error_message))
                else:
                    new_parts.append(part)

            if modified:
                event.content = genai_types.Content(
                    parts=new_parts, role=event.content.role
                )

        doc_id = f"{session.app_name}_{session.user_id}_{session.id}"
        session_ref = self._client.collection(self._sessions_collection).document(
            doc_id
        )
        event_ref = session_ref.collection("events").document()

        transaction = self._client.transaction()

        @firestore.transactional
        def update_in_transaction(transaction: firestore.Transaction) -> None:
            session_doc = next(transaction.get(session_ref), None)
            if not session_doc or not session_doc.exists:
                raise ValueError(f"Session with id {session.id} does not exist.")

            session_data = session_doc.to_dict()
            last_update_time = session_data.get("last_update_time")
            if (
                last_update_time
                and last_update_time.timestamp() > session.last_update_time
            ):
                raise ValueError(
                    "The last_update_time provided in the session object is stale."
                )

            state_deltas = _extract_state_delta(event.actions.state_delta)
            app_state_delta = state_deltas["app"]
            user_state_delta = state_deltas["user"]
            session_state_delta = state_deltas["session"]

            update_data = {"last_update_time": firestore.SERVER_TIMESTAMP}

            if session_state_delta:
                for key, value in session_state_delta.items():
                    update_data[f"state.{key}"] = value

            transaction.update(session_ref, update_data)

            if app_state_delta:
                app_state_ref = self._client.collection(
                    self._app_state_collection
                ).document(session.app_name)
                transaction.set(app_state_ref, {"state": app_state_delta}, merge=True)

            if user_state_delta:
                user_state_id = f"{session.app_name}_{session.user_id}"
                user_state_ref = self._client.collection(
                    self._user_state_collection
                ).document(user_state_id)
                transaction.set(user_state_ref, {"state": user_state_delta}, merge=True)

            persisted_event = Event.model_validate(event.model_dump(exclude_none=True))
            if persisted_event.actions and persisted_event.actions.state_delta:
                persisted_event.actions.state_delta = {
                    k: v
                    for k, v in persisted_event.actions.state_delta.items()
                    if not k.startswith("temp.")
                }

            transaction.set(event_ref, _event_to_dict(persisted_event))

        await asyncio.to_thread(update_in_transaction, transaction)

        # Update the session's last_update_time
        updated_session_doc = await asyncio.to_thread(session_ref.get)
        if updated_session_doc.exists:
            session.last_update_time = updated_session_doc.to_dict()[
                "last_update_time"
            ].timestamp()

        await super().append_event(session=session, event=event)
        return event

    async def _recursive_delete(self, doc_ref: firestore.DocumentReference) -> None:
        """Helper to recursively delete a document and its subcollections."""
        collections = await asyncio.to_thread(doc_ref.collections)
        for collection in collections:
            docs = await asyncio.to_thread(collection.stream)
            for doc in docs:
                await self._recursive_delete(doc.reference)

        await asyncio.to_thread(doc_ref.delete)
