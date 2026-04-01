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

"""Tools for rewriting and generating voiceovers for grouped scenes."""

import logging
import uuid
from typing import Optional

import mediagent_kit.services.aio
from mediagent_kit.services.types import Asset

from ...utils.storyboard.storyboard_model import VoiceoverGroup

logger = logging.getLogger(__name__)

REWRITE_INSTRUCTION = """
You are a creative scriptwriter for high-end video advertisements. Your task is to rewrite choppy, short voiceover snippets into a single, flowing narrative script that maximizes the capabilities of an advanced Gemini 2.5 Pro TTS model.

**CRITICAL RULE: OUTPUT CONTENT ONLY.**
Respond ONLY with the rewritten script text. Do NOT include any introductory or concluding remarks (e.g., "Here is your script", "Revised version:"). Any text you output will be spoken literally by the TTS engine.

Total Target Duration: {total_duration:.1f} seconds.

Original text snippets:
{original_texts_formatted}

**TASK:**
Rewrite these snippets into a compelling narrative (1-3 sentences). The goal is a professional, human-like delivery that sounds natural across multiple scenes.

**GUIDELINES FOR PROSODY & EMOTION:**

1. **EMOTIONAL ALIGNMENT:** Write emotionally rich text. Use energetic verbs for excitement, or sophisticated language for premium vibes.

2. **MARKUP TAGS (THE CONTROL LEVERS):** You MUST inject bracketed tags to guide the performance. Use the following EXACT syntax:

   - **Pacing and Pauses (Rhythm):**
     - `[short pause]` (~250ms): Use to separate clauses or list items.
     - `[medium pause]` (~500ms): Use between distinct sentences or thoughts.
     - `[long pause]` (1000ms+): Use for dramatic effect or before a brand name.

   - **Non-speech sounds (Realism):**
     - Use `[sigh]`, `[laughing]`, or `[uhm]` for human-like realism.

   - **Style modifiers (Dynamic):**
     - Use `[shouting]`, `[whispering]`, `[extremely fast]`, or `[robotic]` for specific emphasis.

3. **CONSTRAINTS:**
   - The rewritten script MUST be concise enough to be spoken within {total_duration:.1f} seconds.
   - Maintain the core message of the original snippets.
   - **EXTREME SHORT DURATION RULE (Under 3 seconds):** If the Total Target Duration is less than 3.0 seconds, you MUST NOT use any pause tags (`[short pause]`, `[medium pause]`, etc.). You MUST write a single, rapid, punchy fragment (e.g., "The ultimate driving machine.") with no internal punctuation so the TTS engine speaks it in one fluid breath.

"""

async def rewrite_group_script(user_id: str, group: VoiceoverGroup, group_index: int = 0) -> str:
    """Uses an LLM to rewrite a group's choppy scripts into a flowing narrative."""
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
    asset_service = mediagent_kit.services.aio.get_asset_service()

    # Format inputs for the prompt
    formatted_texts = []
    for i, script in enumerate(group.original_scripts):
        formatted_texts.append(f"- Segment {i+1}: \"{script}\"")
    
    # Use explicit newline joining
    formatted_str = "\n".join(formatted_texts)
    
    prompt = REWRITE_INSTRUCTION.format(
        total_duration=group.total_duration,
        original_texts_formatted=formatted_str
    )

    try:
        short_id = uuid.uuid4().hex[:8]
        filename = f"voiceover_rewrite_group_{group_index}_{group.group_id}_{short_id}.txt"
        
        response_asset = await mediagen_service.generate_text_with_gemini(
            user_id=user_id,
            prompt=prompt,
            file_name=filename,
            reference_image_filenames=[],
            model="gemini-2.5-flash"
        )
        
        blob = await asset_service.get_asset_blob(response_asset.id)
        rewritten_text = blob.content.decode("utf-8").strip()
        
        if not rewritten_text:
            logger.warning(f"Rewritten text was empty for group {group.group_id}. Fallback to concat.")
            return " ".join(group.original_scripts)
            
        logger.info(f"Rewrote script for group {group.group_id}: '{rewritten_text}'")
        return rewritten_text

    except Exception as e:
        logger.error(f"Failed to rewrite script for group {group.group_id}: {e}")
        return " ".join(group.original_scripts)


