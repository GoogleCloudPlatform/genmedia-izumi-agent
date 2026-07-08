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

"""In-Memory Gradio UI for Ads-X agent chat and state inspection."""

import json
import logging
import os
import sys
import uuid
from typing import Any, Dict, List, Tuple

import gradio as gr
from google.adk import Runner
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

import mediagent_kit
from mediagent_kit import MediagentKitConfig

from dotenv import load_dotenv

# Ensure backend directory is in sys.path when executed directly
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Load .env.dev environment variables
env_dev_path = os.path.join(backend_dir, ".env.dev")
if os.path.exists(env_dev_path):
    load_dotenv(dotenv_path=env_dev_path, override=True)
else:
    load_dotenv(override=True)

# Force Vertex AI ADC mode for Gemini & ADK
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gradio_app")

import google.auth

try:
    _, default_project = google.auth.default()
except Exception:
    default_project = None

project = os.getenv("GOOGLE_CLOUD_PROJECT") or default_project or "nachov-argolis"
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
gcs_bucket = os.getenv("ASSET_SERVICE_GCS_BUCKET", "nachov-izumi-test")
firestore_db = os.getenv("FIRESTORE_DATABASE_ID", "(default)")
use_cs = os.getenv("USE_CREATIVE_STUDIO", "True").lower() in ["true", "1"]
cs_backend_url = os.getenv(
    "CREATIVE_STUDIO_BACKEND_URL", "https://cstudio-be-464814743320.us-central1.run.app"
)
token_key = os.getenv("CREATIVE_STUDIO_USER_AUTH_TOKEN_KEY", "user_auth_token")

os.environ["GOOGLE_CLOUD_PROJECT"] = project
os.environ["GOOGLE_CLOUD_LOCATION"] = location

kit_config = MediagentKitConfig(
    google_cloud_project=project,
    google_cloud_location=location,
    asset_service_gcs_bucket=gcs_bucket,
    firestore_database_id=firestore_db,
    use_creative_studio=use_cs,
    cs_backend_url=cs_backend_url if use_cs else None,
    cs_user_auth_token_key=token_key,
)
mediagent_kit.initialize(kit_config)

from ads_x.agent import root_agent

# Instantiate ADK In-Memory Services
session_service = InMemorySessionService()
artifact_service = InMemoryArtifactService()

# Runner instance
runner = Runner(
    agent=root_agent,
    session_service=session_service,
    artifact_service=artifact_service,
    app_name="ads_x_app",
)

USER_ID = "gradio_user"
APP_NAME = "ads_x_app"


async def get_or_create_session(
    session_id: str, workspace_id: str, auth_token: str, custom_state_str: str
):
    """Retrieves existing session or creates a new one with injected state."""
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    if not session:
        initial_state: Dict[str, Any] = {
            "workspace_id": workspace_id.strip() or "1",
            os.getenv(
                "CREATIVE_STUDIO_USER_AUTH_TOKEN_KEY", "user_auth_token"
            ): auth_token.strip(),
            "parameters": {},
            "user_assets": {},
            "storyboard": {},
            "forced_metadata": {},
        }
        if custom_state_str.strip():
            try:
                parsed_custom = json.loads(custom_state_str)
                if isinstance(parsed_custom, dict):
                    initial_state.update(parsed_custom)
            except Exception as e:
                logger.error(f"Failed to parse custom JSON state: {e}")

        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session_id,
            state=initial_state,
        )
    return session


async def reset_session_action(
    workspace_id: str, auth_token: str, custom_state_str: str
) -> Tuple[str, List[Dict[str, str]], str]:
    """Resets the current session with fresh injected state."""
    new_session_id = f"session_{uuid.uuid4().hex[:8]}"
    initial_state: Dict[str, Any] = {
        "workspace_id": workspace_id.strip() or "1",
        os.getenv(
            "CREATIVE_STUDIO_USER_AUTH_TOKEN_KEY", "user_auth_token"
        ): auth_token.strip(),
        "parameters": {},
        "user_assets": {},
        "storyboard": {},
        "forced_metadata": {},
    }
    if custom_state_str.strip():
        try:
            parsed_custom = json.loads(custom_state_str)
            if isinstance(parsed_custom, dict):
                initial_state.update(parsed_custom)
        except Exception as e:
            logger.error(f"Failed to parse custom JSON state: {e}")

    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=new_session_id,
        state=initial_state,
    )
    return (
        new_session_id,
        [],
        json.dumps(initial_state, indent=2, default=str),
    )


