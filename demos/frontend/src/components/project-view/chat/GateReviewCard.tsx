/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { useState } from "react";
import {
  alpha,
  Box,
  Button,
  Chip,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import CheckIcon from "@mui/icons-material/Check";
import MovieFilterIcon from "@mui/icons-material/MovieFilter";
import ReplayIcon from "@mui/icons-material/Replay";
import TuneIcon from "@mui/icons-material/Tune";
import ViewTimelineIcon from "@mui/icons-material/ViewTimeline";
import type {
  GateDecision,
  GatePayload,
  GateScene,
  GateStage,
  PendingGate,
  ProjectAsset,
} from "../../../data/types";

const STAGES: Record<
  GateStage,
  { step: string; title: string; icon: typeof TuneIcon; accent: string }
> = {
  strategy: {
    step: "Checkpoint 1 of 3",
    title: "Campaign strategy",
    icon: AutoAwesomeIcon,
    accent: "#818CF8", // primary.light
  },
  storyboard: {
    step: "Checkpoint 2 of 3",
    title: "Storyboard",
    icon: ViewTimelineIcon,
    accent: "#F472B6", // secondary.light
  },
  final_cut: {
    step: "Checkpoint 3 of 3",
    title: "Final cut",
    icon: MovieFilterIcon,
    accent: "#34D399",
  },
};

/** The order the checkpoints happen in, for the progress dots. */
const STAGE_ORDER: GateStage[] = ["strategy", "storyboard", "final_cut"];

/** What the guidance box is actually asking for at each checkpoint. */
const GUIDANCE_PROMPTS: Record<GateStage, string> = {
  strategy: "What have I misunderstood?",
  storyboard: "What should change before anything is rendered?",
  final_cut: "Which clips need another take?",
};

const FALLBACK_STAGE = {
  step: "Review",
  title: "Review required",
  icon: TuneIcon,
  accent: "#818CF8",
};

interface GateReviewCardProps {
  gate: PendingGate;
  onRespond: (decision: GateDecision, guidance: string) => void;
  disabled?: boolean;
  /** Used to show the real assets a checkpoint refers to, not just names. */
  projectAssets?: readonly ProjectAsset[];
  /**
   * Set for a checkpoint that has already been answered. The card becomes a
   * collapsed record of what was approved, with no way to answer it again.
   */
  verdict?: { decision?: GateDecision; guidance?: string };
}

/** Finds the asset a checkpoint names, by id or by filename. */
function findAsset(
  assets: readonly ProjectAsset[] | undefined,
  key: string | undefined,
): ProjectAsset | undefined {
  if (!assets || !key) {
    return undefined;
  }
  return assets.find((a) => a.id === key || a.fileName === key);
}

/**
 * The uploaded assets, shown rather than listed.
 *
 * A row of filenames tells the reviewer nothing about whether the right
 * pictures were picked up; the pictures themselves do.
 */
function AssetStrip({
  names,
  projectAssets,
}: {
  names?: string[];
  projectAssets?: readonly ProjectAsset[];
}) {
  if (!names || names.length === 0) {
    return null;
  }
  return (
    <Box>
      <Typography
        variant="caption"
        sx={{
          color: "text.secondary",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          fontSize: "0.65rem",
          display: "block",
          mb: 0.5,
        }}
      >
        Assets
      </Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
        {names.map((name) => {
          const asset = findAsset(projectAssets, name);
          return asset?.url ? (
            <Box
              key={name}
              component="img"
              src={asset.thumbnailUrl || asset.url}
              alt={name}
              title={name}
              sx={{
                width: 56,
                height: 56,
                objectFit: "cover",
                borderRadius: 1,
                border: "1px solid",
                borderColor: "divider",
              }}
            />
          ) : (
            <Chip key={name} label={name} size="small" variant="outlined" />
          );
        })}
      </Box>
    </Box>
  );
}

/**
 * Renders a payload value as text.
 *
 * Checkpoint payloads are agent output, so a field that is documented as a
 * string can still arrive as a structure — `final_video.asset_ref` is a whole
 * object. Rendering one of those straight into JSX throws and takes the app
 * down with it, so everything is flattened to text on the way in.
 */
function asText(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    return value.map(asText).filter(Boolean).join(", ");
  }
  const record = value as Record<string, unknown>;
  // Asset-shaped objects are worth naming; anything else is noise here.
  return asText(record.id ?? record.name ?? record.asset_id ?? "");
}