async def _shorten_group_script(user_id: str, text: str, target_duration: float) -> str:
    """Uses LLM to condense a script to fit a target duration."""
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
    asset_service = mediagent_kit.services.aio.get_asset_service()
    
    pause_instruction = (
        "Keep [short pause], [medium pause], and [long pause] tags if present."
        if target_duration >= 3.0
        else "CRITICAL: The target duration is extremely short. DO NOT use any pause tags ([short pause], etc.). Write a single, punchy phrase with no internal punctuation."
    )
    
    prompt = (
        "You are a professional script editor. The following voiceover script is too long. "
        f"Rewrite it to be approximately {target_duration:.1f} seconds long while keeping the core message and tone. "
        f"{pause_instruction} "
        "CRITICAL: Respond ONLY with the script. No intro text like 'Revised version:'."
        f"\n\nORIGINAL SCRIPT:\n{text}"
    )
    
    try:
        short_id = uuid.uuid4().hex[:6]
        response = await mediagen_service.generate_text_with_gemini(
            user_id=user_id,
            prompt=prompt,
            file_name=f"shorten_script_{short_id}.txt",
            reference_image_filenames=[],
            model="gemini-2.5-flash"
        )
        blob = await asset_service.get_asset_blob(response.id)
        return blob.content.decode("utf-8").strip()
    except Exception as e:
        logger.warning(f"Failed to shorten script: {e}")
        return text


async def generate_group_voiceover(
    user_id: str, 
    group: VoiceoverGroup, 
    voice_name: str = "Aoede",
    style_prompt: str = "Narrate in a warm, professional, and engaging tone for a high-end commercial. Ensure natural pauses and prosody.",
    group_index: int = 0
) -> Optional[Asset]:
    """Generates the audio asset for a voiceover group with duration optimization."""
    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
    
    # 1. Initial Rewrite
    current_text = await rewrite_group_script(user_id, group, group_index=group_index)
    
    # 2. Generation Loop (Max 3 attempts)
    MAX_ATTEMPTS = 4
    SPEED_TOLERANCE = 1.25 # Allow up to 25% speed-up in post-processing
    
    for attempt in range(MAX_ATTEMPTS):
        filename = f"voiceover_group_{group_index}_{group.group_id}_att{attempt}.mp3"
        
        try:
            logger.info(f"Generating group audio (Attempt {attempt+1}/{MAX_ATTEMPTS})...")
            voiceover_asset = await mediagen_service.generate_speech_single_speaker(
                user_id=user_id,
                file_name=filename,
                text=current_text,
                voice_name=voice_name,
                prompt=style_prompt
            )
            
            # Check Duration
            actual_duration = voiceover_asset.versions[-1].duration_seconds
            max_allowed = group.total_duration * SPEED_TOLERANCE
            
            if actual_duration <= max_allowed:
                logger.info(f"Group {group_index} audio accepted. Duration: {actual_duration:.2f}s (Target: {group.total_duration}s, Limit: {max_allowed:.2f}s)")
                group.rewritten_script = current_text
                group.audio_asset_id = voiceover_asset.id
                return voiceover_asset
            
            # If too long, shorten and retry
            logger.warning(f"Group {group_index} audio too long ({actual_duration:.2f}s > {max_allowed:.2f}s). Shortening script...")
            current_text = await _shorten_group_script(user_id, current_text, group.total_duration * 0.9)
            
        except Exception as e:
            logger.error(f"Failed to generate voiceover audio for group {group.group_id}: {e}")
            break
            
    return None