async def user_chat_action(
    user_message: str,
    history: List[Dict[str, str]],
    session_id: str,
    workspace_id: str,
    auth_token: str,
    custom_state_str: str,
):
    """Handles chat interaction with the Ads-X agent runner."""
    if not user_message.strip():
        yield history, "", ""
        return

    if not session_id:
        session_id = f"session_{uuid.uuid4().hex[:8]}"

    session = await get_or_create_session(
        session_id, workspace_id, auth_token, custom_state_str
    )

    # Sync state with latest UI inputs
    token_key = os.getenv("CREATIVE_STUDIO_USER_AUTH_TOKEN_KEY", "user_auth_token")
    clean_token = auth_token.strip()
    clean_ws = workspace_id.strip() or "1"

    if clean_token:
        session.state[token_key] = clean_token
        session.state["user_auth_token"] = clean_token
    if clean_ws:
        session.state["workspace_id"] = clean_ws

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": "Thinking..."})
    yield history, "", json.dumps(session.state, indent=2, default=str)

    from mediagent_kit.utils.context import set_request_context

    # Populate request context for background tools/services
    set_request_context(
        user_auth_token=clean_token,
        workspace_id=clean_ws,
        transient_cache=session.state,
    )
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message)],
    )

    assistant_response = ""
    try:
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=session_id,
            new_message=content,
        ):
            if hasattr(event, "content") and event.content:
                if hasattr(event.content, "parts"):
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            assistant_response += part.text
            elif hasattr(event, "text") and event.text:
                assistant_response += event.text

            if assistant_response:
                history[-1]["content"] = assistant_response
                yield history, "", json.dumps(session.state, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error during agent execution: {e}", exc_info=True)
        assistant_response = f"⚠️ Error executing agent: {e}"
        history[-1]["content"] = assistant_response

    yield history, "", json.dumps(session.state, indent=2, default=str)


async def refresh_state_action(session_id: str) -> str:
    """Refreshes the JSON display of the current session state."""
    if not session_id:
        return json.dumps({"status": "No active session"}, indent=2)

    session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    if not session:
        return json.dumps({"status": "Session not found"}, indent=2)

    return json.dumps(session.state, indent=2, default=str)


# Build Gradio UI Interface
with gr.Blocks(title="Ads-X Agent Interactive Workbench") as demo:
    gr.Markdown("# 🚀 Ads-X AI Creative Director Workbench")
    gr.Markdown(
        "Interact with the in-memory **Ads-X Agent**, inject initial state, and observe real-time state mutations."
    )

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### ⚙️ Session State Configuration")
            workspace_id_input = gr.Textbox(
                label="Workspace ID",
                value=os.getenv("WORKSPACE_ID", "1"),
                placeholder="1",
            )
            auth_token_input = gr.Textbox(
                label="Auth Token",
                value=os.getenv("CREATIVE_STUDIO_USER_AUTH_TOKEN", "demo_auth_token"),
                type="password",
            )
            custom_state_input = gr.Code(
                label="Pre-injected Custom State (JSON)",
                language="json",
                value='{\n  "forced_metadata": {}\n}',
                lines=5,
            )
            reset_btn = gr.Button("🔄 Initialize / Reset Session", variant="secondary")
            session_id_display = gr.Textbox(
                label="Active Session ID", interactive=False
            )

        with gr.Column(scale=2):
            with gr.Tabs():
                with gr.TabItem("💬 Agent Chat"):
                    chatbot = gr.Chatbot(
                        label="Ads-X Conversation",
                        height=500,
                    )
                    msg_input = gr.Textbox(
                        label="User Prompt / Brief",
                        placeholder="e.g. Create a 15s cinematic ad for blue suede sneakers targeting marathon runners...",
                        lines=2,
                    )
                    send_btn = gr.Button("Send Message 📤", variant="primary")

                with gr.TabItem("🔍 Agent Inner State Inspector"):
                    gr.Markdown("### Live Session State (`session.state`)")
                    refresh_state_btn = gr.Button("🔄 Refresh State View")
                    state_json_view = gr.Code(
                        label="session.state",
                        language="json",
                        lines=25,
                        interactive=False,
                    )

    # Wire event handlers
    reset_btn.click(
        fn=reset_session_action,
        inputs=[workspace_id_input, auth_token_input, custom_state_input],
        outputs=[session_id_display, chatbot, state_json_view],
    )

    send_btn.click(
        fn=user_chat_action,
        inputs=[
            msg_input,
            chatbot,
            session_id_display,
            workspace_id_input,
            auth_token_input,
            custom_state_input,
        ],
        outputs=[chatbot, msg_input, state_json_view],
    )

    msg_input.submit(
        fn=user_chat_action,
        inputs=[
            msg_input,
            chatbot,
            session_id_display,
            workspace_id_input,
            auth_token_input,
            custom_state_input,
        ],
        outputs=[chatbot, msg_input, state_json_view],
    )

    refresh_state_btn.click(
        fn=refresh_state_action,
        inputs=[session_id_display],
        outputs=[state_json_view],
    )


if __name__ == "__main__":
    demo.queue()
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
