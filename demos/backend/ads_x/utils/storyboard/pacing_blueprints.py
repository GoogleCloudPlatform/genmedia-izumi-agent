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

"""Defined rhythmic pacing patterns for creative AI Director sessions."""

from typing import List, Dict

# Standard Pacing Presets (durations in seconds)
# These ensure a modern, punchy feel for social ads.
#
# Every scene length is a whole number of seconds between 3 and 5, which is
# what the video model renders natively. A scene is therefore generated at
# exactly its planned length and reaches the cut without trimming; a fractional
# length would be rendered at the nearest whole second and cut back. The
# upper bound is five seconds: a single generated clip degrades as it runs
# longer, so a beat that needs more screen time is split across two scenes.

PACING_PRESETS: Dict[str, Dict[int, List[List[float]]]] = {
    "12s": {
        4: [
            [3.0, 3.0, 3.0, 3.0],  # Balanced Pacing
        ]
    },
    "15s": {
        4: [
            [4.0, 4.0, 4.0, 3.0],
            [3.0, 4.0, 4.0, 4.0],
        ],
        5: [
            [3.0, 3.0, 3.0, 3.0, 3.0],
        ],
    },
    "18s": {
        4: [
            [4.0, 5.0, 5.0, 4.0],  # Bookended: hero pair held in the middle
            [3.0, 5.0, 5.0, 5.0],  # Quick hook, then three even holds
        ],
        5: [
            [4.0, 3.0, 4.0, 3.0, 4.0],  # Alternating long/short
            [3.0, 4.0, 4.0, 4.0, 3.0],
            [3.0, 3.0, 4.0, 5.0, 3.0],  # Accelerating build, snap close
            [4.0, 4.0, 3.0, 3.0, 4.0],  # Slow open, quick core, resolve
        ],
        # Six scenes in 18s leaves no room to vary: every scene must be 3.0s
        # once nothing may fall below the renderable minimum.
        6: [
            [3.0, 3.0, 3.0, 3.0, 3.0, 3.0],
        ],
    },
    "24s": {
        5: [
            [4.0, 5.0, 5.0, 5.0, 5.0],  # Quick open, then even holds
            [5.0, 4.0, 5.0, 5.0, 5.0],  # Dip in the second beat
        ],
        6: [
            [4.0, 4.0, 4.0, 4.0, 4.0, 4.0],
            [3.0, 5.0, 4.0, 5.0, 4.0, 3.0],  # Syncopated, twin accents
            [3.0, 4.0, 5.0, 5.0, 4.0, 3.0],  # Rising build, tapered close
            [5.0, 4.0, 3.0, 3.0, 4.0, 5.0],  # Bookended, quick core
        ],
        7: [
            [3.0, 3.0, 4.0, 4.0, 4.0, 3.0, 3.0],  # Centre-weighted
            [4.0, 3.0, 3.0, 3.0, 3.0, 4.0, 4.0],  # Quick core, longest last
        ],
        # Eight scenes in 24s is likewise fixed at the 3.0s floor.
        8: [
            [3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0],
        ],
    },
    "30s": {
        6: [
            [5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
        ],
        7: [
            [4.0, 4.0, 5.0, 5.0, 4.0, 4.0, 4.0],  # Centre-weighted
            [3.0, 4.0, 5.0, 5.0, 5.0, 4.0, 4.0],  # Rise to a mid hero
        ],
        8: [
            [4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 3.0, 3.0],
            [3.0, 3.0, 4.0, 5.0, 5.0, 4.0, 3.0, 3.0],  # Arc: open, swell, close
        ],
    },
    "10s": {
        3: [
            [3.0, 4.0, 3.0],
            [4.0, 3.0, 3.0],
        ],
    },
}


def get_pacing_options_json() -> str:
    """Returns a JSON string of the pacing presets for LLM injection."""
    import json

    return json.dumps(PACING_PRESETS, indent=2)


def get_blueprint_for_count(total_duration: float, scene_count: int) -> List[float]:
    """Fallback logic to distribute duration if no preset matches. Maps to nearest lower preset."""
    if total_duration <= 0 or scene_count <= 0:
        return []

    # Extract available presets and find the nearest lower or equal one
    available_presets = sorted([int(k.replace("s", "")) for k in PACING_PRESETS.keys()])
    effective_duration = float(available_presets[0])
    for p in available_presets:
        if p <= total_duration:
            effective_duration = float(p)
        else:
            break

    duration_key = f"{int(effective_duration)}s"

    if duration_key in PACING_PRESETS:
        presets_for_duration = PACING_PRESETS[duration_key]
        import random

        if scene_count in presets_for_duration:
            return random.choice(presets_for_duration[scene_count])

    # Manual distribution logic using the EFFECTIVE duration (0.5s increments)
    avg = effective_duration / scene_count
    # Round to nearest 0.5
    rounded_avg = round(avg * 2) / 2

    durations = [rounded_avg] * (scene_count - 1)
    remaining = effective_duration - sum(durations)
    durations.append(max(0.5, round(remaining * 2) / 2))

    return durations


def matches_any_preset(total_duration: float, llm_durations: List[float]) -> bool:
    """Checks if the provided durations exactly match ANY valid preset combination for the resolved target duration."""
    if total_duration <= 0 or not llm_durations:
        return False

    scene_count = len(llm_durations)
    available_presets = sorted([int(k.replace("s", "")) for k in PACING_PRESETS.keys()])
    effective_duration = float(available_presets[0])
    for p in available_presets:
        if p <= total_duration:
            effective_duration = float(p)
        else:
            break

    duration_key = f"{int(effective_duration)}s"

    if duration_key in PACING_PRESETS and scene_count in PACING_PRESETS[duration_key]:
        for valid_preset in PACING_PRESETS[duration_key][scene_count]:
            if llm_durations == valid_preset:
                return True

    return False


def get_valid_scene_counts_for_duration(total_duration: float) -> List[int]:
    """Returns the list of valid scene counts for a given target duration."""
    if total_duration <= 0:
        return [4]

    available_presets = sorted([int(k.replace("s", "")) for k in PACING_PRESETS.keys()])
    effective_duration = float(available_presets[0])
    for p in available_presets:
        if p <= total_duration:
            effective_duration = float(p)
        else:
            break

    duration_key = f"{int(effective_duration)}s"

    if duration_key in PACING_PRESETS:
        return list(PACING_PRESETS[duration_key].keys())

    return [4]


def get_random_blueprint_for_duration(total_duration: float) -> List[float]:
    """Resolves a target duration to a single, mathematically rigorous array of scene lengths for the LLM to follow natively."""
    if total_duration <= 0:
        return [3.0, 3.0, 3.0, 3.0]  # Default fallback

    available_presets = sorted([int(k.replace("s", "")) for k in PACING_PRESETS.keys()])
    effective_duration = float(available_presets[0])
    for p in available_presets:
        if p <= total_duration:
            effective_duration = float(p)
        else:
            break

    duration_key = f"{int(effective_duration)}s"

    if duration_key in PACING_PRESETS:
        presets_for_duration = PACING_PRESETS[duration_key]
        import random

        # Pick a random scene count from the available ones for this duration
        scene_count = random.choice(list(presets_for_duration.keys()))
        return random.choice(presets_for_duration[scene_count])

    return [3.0, 3.0, 3.0, 3.0]
