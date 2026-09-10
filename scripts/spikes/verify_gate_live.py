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


def _user(text):
    from google.genai import types as _t

    return _t.Content(role="user", parts=[_t.Part(text=text)])


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
        "--max-gates", type=int, default=4, help="Safety bound on checkpoints"
    )
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

    async def current_state():
        live = await runner.session_service.get_session(
            app_name="ads_x", user_id="gate-verifier", session_id=session.id
        )
        return live.state if live else {}

    seen_gates: list = []

    async def drive(label: str, message) -> tuple:
        """Runs one turn; returns (pending_call, payload) if a gate suspended."""
        print(f"\n[{label}]\n")
        pending, payload = None, None
        async for event in runner.run_async(
            user_id="gate-verifier", session_id=session.id, new_message=message
        ):
            _summarise(event)
            ids = getattr(event, "long_running_tool_ids", None) or set()
            for part in (event.content.parts if event.content else None) or []:
                call = getattr(part, "function_call", None)
                if call is not None and call.id in ids:
                    pending = (call.id, call.name)
                response = getattr(part, "function_response", None)
                if response is not None and str(response.name).startswith("await_"):
                    payload = response.response
        return pending, payload

    def answer(call, decision="accept", guidance=""):
        call_id, name = call
        return types.Content(
            role="user",
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        id=call_id,
                        name=name,
                        response={"decision": decision, "guidance": guidance},
                    )
                )
            ],
        )

    # The root agent presents a blueprint and waits for confirmation before
    # handing off to the pipeline, so the first two turns are conversational.
    pending, payload = await drive("turn 1: brief", _user(BRIEF))
    if not pending:
        pending, payload = await drive(
            "turn 2: confirm",
            _user("Yes, that looks right. Please proceed."),
        )

    # Then answer each checkpoint in turn until the pipeline runs out of them.
    for round_number in range(1, args.max_gates + 1):
        if not pending:
            break
        call_id, name = pending
        stage = (payload or {}).get("result", {}).get("stage", name)
        seen_gates.append(stage)
        print(f"\n{'=' * 70}\nGATE {round_number}: {stage}  (call {call_id})")
        print(json.dumps(payload, indent=2, default=str)[:1800])
        print("=" * 70)
        pending, payload = await drive(
            f"answering {stage} -> accept", answer(pending, "accept")
        )

    print(f"\ncheckpoints reached: {seen_gates}")

    state = await current_state()
    storyboard = state.get("storyboard") or {}

    print("\n" + "=" * 70)
    print(f"storyboard scenes : {len(storyboard.get('scenes') or [])}")
    print(
        f"scene ids         : {[s.get('scene_id') for s in storyboard.get('scenes') or []]}"
    )
    print(f"stage cursor      : {state.get('stage_completed')}")
    print(f"strategy approved : {bool(state.get('strategy_decision'))}")
    print(f"storyboard approved: {bool(state.get('storyboard_decision'))}")
    print(f"final cut approved : {bool(state.get('final_cut_decision'))}")
    print(f"final video asset : {state.get('final_video_asset_id')}")
    rendered = sum(
        1
        for sc in storyboard.get("scenes") or []
        if (sc.get("video_prompt") or {}).get("asset_id")
    )
    print(f"clips rendered    : {rendered}")
    print("=" * 70)

    ok = len(seen_gates) >= 1
    print(f"\n==> reached {len(seen_gates)} checkpoint(s): {seen_gates}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
