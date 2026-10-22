/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/** When to use each agent, shown where a new chat chooses one. */
export const AGENT_DESCRIPTIONS: Readonly<Record<string, string>> = {
  ads_codirector:
    'Use when you want the agent to try several creative directions for a ' +
    'brief and refine the strongest one on its own.',
  ads_x:
    'Use when you have a product and a brief and want a finished video ad. ' +
    'It directs the whole campaign: strategy, storyboard, frames and final cut.',
  creative_toolbox:
    'Use for one-off assets by chat, such as an image, a short video clip, ' +
    'music or a voiceover, when you do not need a full campaign.',
  elements_to_video:
    'Use when a character, mascot or object must look the same in every ' +
    'clip of a multi-scene video.',
};
