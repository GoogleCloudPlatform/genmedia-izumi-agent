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

import json
from pathlib import Path

from google.adk.tools.tool_context import ToolContext

import mediagent_kit.services.aio
from utils.adk import get_user_id_from_context

from ..instructions.verifier import video_verifier_instruction
from ..utils import common_utils, final_video_verifier_model

# The path to the verifier prompt, relative to this file
_VERIFIER_PROMPT_PATH = (
    Path(__file__).parent.parent
    / "instructions/verifier/video_verifier.md"
)


async def evaluate_final_video(tool_context: ToolContext) -> dict:
    """
    Evaluates the final stitched video using a multimodal model.
    If video generation failed, it returns a valid VerificationResult with a score of 0.
    """
    storyboard = tool_context.state.get(common_utils.STORYBOARD_KEY, {})
    parameters = tool_context.state.get(common_utils.PARAMETERS_KEY, {})
    user_assets = tool_context.state.get(common_utils.USER_ASSETS_KEY, {})

    iteration_num = tool_context.state.get("mab_iteration", 0)
    user_id = get_user_id_from_context(tool_context)
    final_video_asset_id = storyboard.get("final_video_asset_id")

    # If the video asset ID is missing, it means generation failed.
    # Store a zero-score VerificationResult in the state and return.
    if not final_video_asset_id:
        result = {
            "breakdown": {},
            "feedback": "Video generation failed; no video was produced for evaluation.",
            "primary_fault": "Video Generation Failure",
            "actionable_feedback": "Check the generation agent logs for errors.",
            "score": 0,
        }
        tool_context.state[common_utils.VERIFICATION_RESULT_KEY] = result
        return common_utils.tool_failure("Video generation failed.")

    asset_service = mediagent_kit.services.aio.get_asset_service()
    try:
        final_video_asset = await asset_service.get_asset_by_id(
            asset_id=final_video_asset_id
        )
    except Exception as e:
        result = {
            "breakdown": {},
            "feedback": f"Could not retrieve final video asset for evaluation: {e}",
            "primary_fault": "Asset Retrieval Failure",
            "actionable_feedback": "Check asset service and GCS permissions.",
            "score": 0,
        }
        tool_context.state[common_utils.VERIFICATION_RESULT_KEY] = result
        return common_utils.tool_failure(str(e))

    # Load the base verifier prompt from the markdown file
    with open(_VERIFIER_PROMPT_PATH) as f:
        prompt_template = f.read()

    # Match placeholders to common_utils keys
    context_string = video_verifier_instruction.INSTRUCTION_CONTEXT.format(
        **{
            common_utils.PARAMETERS_KEY: parameters,
            common_utils.USER_ASSETS_KEY: user_assets,
            common_utils.ANNOTATED_REFERENCE_VISUALS_KEY: tool_context.state.get(
                common_utils.ANNOTATED_REFERENCE_VISUALS_KEY, {}
            ),
            common_utils.CREATIVE_CONFIG_KEY: tool_context.state.get(
                common_utils.CREATIVE_CONFIG_KEY, {}
            ),
            common_utils.THEORETICAL_DEFS_KEY: tool_context.state.get(
                common_utils.THEORETICAL_DEFS_KEY, {}
            ),
            common_utils.STORYBOARD_KEY: storyboard,
        }
    )

    final_prompt = prompt_template.format(
        json_output_schema=final_video_verifier_model.DESCRIPTION,
        context=context_string,
    )

    # Get the list of original user asset filenames
    user_asset_filenames = list(user_assets.keys())

    # Create a combined list for the multimodal prompt
    all_reference_filenames = [final_video_asset.file_name, *user_asset_filenames]

    mediagen_service = mediagent_kit.services.aio.get_media_generation_service()
    try:
        response_asset = await mediagen_service.generate_text_with_gemini(
            user_id=user_id,
            prompt=final_prompt,
            reference_image_filenames=all_reference_filenames,
            file_name=f"iter_{iteration_num}_verification_result.txt",
        )

        blob = await asset_service.get_asset_blob(response_asset.id)
        raw_response_text = blob.content.decode()

        try:
            start_index = raw_response_text.find("{")
            end_index = raw_response_text.rfind("}") + 1
            if start_index != -1 and end_index != -1:
                json_string = raw_response_text[start_index:end_index]
                parsed_json = json.loads(json_string)

                # Authoritative Summation: Always recalculate score from breakdown for consistency
                if "breakdown" in parsed_json:
                    breakdown_scores = [v for v in parsed_json["breakdown"].values() if isinstance(v, (int, float))]
                    if breakdown_scores:
                        parsed_json["score"] = sum(breakdown_scores)

                tool_context.state[common_utils.VERIFICATION_RESULT_KEY] = parsed_json
                return common_utils.tool_success("Verification complete.")
            else:
                raise json.JSONDecodeError(
                    "Could not find JSON block in the response.", raw_response_text, 0
                )

        except json.JSONDecodeError as e:
            result = {
                "breakdown": {},
                "feedback": f"Failed to parse LLM response as JSON: {e}. Raw response: {raw_response_text}",
                "primary_fault": "JSON Parsing Failure",
                "actionable_feedback": "Review the verifier prompt and LLM output.",
                "score": 0,
            }
            tool_context.state[common_utils.VERIFICATION_RESULT_KEY] = result
            return common_utils.tool_failure(str(e))

    except Exception as e:
        result = {
            "breakdown": {},
            "feedback": f"An unexpected error occurred during video evaluation: {e}",
            "primary_fault": "Video Evaluation Failure",
            "actionable_feedback": "Check the mediagen service logs.",
            "score": 0,
        }
        tool_context.state[common_utils.VERIFICATION_RESULT_KEY] = result
        return common_utils.tool_failure(str(e))
