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

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GateReviewCard from './GateReviewCard';
import type { PendingGate } from '../../../data/types';

const strategyGate: PendingGate = {
  id: 'call-1',
  name: 'await_strategy_approval',
  payload: {
    status: 'awaiting_human_review',
    stage: 'strategy',
    message: 'Check I have understood the brief.',
    campaign: { name: 'Spring launch', audience: 'runners aged 25-40' },
    look: { name: 'Sunlit Kinetic' },
    features_a_person: true,
    creator_description: 'a marathon runner',
    uploaded_assets: ['shoe.png'],
    direction: {
      lighting: 'golden hour',
      key_light: 'motivated candle-light',
      optics: '85mm f/1.8',
      texture: 'anamorphic 35mm',
      music: 'warm strings, soft piano',
    },
  },
};

const storyboardGate: PendingGate = {
  id: 'call-2',
  name: 'await_storyboard_approval',
  payload: {
    status: 'awaiting_human_review',
    stage: 'storyboard',
    message: 'Here is the storyboard.',
    campaign_title: 'Spring launch',
    scenes: [
      {
        scene_id: 'scene_001',
        topic: 'Hook',
        action: 'Runner laces up at dawn.',
        voiceover: 'Every mile starts somewhere.',
        opening_frame: 'Trainers on a doorstep at dawn.',
        shot: { camera: 'slow dolly in', lens: '50mm' },
        duration_seconds: 4,
      },
    ],
  },
};

const framesGate: PendingGate = {
  id: 'gate-frames',
  name: 'await_frame_approval',
  payload: {
    status: 'awaiting_human_review',
    stage: 'frames',
    message: 'Here are the opening frames.',
    frames: [
      {
        scene_id: 'scene_001',
        topic: 'Hook',
        duration_seconds: 3,
        asset_id: 'img-1',
        opening_frame: 'Trainers on a doorstep at dawn.',
      },
      { scene_id: 'scene_002', topic: 'Payoff', duration_seconds: 3 },
    ],
  },
};

