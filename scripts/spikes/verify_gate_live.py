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

"""Drives the real ads_x pipeline until the storyboard review gate fires.

Unit tests cover the gate's tools and the pipeline shape, and a separate spike
proved the ADK pause/resume machinery on Agent Engine. What neither covers is
the real pipeline actually reaching the gate and suspending there. This closes
that gap and prints the exact payload a frontend receives, so the Creative
Studio approval ribbon can be built against something real rather than a guess.

Cheap by construction: the gate fires *before* the generation stage, so a run
costs a handful of text calls and renders no media. The run is abandoned at the
gate unless --approve is passed.

Run:
  uv run python scripts/spikes/verify_gate_live.py --project=project-izumi-dev
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

BRIEF = (
    "Create a 15 second ad for Aurora, a premium stainless steel water bottle "
    "that keeps drinks cold for 24 hours. Audience is urban professionals. "
    "Tone: refined and calm. No on-screen people, product only."
)


def _configure_environment(project: str, location: str) -> None:
    """Environment must be set before ads_x.agent is imported.

    config.settings is built at import time, so ENABLE_HITL_GATES has to be in
    place first or the pipeline is assembled without the gate.
    """
    os.environ["ENABLE_HITL_GATES"] = "True"
    os.environ["GOOGLE_CLOUD_PROJECT"] = project
    os.environ["GOOGLE_CLOUD_LOCATION"] = location
    os.environ["MODEL_TARGET_LOCATION"] = location
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
    # Exercise the gate on its own: Creative Studio storage is a separate
    # integration and is not what this run is checking.
    os.environ["USE_CREATIVE_STUDIO"] = "False"


def _summarise(event) -> None:
    author = getattr(event, "author", "?")
    for part in (event.content.parts if event.content else None) or []:
        if getattr(part, "function_call", None):
            print(f"    [{author}] -> call {part.function_call.name}")
        elif getattr(part, "text", None):
            text = " ".join(part.text.split())
            if text:
                print(f"    [{author}] {text[:150]}")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default="project-izumi-dev")
    parser.add_argument("--location", default="global")
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Answer the gate and let generation start (renders media, slow)",
    )
    args = parser.parse_args()

    _configure_environment(args.project, args.location)

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    sys.path.insert(0, os.path.join(root, "demos/backend"))

    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types

    from ads_x.agent import app, full_pipeline_agent
    from ads_x.tools.storyboard import gate_tools

    print(f"• Project : {args.project}")
    print(f"• Stages  : {[a.name for a in full_pipeline_agent.sub_agents]}")
    print(f"• Resumable: {app.resumability_config.is_resumable}")
    stage_names = [a.name for a in full_pipeline_agent.sub_agents]
    if not any("gate" in n or "review" in n for n in stage_names):
        print("!! Gate absent - ENABLE_HITL_GATES did not take effect.")
        return 1

    runner = Runner(app=app, session_service=InMemorySessionService())
    session = await runner.session_service.create_session(
        app_name="ads_x", user_id="gate-verifier"
    )

    gate_payload, long_running_ids = None, set()

    async def turn(label: str, text: str) -> None:
        nonlocal gate_payload
        print(f"\n[{label}] {text[:70]}...\n")
        async for event in runner.run_async(
            user_id="gate-verifier",
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text=text)]),
        ):
            _summarise(event)
            if getattr(event, "long_running_tool_ids", None):
                long_running_ids.update(event.long_running_tool_ids)
            for part in (event.content.parts if event.content else None) or []:
                response = getattr(part, "function_response", None)
                if response and response.name == "await_storyboard_approval":
                    gate_payload = response.response

    # The root agent presents a "creative blueprint" and waits for explicit
    # confirmation before handing off to full_pipeline_agent (root_instruction
    # Step 1C/1D), so driving it takes two turns.
    await turn("turn 1: brief", BRIEF)
    if not long_running_ids:
        await turn(
            "turn 2: confirm",
            "Yes, the blueprint looks right. Please proceed and build the "
            "storyboard.",
        )

    session = await runner.session_service.get_session(
        app_name="ads_x", user_id="gate-verifier", session_id=session.id
    )
    state = session.state if session else {}
    storyboard = state.get("storyboard") or {}

    print("\n" + "=" * 70)
    print(
        f"storyboard built     : {bool(storyboard.get('scenes'))} "
        f"({len(storyboard.get('scenes') or [])} scenes)"
    )
    print(
        f"gate suspended run   : {bool(long_running_ids)}  {sorted(long_running_ids)}"
    )
    print(
        f"scene ids assigned   : "
        f"{[s.get('scene_id') for s in storyboard.get('scenes') or []]}"
    )
    print(f"stage cursor         : {state.get('stage_completed')}")
    print(f"approved             : {gate_tools.storyboard_is_approved(state)}")

    if gate_payload:
        print("\n--- payload delivered to the frontend ---")
        print(json.dumps(gate_payload, indent=2, default=str)[:2000])

    rendered = any(
        (s.get("video_prompt") or {}).get("asset_id")
        for s in storyboard.get("scenes") or []
    )
    print(f"\nmedia rendered before approval: {rendered}  <- must be False")
    print("=" * 70)

    ok = bool(long_running_ids) and not rendered
    print("\n==> GATE VERIFIED" if ok else "\n==> GATE DID NOT BEHAVE AS EXPECTED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
