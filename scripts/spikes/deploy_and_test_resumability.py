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

"""I0 spike (remote half): does the gate pause/resume on Agent Engine?

The local spike proved the mechanism against InMemorySessionService. Agent Engine
uses VertexAiSessionService, so this deploys a throwaway engine and runs the same
pause/resume round-trip against the managed runtime.

Deploys under its own display name so the shared dev engine is never touched, and
deletes itself at the end (unless --keep).

Run:  uv run python scripts/spikes/deploy_and_test_resumability.py
"""

from __future__ import annotations

import argparse
import asyncio
import concurrent.futures
import os
import time
import sys
import traceback

import vertexai
from dotenv import load_dotenv
from vertexai import agent_engines
from vertexai.agent_engines import AdkApp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spike_agent import GATE_CALL_ID, GATE_TOOL_NAME, build_app  # noqa: E402

DISPLAY_NAME = "ads-x-hitl-resumability-spike"
USER_ID = "spike-user"

REQUIREMENTS = [
    "google-cloud-aiplatform[agent_engines,adk]==1.159.0",
    "google-adk==1.29.0",
    "pydantic==2.12.3",
    "cloudpickle==3.1.2",
]


def texts_of(event: dict) -> list[str]:
    parts = (event.get("content") or {}).get("parts") or []
    return [p["text"] for p in parts if p.get("text")]


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=None)
    parser.add_argument("--location", default="us-central1")
    parser.add_argument("--bucket", default=None, help="Staging bucket (overrides env)")
    parser.add_argument(
        "--keep", action="store_true", help="Do not delete the engine afterwards"
    )
    args = parser.parse_args()

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    load_dotenv(os.path.join(root, "demos/backend/.env.dev"), override=True)

    project = args.project or os.getenv("GOOGLE_CLOUD_PROJECT")
    bucket = (
        args.bucket
        or os.getenv("ASSET_SERVICE_GCS_BUCKET")
        or f"{project}-agent-engine"
    )
    if not bucket.startswith("gs://"):
        bucket = f"gs://{bucket}"

    print(f"• Project: {project}\n• Location: {args.location}\n• Bucket: {bucket}")
    vertexai.init(project=project, location=args.location, staging_bucket=bucket)

    print(f"\nDeploying throwaway engine '{DISPLAY_NAME}' (a few minutes)...")
    # cloudpickle stores the agent classes BY REFERENCE (module 'spike_agent'), so
    # the module must be importable remotely as a top-level name. extra_packages
    # entries are resolved relative to cwd, so chdir here — passing an absolute
    # path lands it at the wrong place and the engine dies with ModuleNotFoundError.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    remote = None
    ok = False
    try:
        try:
            remote = agent_engines.create(
                agent_engine=AdkApp(app=build_app()),
                requirements=REQUIREMENTS,
                extra_packages=["spike_agent.py"],
                display_name=DISPLAY_NAME,
                description=(
                    "Throwaway spike: validates ADK resumability on Agent Engine."
                ),
            )
        except concurrent.futures.TimeoutError:
            # The client stops polling at 900s, but provisioning often completes
            # shortly after. Recover the engine by name instead of redeploying.
            print("Client poll timed out; waiting for the engine to appear...")
            for attempt in range(20):
                time.sleep(30)
                found = list(
                    agent_engines.list(filter=f'display_name="{DISPLAY_NAME}"')
                )
                if found:
                    remote = found[0]
                    print(f"Recovered after {(attempt + 1) * 30}s.")
                    break
            if remote is None:
                print("Engine never became available.")
                return 1
        print(f"Deployed: {remote.resource_name}")

        session = remote.create_session(user_id=USER_ID)
        session_id = session["id"]
        print(f"Session: {session_id}")

        # ---- Turn 1: expect a PAUSE at the gate ----------------------------
        print("\n[turn 1] starting pipeline...")
        invocation_id, paused_signal, seen = None, False, []
        # NOTE: async_stream_query, NOT the deprecated sync stream_query. The sync
        # path routes to Runner.run(), whose signature has no `invocation_id`, so a
        # paused invocation simply cannot be resumed through it.
        async for event in remote.async_stream_query(
            user_id=USER_ID, session_id=session_id, message="make me an ad"
        ):
            invocation_id = event.get("invocation_id") or invocation_id
            if event.get("long_running_tool_ids"):
                paused_signal = True
                print(f"  gate emitted: {event['long_running_tool_ids']}")
            seen += texts_of(event)

        print(f"  events: {seen}")
        ran_generation = any("stage_c_generation" in t for t in seen)
        print(
            f"  long-running signal reached client? {'YES' if paused_signal else 'NO'}"
        )
        print(
            f"  PAUSED before generation?           {'YES' if not ran_generation else 'NO'}"
        )

        if ran_generation:
            print("\n  !! Did NOT pause on Agent Engine — resumability not in effect.")
            return 1

        # ---- Turn 2: send the gate response, expect RESUME -----------------
        # Deliberately NO invocation_id. It is absent from the deployed operation
        # schema (so sending it makes the request malformed), and it is not
        # needed: Runner._resolve_invocation_id infers the paused invocation by
        # matching the function_response id back to its function_call event.
        print(f"\n[turn 2] resuming (paused invocation was {invocation_id})...")
        resumed = []
        async for event in remote.async_stream_query(
            user_id=USER_ID,
            session_id=session_id,
            message={
                "role": "user",
                "parts": [
                    {
                        "function_response": {
                            "id": GATE_CALL_ID,
                            "name": GATE_TOOL_NAME,
                            "response": {"decision": "accept", "guidance": ""},
                        }
                    }
                ],
            },
        ):
            resumed += texts_of(event)

        print(f"  events: {resumed}")
        advanced = any("stage_c_generation" in t for t in resumed)
        replayed = any("RAN:stage_a_storyboard" in t for t in resumed)
        print(f"  RESUMED into generation?    {'YES' if advanced else 'NO'}")
        print(f"  Re-ran earlier stage (bad)? {'YES' if replayed else 'NO'}")

        ok = advanced and not replayed
        print(
            "\n==> VERDICT: resumability WORKS on Agent Engine."
            if ok
            else "\n==> VERDICT: resume did NOT behave as expected."
        )
    except Exception:  # noqa: BLE001 - spike: surface anything and still clean up
        traceback.print_exc()
    finally:
        if args.keep and remote is not None:
            print(f"\nKeeping engine: {remote.resource_name}")
        else:
            # Sweep by display name: a create() that fails mid-provision leaves no
            # handle, so deleting via `remote` alone can leak the resource.
            print("\nCleaning up throwaway engine(s)...")
            for engine in agent_engines.list(filter=f'display_name="{DISPLAY_NAME}"'):
                try:
                    engine.delete(force=True)
                    print(f"Deleted {engine.resource_name}")
                except Exception as exc:  # noqa: BLE001
                    print(f"!! Delete failed for {engine.resource_name}: {exc}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