describe('GateReviewCard', () => {
  it('shows the rendered frames, since the picture is what is being judged', () => {
    render(
      <GateReviewCard
        gate={framesGate}
        onRespond={vi.fn()}
        projectAssets={[
          {
            id: 'img-1',
            fileName: 'scene_0_first_frame.png',
            url: 'https://example.test/img-1',
          } as never,
        ]}
      />,
    );

    expect(screen.getByText('Opening frames')).toBeInTheDocument();
    expect(screen.getByText('Checkpoint 3 of 4')).toBeInTheDocument();
    expect(screen.getByAltText('scene_001')).toBeInTheDocument();
    expect(screen.getByText('video not yet generated')).toBeInTheDocument();
  });

  it('marks a frame that did not render rather than leaving a gap', () => {
    render(<GateReviewCard gate={framesGate} onRespond={vi.fn()} />);

    expect(screen.getAllByText('not rendered')).toHaveLength(2);
    expect(screen.getByText(/did not render/)).toBeInTheDocument();
  });

  it('renders the payload message rather than relying on agent text', () => {
    render(<GateReviewCard gate={strategyGate} onRespond={vi.fn()} />);

    expect(
      screen.getByText('Check I have understood the brief.'),
    ).toBeInTheDocument();
    expect(screen.getByText('Campaign strategy')).toBeInTheDocument();
    expect(screen.getByText('Checkpoint 1 of 4')).toBeInTheDocument();
  });

  it('shows the strategy the reviewer is being asked to judge', () => {
    render(<GateReviewCard gate={strategyGate} onRespond={vi.fn()} />);

    expect(screen.getByText('Spring launch')).toBeInTheDocument();
    expect(screen.getByText('runners aged 25-40')).toBeInTheDocument();
    expect(screen.getByText('Sunlit Kinetic')).toBeInTheDocument();
    expect(screen.getByText('a marathon runner')).toBeInTheDocument();
    expect(screen.getByText('shoe.png')).toBeInTheDocument();
  });

  it('shows each scene of a storyboard', () => {
    render(<GateReviewCard gate={storyboardGate} onRespond={vi.fn()} />);

    expect(screen.getByText('Hook')).toBeInTheDocument();
    expect(screen.getByText('Runner laces up at dawn.')).toBeInTheDocument();
    expect(
      screen.getByText('Every mile starts somewhere.'),
    ).toBeInTheDocument();
    expect(screen.getByText('1 scene')).toBeInTheDocument();
    expect(screen.getByText('4s total')).toBeInTheDocument();
  });

  it('renders a structured field without crashing', () => {
    // final_video.asset_ref is an object, not the string the payload implies.
    // Rendering one straight into JSX throws and unmounts the whole app.
    const finalCutGate: PendingGate = {
      id: 'call-3',
      name: 'await_final_cut_approval',
      payload: {
        status: 'awaiting_human_review',
        stage: 'final_cut',
        message: 'Your video is ready.',
        final_video: {
          asset_id: 'asset-42',
          asset_ref: {
            id: 'asset-42',
            asset_type: 'generated',
            workspace_id: 'proj-1',
          },
        } as never,
        clips: [{ scene_id: 'scene_001', topic: 'Hook', duration_seconds: 4 }],
      },
    };

    render(<GateReviewCard gate={finalCutGate} onRespond={vi.fn()} />);

    expect(screen.getByText('Final cut')).toBeInTheDocument();
    expect(screen.getByText('Your video is ready.')).toBeInTheDocument();
  });

  it('accepts without guidance', async () => {
    const onRespond = vi.fn();
    render(<GateReviewCard gate={storyboardGate} onRespond={onRespond} />);

    await userEvent.click(screen.getByRole('button', { name: 'Accept' }));

    expect(onRespond).toHaveBeenCalledWith('accept', '');
  });

  it('sends the guidance along with a change request', async () => {
    const onRespond = vi.fn();
    render(<GateReviewCard gate={storyboardGate} onRespond={onRespond} />);

    await userEvent.type(screen.getByRole('textbox'), 'Shorten scene_001.');
    await userEvent.click(
      screen.getByRole('button', { name: 'Request changes' }),
    );

    expect(onRespond).toHaveBeenCalledWith('modify', 'Shorten scene_001.');
  });

  it('will not send a rejection without saying what is wrong', () => {
    render(<GateReviewCard gate={storyboardGate} onRespond={vi.fn()} />);

    expect(screen.getByRole('button', { name: 'Request changes' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Start over' })).toBeDisabled();
  });

  it('disables every control while a verdict is in flight', () => {
    render(
      <GateReviewCard gate={storyboardGate} onRespond={vi.fn()} disabled />,
    );

    expect(screen.getByRole('button', { name: 'Accept' })).toBeDisabled();
    expect(screen.getByRole('textbox')).toBeDisabled();
  });

  it('shows the direction the whole campaign inherits', () => {
    render(<GateReviewCard gate={strategyGate} onRespond={vi.fn()} />);

    expect(screen.getByText('golden hour')).toBeInTheDocument();
    expect(screen.getByText('85mm f/1.8')).toBeInTheDocument();
    expect(screen.getByText('warm strings, soft piano')).toBeInTheDocument();
  });

  it('shows how each scene will be shot', () => {
    render(<GateReviewCard gate={storyboardGate} onRespond={vi.fn()} />);

    expect(
      screen.getByText('Trainers on a doorstep at dawn.'),
    ).toBeInTheDocument();
    expect(screen.getByText('slow dolly in')).toBeInTheDocument();
    expect(screen.getByText('50mm')).toBeInTheDocument();
  });

  it('names the two lights and the two lens fields distinguishably', () => {
    // The payload keys read as duplicates: "lighting" beside "key light",
    // "optics" beside "texture". All four reach the renderer, so the reviewer
    // has to be able to tell which one to change.
    render(<GateReviewCard gate={strategyGate} onRespond={vi.fn()} />);

    expect(screen.getByText('Ambient light')).toBeInTheDocument();
    expect(screen.getByText('Key light')).toBeInTheDocument();
    expect(screen.getByText('Lens')).toBeInTheDocument();
    expect(screen.getByText('Film texture')).toBeInTheDocument();
  });

  it('shows the uploaded assets rather than listing their names', () => {
    const assets = [
      {
        id: 'a1',
        type: 'image' as const,
        url: 'https://example.test/shoe.png',
        fileName: 'shoe.png',
        currentVersion: 1,
        versions: [],
      },
    ];
    render(
      <GateReviewCard
        gate={strategyGate}
        onRespond={vi.fn()}
        projectAssets={assets}
      />,
    );

    expect(screen.getByAltText('shoe.png')).toHaveAttribute(
      'src',
      'https://example.test/shoe.png',
    );
  });

  it('falls back to the filename when the asset cannot be resolved', () => {
    render(<GateReviewCard gate={strategyGate} onRespond={vi.fn()} />);

    expect(screen.getByText('shoe.png')).toBeInTheDocument();
  });

  it('does not embed the video in the final cut card', () => {
    // A 9:16 cut in a chat-width card is either letterboxed to uselessness or
    // taller than the card.
    const finalCutGate: PendingGate = {
      id: 'call-3',
      name: 'await_final_cut_approval',
      payload: {
        status: 'awaiting_human_review',
        stage: 'final_cut',
        final_video: { asset_id: 'asset-42' },
        clips: [{ scene_id: 'scene_001', topic: 'Hook' }],
      },
    };
    const { container } = render(
      <GateReviewCard gate={finalCutGate} onRespond={vi.fn()} />,
    );

    expect(container.querySelector('video')).toBeNull();
    expect(screen.getByText('asset-42')).toBeInTheDocument();
  });

  it('shows an answered checkpoint as a read-only record', async () => {
    render(
      <GateReviewCard
        gate={storyboardGate}
        onRespond={vi.fn()}
        verdict={{ decision: 'modify', guidance: 'Shorten scene_001.' }}
      />,
    );

    expect(screen.getByText('modify')).toBeInTheDocument();
    expect(screen.getByText('Shorten scene_001.')).toBeInTheDocument();
    // No way to answer it a second time.
    expect(screen.queryByRole('button', { name: 'Accept' })).toBeNull();

    // Collapsed until asked for, then the whole plan is there again.
    expect(screen.queryByText('Hook')).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'View' }));
    expect(screen.getByText('Hook')).toBeInTheDocument();
  });

  it('reviews the final cut as finished takes, not as a plan', () => {
    const finalCutGate: PendingGate = {
      id: 'call-3',
      name: 'await_final_cut_approval',
      payload: {
        status: 'awaiting_human_review',
        stage: 'final_cut',
        final_video: { asset_id: 'asset-42' },
        clips: [
          {
            scene_id: 'scene_001',
            topic: 'Hook',
            action: 'Runner laces up at dawn.',
            voiceover: 'Every mile starts somewhere.',
            duration_seconds: 4,
            asset_id: 'vid-1',
          },
        ],
      },
    };
    render(<GateReviewCard gate={finalCutGate} onRespond={vi.fn()} />);

    // Framed as rendered work, with the id to name for a re-render.
    expect(screen.getByText('1 clip')).toBeInTheDocument();
    expect(screen.getByText('rendered and stitched')).toBeInTheDocument();
    expect(screen.getByText('scene_001')).toBeInTheDocument();
    expect(screen.getByText(/Intended:/)).toBeInTheDocument();
    // Not the storyboard's framing.
    expect(screen.queryByText('nothing rendered yet')).toBeNull();
    expect(
      screen.getByPlaceholderText('Which clips need another take?'),
    ).toBeInTheDocument();
  });

  it('asks the storyboard question at the storyboard checkpoint', () => {
    render(<GateReviewCard gate={storyboardGate} onRespond={vi.fn()} />);

    expect(screen.getByText('nothing rendered yet')).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(
        'What should change before anything is rendered?',
      ),
    ).toBeInTheDocument();
  });
});