/** A label above its value, so long values are not squeezed into a column. */
function Field({ label, value }: { label: string; value: unknown }) {
  const text = asText(value);
  if (!text) {
    return null;
  }
  return (
    <Box>
      <Typography
        variant="caption"
        sx={{
          color: "text.secondary",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          fontSize: "0.65rem",
          display: "block",
        }}
      >
        {label}
      </Typography>
      <Typography variant="body2" sx={{ lineHeight: 1.45 }}>
        {text}
      </Typography>
    </Box>
  );
}

/** Short facts, shown as chips so they read at a glance. */
function Facts({ values, accent }: { values: unknown[]; accent: string }) {
  const labels = values.map(asText).filter(Boolean);
  if (labels.length === 0) {
    return null;
  }
  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
      {labels.map((label) => (
        <Chip
          key={label}
          label={label}
          size="small"
          sx={{
            height: 22,
            fontSize: "0.7rem",
            bgcolor: alpha(accent, 0.14),
            color: "text.primary",
            border: `1px solid ${alpha(accent, 0.35)}`,
          }}
        />
      ))}
    </Box>
  );
}

function SceneRow({
  scene,
  index,
  accent,
}: {
  scene: GateScene;
  index: number;
  accent: string;
}) {
  const duration = asText(scene.duration_seconds);
  return (
    <Box
      sx={{
        display: "flex",
        gap: 1.25,
        py: 1,
        borderTop: index === 0 ? "none" : "1px solid",
        borderColor: "divider",
      }}
    >
      <Box
        sx={{
          flexShrink: 0,
          width: 22,
          height: 22,
          borderRadius: "50%",
          bgcolor: alpha(accent, 0.18),
          color: accent,
          fontSize: "0.7rem",
          fontWeight: 700,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {index + 1}
      </Box>
      <Box sx={{ minWidth: 0, flexGrow: 1 }}>
        <Box
          sx={{
            display: "flex",
            alignItems: "baseline",
            gap: 1,
            flexWrap: "wrap",
          }}
        >
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {asText(scene.topic) ||
              asText(scene.scene_id) ||
              `Scene ${index + 1}`}
          </Typography>
          {duration && (
            <Typography variant="caption" sx={{ color: "text.secondary" }}>
              {duration}s
            </Typography>
          )}
          {scene.rendered && (
            <Typography variant="caption" sx={{ color: accent }}>
              rendered
            </Typography>
          )}
        </Box>
        {scene.action && (
          <Typography
            variant="caption"
            sx={{ display: "block", color: "text.secondary", lineHeight: 1.5 }}
          >
            {asText(scene.action)}
          </Typography>
        )}
        {scene.opening_frame && (
          <Typography
            variant="caption"
            sx={{ display: "block", color: "text.secondary", lineHeight: 1.5 }}
          >
            <Box component="span" sx={{ opacity: 0.65 }}>
              Opens on:{" "}
            </Box>
            {asText(scene.opening_frame)}
          </Typography>
        )}
        {scene.voiceover && (
          <Typography
            variant="caption"
            sx={{
              display: "block",
              mt: 0.5,
              pl: 1,
              borderLeft: `2px solid ${alpha(accent, 0.5)}`,
              fontStyle: "italic",
            }}
          >
            {asText(scene.voiceover)}
          </Typography>
        )}
        {scene.shot && Object.keys(scene.shot).length > 0 && (
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 0.75 }}>
            {Object.entries(scene.shot).map(([key, value]) => (
              <Typography
                key={key}
                variant="caption"
                sx={{
                  px: 0.75,
                  py: 0.125,
                  borderRadius: 0.75,
                  bgcolor: alpha(accent, 0.1),
                  color: "text.secondary",
                  fontSize: "0.68rem",
                }}
              >
                <Box component="span" sx={{ opacity: 0.7 }}>
                  {key.replace(/_/g, " ")}:{" "}
                </Box>
                {asText(value)}
              </Typography>
            ))}
          </Box>
        )}
      </Box>
    </Box>
  );
}

/**
 * A rendered take, as opposed to a scene still being planned.
 *
 * At the final checkpoint the work is done and the question has changed: not
 * "should we make this" but "which of these needs another take". So the clip
 * leads with its identifier, which is the handle the reviewer names when
 * asking for a re-render, and puts the intended action last, where it serves
 * as something to compare the footage against.
 */
