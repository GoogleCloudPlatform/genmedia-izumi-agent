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

import os

from fastapi import FastAPI
from starlette.routing import Route

from mediagent_kit.api.assets import router as assets_router
from mediagent_kit.api.canvases import router as canvases_router
from mediagent_kit.api.jobs import router as jobs_router
from mediagent_kit.api.media_generation import router as media_generation_router
from mediagent_kit.api.sessions import router as sessions_router
from mediagent_kit.api.video_stitching import router as video_stitching_router
from mediagent_kit.frontend.spa_static_files import SPAStaticFiles


def mount_to_fastapi_app(app: FastAPI) -> None:
    """
    Initialize the mediagent-kit API endpoints and static files.
    This function adds the mediagent-kit endpoints to the provided FastAPI app.

    Args:
        app: The FastAPI application to mount to.
    """
    # We use the agent app as the main FastAPI application.
    # This allows for a unified OpenAPI schema (documentation) under /docs,
    # which includes both the agent's and other custom endpoints.
    # The trade-off is that the agent's endpoints are at the root of the URL structure,
    # and not under a specific subpath like /agents.

    # Remove the default root route from ADK that redirects to /dev-ui/
    for route in app.router.routes:
        if isinstance(route, Route) and route.path == "/":
            app.router.routes.remove(route)
            break

    # Include the Mediagent Kit REST APIs.
    # These will be available alongside the ADK agent's endpoints.
    app.include_router(assets_router)
    app.include_router(canvases_router)
    app.include_router(media_generation_router)
    app.include_router(jobs_router)
    app.include_router(video_stitching_router)
    app.include_router(sessions_router)

    current_dir = os.path.dirname(__file__)
    adk_web_dir = os.path.join(current_dir, "frontend/public/adk-web")
    debug_ui_dir = os.path.join(current_dir, "frontend/public/debug-ui")

    app.mount(
        "/adk-web",
        SPAStaticFiles(directory=adk_web_dir, html=True),
        name="adk-web",
    )

    # Add the debug UI for the Mediagent Kit REST API
    app.mount(
        "/debug-ui",
        SPAStaticFiles(directory=debug_ui_dir, html=True),
        name="debug-ui",
    )
