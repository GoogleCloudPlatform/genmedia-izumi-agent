import uuid
from typing import Any

from firebase_admin import firestore

from mediagent_kit.config import MediagentKitConfig
from mediagent_kit.services import types
from mediagent_kit.services.asset_service import AssetService
from mediagent_kit.services.canvas_service import CanvasService

class CreativeStudioCanvasService(CanvasService):
    """Service for managing canvases in transient cache, bypassing Firestore for Creative Studio."""

    def __init__(
        self,
        db: firestore.Client,
        asset_service: AssetService,
        config: MediagentKitConfig,
        workspace_id: str | int | None = None,
        user_auth_token: str | None = None,
        transient_cache: dict[str, Any] | None = None,
    ):
        """Initializes the CreativeStudioCanvasService."""
        super().__init__(db, asset_service, config)
        self.__workspace_id = workspace_id
        self.__user_auth_token = user_auth_token
        self.__transient_cache = transient_cache

    @property
    def _workspace_id(self) -> Any:
        if self.__workspace_id is not None:
            return self.__workspace_id
        from mediagent_kit.utils.context import get_request_context
        ctx = get_request_context()
        return ctx.get("workspace_id") if ctx else None

    @property
    def _user_auth_token(self) -> str | None:
        if self.__user_auth_token is not None:
            return self.__user_auth_token
        from mediagent_kit.utils.context import get_request_context
        ctx = get_request_context()
        return ctx.get("user_auth_token") if ctx else None

    @property
    def _transient_cache(self) -> dict[str, Any]:
        if self.__transient_cache is not None:
            return self.__transient_cache
        from mediagent_kit.utils.context import get_request_context
        ctx = get_request_context()
        return ctx.get("transient_cache") if (ctx and ctx.get("transient_cache") is not None) else {}

    def create_canvas(
        self,
        user_id: str,
        title: str,
        video_timeline: types.VideoTimeline | None = None,
        html: types.Html | None = None,
    ) -> types.Canvas:
        """Creates a new canvas in the transient cache."""
        canvas_id = str(uuid.uuid4())
        canvas = types.Canvas(
            id=canvas_id,
            user_id=user_id,
            title=title,
            video_timeline=video_timeline,
            html=html,
        )
        if hasattr(canvas, "to_dict"):
            self._transient_cache[f"canvas_{canvas_id}"] = canvas.to_dict()
        else:
            self._transient_cache[f"canvas_{canvas_id}"] = canvas
        return canvas

    def get_canvas(self, canvas_id: str) -> types.Canvas | None:
        """Gets a canvas from the transient cache, falling back to db."""
        key = f"canvas_{canvas_id}"
        if key in self._transient_cache:
            cached = self._transient_cache[key]
            if isinstance(cached, dict):
                return types.Canvas.from_dict(cached, self._asset_service)
            return cached
        return super().get_canvas(canvas_id)

    def list_canvases(self, user_id: str) -> list[types.Canvas]:
        """Lists canvases, including transient ones."""
        canvases = []
        for key, value in self._transient_cache.items():
            if key.startswith("canvas_"):
                canvas = value
                if isinstance(canvas, dict):
                    canvas = types.Canvas.from_dict(canvas, self._asset_service)
                if canvas.user_id == user_id:
                    canvases.append(canvas)
        
        # Also get from db
        db_canvases = super().list_canvases(user_id)
        
        # Combine and deduplicate
        seen = {c.id for c in canvases}
        for c in db_canvases:
            if c.id not in seen:
                canvases.append(c)
                
        return canvases

    def update_canvas(self, canvas_id: str, **kwargs: Any) -> types.Canvas | None:
        """Updates a canvas in the transient cache, or db if missing."""
        key = f"canvas_{canvas_id}"
        if key in self._transient_cache:
            canvas = self._transient_cache[key]
            if isinstance(canvas, dict):
                canvas = types.Canvas.from_dict(canvas, self._asset_service)
            for k, v in kwargs.items():
                if hasattr(canvas, k):
                    setattr(canvas, k, v)
            if hasattr(canvas, "to_dict"):
                self._transient_cache[key] = canvas.to_dict()
            else:
                self._transient_cache[key] = canvas
            return canvas
            
        return super().update_canvas(canvas_id, **kwargs)

    def delete_canvas(self, canvas_id: str) -> None:
        """Deletes a canvas from cache and db."""
        key = f"canvas_{canvas_id}"
        if key in self._transient_cache:
            del self._transient_cache[key]
        
        try:
            super().delete_canvas(canvas_id)
        except Exception:
            pass