function ClipRow({
  clip,
  index,
  accent,
}: {
  clip: GateScene;
  index: number;
  accent: string;
}) {
  const duration = asText(clip.duration_seconds);
  const sceneId = asText(clip.scene_id);
  return (
    <Box
      sx={{
        display: 'flex',
        gap: 1.25,
        py: 1,
        borderTop: index === 0 ? 'none' : '1px solid',
        borderColor: 'divider',
      }}
    >
      <Box
        sx={{
          flexShrink: 0,
          width: 26,
          height: 26,
          borderRadius: 1,
          bgcolor: alpha(accent, 0.16),
          color: accent,
          fontSize: '0.7rem',
          fontWeight: 700,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {index + 1}
      </Box>
      <Box sx={{ minWidth: 0, flexGrow: 1 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'baseline',
            gap: 1,
            flexWrap: 'wrap',
          }}
        >
          {sceneId && (
            <Typography
              variant="caption"
              sx={{
                fontFamily: 'monospace',
                fontWeight: 600,
                color: accent,
                fontSize: '0.72rem',
              }}
            >
              {sceneId}
            </Typography>
          )}
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            {asText(clip.topic)}
          </Typography>
          {duration && (
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              · {duration}s
            </Typography>
          )}
        </Box>
        {clip.voiceover && (
          <Typography
            variant="caption"
            sx={{
              display: 'block',
              mt: 0.25,
              pl: 1,
              borderLeft: `2px solid ${alpha(accent, 0.5)}`,
              fontStyle: 'italic',
            }}
          >
            {asText(clip.voiceover)}
          </Typography>
        )}
        {clip.action && (
          <Typography
            variant="caption"
            sx={{ display: 'block', mt: 0.25, color: 'text.secondary' }}
          >
            <Box component="span" sx={{ opacity: 0.65 }}>
              Intended:{' '}
            </Box>
            {asText(clip.action)}
          </Typography>
        )}
      </Box>
    </Box>
  );
}

/**
 * How a cinematographer would name each part of the direction.
 *
 * The payload keys are terse and two pairs of them read as duplicates without
 * this: "lighting" next to "key light" looks like the same thing said twice
 * when they are the ambient wash and the light on the subject, and "optics"
 * next to "texture" gives no clue that one is the lens and the other the film
 * stock. All four are injected into every scene prompt, so the reviewer needs
 * to be able to tell them apart to change the right one.
 */
const DIRECTION_LABELS: Record<string, string> = {
  style_mode: "Mode",
  lighting: "Ambient light",
  key_light: "Key light",
  optics: "Lens",
  texture: "Film texture",
  setting: "Setting",
  music: "Music",
  cast: "Cast",
  wardrobe: "Wardrobe",
};

/**
 * The art direction the whole campaign inherits.
 *
 * It is settled before a single scene is written, which makes the strategy
 * checkpoint the one place where changing it costs nothing.
 */
function DirectionGrid({
  direction,
  accent,
}: {
  direction?: Record<string, string>;
  accent: string;
}) {
  const entries = Object.entries(direction || {}).filter(([, v]) => asText(v));
  if (entries.length === 0) {
    return null;
  }
  return (
    <Box>
      <Typography
        variant="caption"
        sx={{
          color: "text.secondary",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          fontSize: "0.65rem",
          display: "block",
          mb: 0.5,
        }}
      >
        Direction
      </Typography>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
          gap: 0.75,
        }}
      >
        {entries.map(([key, value]) => (
          <Box
            key={key}
            sx={{
              px: 1,
              py: 0.5,
              borderRadius: 1,
              bgcolor: alpha(accent, 0.08),
            }}
          >
            <Typography
              variant="caption"
              sx={{
                display: "block",
                color: "text.secondary",
                fontSize: "0.62rem",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              {DIRECTION_LABELS[key] || key.replace(/_/g, " ")}
            </Typography>
            <Typography variant="caption" sx={{ lineHeight: 1.4 }}>
              {asText(value)}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
}

/** Stage-specific detail: what the reviewer is being asked to judge. */
function GateDetails({
  payload,
  accent,
  projectAssets,
}: {
  payload: GatePayload;
  accent: string;
  projectAssets?: readonly ProjectAsset[];
}) {
  if (payload.stage === "strategy") {
    const campaign = payload.campaign || {};
    return (
      <Stack spacing={1.5}>
        <Field label="Campaign" value={campaign.name} />
        <Facts
          values={[
            campaign.duration,
            campaign.orientation,
            payload.look?.name,
            payload.features_a_person ? "features a person" : "product only",
            campaign.vertical,
          ]}
          accent={accent}
        />
        <Field label="Audience" value={campaign.audience} />
        <Field label="Key message" value={campaign.key_message} />
        <Field
          label="Theme and tone"
          value={[campaign.theme, campaign.tone].filter(Boolean).join(" · ")}
        />
        <Field label="On screen" value={payload.creator_description} />
        <AssetStrip
          names={payload.uploaded_assets}
          projectAssets={projectAssets}
        />
        <DirectionGrid direction={payload.direction} accent={accent} />
      </Stack>
    );
  }

  const runtime = (items: readonly GateScene[]) =>
    items.reduce((sum, s) => sum + (Number(s.duration_seconds) || 0), 0);

  if (payload.stage === 'final_cut') {
    // The cut is deliberately not played here. A 9:16 video at chat width is
    // either letterboxed to uselessness or taller than the card; it is watched
    // where there is room for it, and this card is where the verdict is given.
    const clips = payload.clips || [];
    const finalVideo = findAsset(projectAssets, payload.final_video?.asset_id);
    const total = runtime(clips);
    return (
      <Stack spacing={1.25}>
        <Field
          label="Finished cut"
          value={finalVideo?.fileName || payload.final_video?.asset_id}
        />
        <Facts
          values={[
            `${clips.length} ${clips.length === 1 ? 'clip' : 'clips'}`,
            total ? `${total}s` : '',
            'rendered and stitched',
          ]}
          accent={accent}
        />
        <Typography
          variant="caption"
          sx={{ color: 'text.secondary', display: 'block' }}
        >
          Watch the cut, then accept it or name the clips that need another
          take. Only those are re-rendered.
        </Typography>
        <Box>
          {clips.map((clip, index) => (
            <ClipRow
              key={asText(clip.scene_id) || index}
              clip={clip}
              index={index}
              accent={accent}
            />
          ))}
        </Box>
      </Stack>
    );
  }

  const scenes = payload.scenes || [];
  const total = runtime(scenes);
  return (
    <Stack spacing={1}>
      <Field label="Campaign" value={payload.campaign_title} />
      <Field label="Music" value={payload.music} />
      <Facts
        values={[
          `${scenes.length} ${scenes.length === 1 ? 'scene' : 'scenes'}`,
          total ? `${total}s total` : '',
          'nothing rendered yet',
        ]}
        accent={accent}
      />
      <Box>
        {scenes.map((scene, index) => (
          <SceneRow
            key={asText(scene.scene_id) || index}
            scene={scene}
            index={index}
            accent={accent}
          />
        ))}
      </Box>
    </Stack>
  );
}

/**
 * The approval control for a suspended review checkpoint.
 *
 * The run stays suspended until this sends a verdict, so the card is the only
 * way forward — typing into the chat box will not resume it.
 */
export default function GateReviewCard({
  gate,
  onRespond,
  disabled = false,
  projectAssets,
  verdict,
}: GateReviewCardProps) {
  const [guidance, setGuidance] = useState("");
  // An answered checkpoint opens collapsed: it is there to be found again,
  // not to compete with the live conversation for space.
  const [expanded, setExpanded] = useState(false);
  const stage = STAGES[gate.payload.stage] || FALLBACK_STAGE;
  const stageIndex = STAGE_ORDER.indexOf(gate.payload.stage);
  const answered = Boolean(verdict);
  const showDetails = !answered || expanded;
  const StageIcon = stage.icon;
  const hasGuidance = guidance.trim() !== "";

  const respond = (decision: GateDecision) => {
    onRespond(decision, guidance.trim());
    setGuidance("");
  };

  return (
    <Paper
      elevation={0}
      data-testid="gate-review-card"
      sx={{
        mb: 1.5,
        overflow: "hidden",
        borderRadius: 2,
        border: "1px solid",
        borderColor: alpha(stage.accent, 0.4),
        bgcolor: "background.paper",
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1,
          px: 2,
          py: 1.25,
          background: `linear-gradient(90deg, ${alpha(stage.accent, 0.22)} 0%, ${alpha(
            stage.accent,
            0.04,
          )} 100%)`,
          borderBottom: "1px solid",
          borderColor: alpha(stage.accent, 0.25),
        }}
      >
        <StageIcon sx={{ fontSize: 18, color: stage.accent }} />
        <Box sx={{ minWidth: 0 }}>
          <Typography
            variant="caption"
            sx={{
              display: "block",
              color: stage.accent,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              fontSize: "0.62rem",
              lineHeight: 1.3,
            }}
          >
            {stage.step}
          </Typography>
          <Typography variant="subtitle2" sx={{ lineHeight: 1.3 }}>
            {stage.title}
          </Typography>
        </Box>
        <Box sx={{ ml: "auto", display: "flex", gap: 0.5, pl: 1 }}>
          {STAGE_ORDER.map((name, index) => (
            <Box
              key={name}
              title={STAGES[name].title}
              sx={{
                width: index === stageIndex ? 18 : 6,
                height: 6,
                borderRadius: 3,
                bgcolor:
                  index === stageIndex
                    ? stage.accent
                    : alpha(stage.accent, index < stageIndex ? 0.55 : 0.2),
                transition: "width 200ms ease",
              }}
            />
          ))}
        </Box>
        {answered && (
          <Button
            size="small"
            onClick={() => setExpanded((open) => !open)}
            sx={{ ml: 1, color: "text.secondary", minWidth: 0 }}
          >
            {expanded ? "Hide" : "View"}
          </Button>
        )}
      </Box>

      {answered && (
        <Box
          sx={{
            px: 2,
            py: 1,
            display: "flex",
            alignItems: "baseline",
            gap: 1,
            flexWrap: "wrap",
          }}
        >
          <Chip
            label={verdict?.decision || "answered"}
            size="small"
            sx={{
              height: 20,
              fontSize: "0.68rem",
              fontWeight: 600,
              bgcolor: alpha(stage.accent, 0.18),
              color: "text.primary",
            }}
          />
          {verdict?.guidance && (
            <Typography variant="caption" sx={{ color: "text.secondary" }}>
              {asText(verdict.guidance)}
            </Typography>
          )}
        </Box>
      )}

      {showDetails && (
        <Box sx={{ px: 2, py: 1.75, pt: answered ? 0 : 1.75 }}>
          {gate.payload.message && (
            <Typography
              variant="body2"
              sx={{ mb: 1.75, color: "text.secondary", lineHeight: 1.6 }}
            >
              {asText(gate.payload.message)}
            </Typography>
          )}

          <Box
            sx={{
              maxHeight: 300,
              overflowY: "auto",
              p: 1.5,
              borderRadius: 1.5,
              bgcolor: alpha(stage.accent, 0.05),
            }}
          >
            <GateDetails
              payload={gate.payload}
              accent={stage.accent}
              projectAssets={projectAssets}
            />
          </Box>

          {!answered && (
            <TextField
              placeholder={
            GUIDANCE_PROMPTS[gate.payload.stage] || 'What should change?'
          }
              fullWidth
              size="small"
              multiline
              minRows={1}
              maxRows={4}
              value={guidance}
              onChange={(e) => setGuidance(e.target.value)}
              disabled={disabled}
              sx={{ mt: 1.75 }}
            />
          )}

          {!answered && (
            <Stack direction="row" spacing={1} sx={{ mt: 1.5 }}>
              <Button
                variant="contained"
                size="small"
                disableElevation
                startIcon={<CheckIcon />}
                disabled={disabled}
                onClick={() => respond("accept")}
                sx={{
                  bgcolor: stage.accent,
                  color: "common.black",
                  fontWeight: 600,
                  "&:hover": { bgcolor: alpha(stage.accent, 0.85) },
                }}
              >
                Accept
              </Button>
              <Button
                variant="outlined"
                size="small"
                startIcon={<TuneIcon />}
                disabled={disabled || !hasGuidance}
                onClick={() => respond("modify")}
              >
                Request changes
              </Button>
              <Button
                variant="text"
                size="small"
                color="inherit"
                startIcon={<ReplayIcon />}
                disabled={disabled || !hasGuidance}
                onClick={() => respond("regenerate")}
                sx={{ color: "text.secondary" }}
              >
                Start over
              </Button>
            </Stack>
          )}
        </Box>
      )}
    </Paper>
  );
}
