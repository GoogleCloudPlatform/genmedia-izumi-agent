/**
 * Copyright 2025 Google LLC
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

document.addEventListener('DOMContentLoaded', () => {
    const canvasTitle = document.getElementById('canvasTitle');
    const timelineContainer = document.getElementById('timeline-container');
    const viewToggle = document.getElementById('viewToggle');
    const toggleLabel = document.getElementById('toggleLabel');
    const urlParams = new URLSearchParams(window.location.search);
    const userId = urlParams.get('userId');
    const canvasId = urlParams.get('canvasId');

    let isVideoView = false;

    if (!userId || !canvasId) {
        canvasTitle.textContent = 'Error: User ID or Canvas ID not provided.';
        return;
    }

    viewToggle.addEventListener('change', () => {
        isVideoView = viewToggle.checked;
        toggleLabel.textContent = isVideoView ? 'View: Videos' : 'View: Images';
        loadCanvas(); // Reload canvas to re-render with the new view
    });

    async function loadCanvas() {
        try {
            const response = await fetch(`/users/${userId}/canvases/${canvasId}`);
            if (!response.ok) {
                throw new Error(`Failed to fetch canvas: ${response.statusText}`);
            }
            const canvas = await response.json();
            
            canvasTitle.textContent = canvas.title || `Canvas ${canvas.id}`;
            if (canvas.video_timeline) {
                renderTimeline(canvas.video_timeline);
            } else {
                timelineContainer.innerHTML = '<p>This canvas does not have a video timeline.</p>';
            }

        } catch (error) {
            console.error('Error loading canvas:', error);
            canvasTitle.textContent = 'Error loading canvas.';
        }
    }

    function renderTimeline(videoTimeline) {
        timelineContainer.innerHTML = ''; // Clear previous render

        if (!videoTimeline || !videoTimeline.video_clips) {
            timelineContainer.innerHTML = '<p>No timeline data available.</p>';
            return;
        }

        const timelineWrapper = document.createElement('div');
        timelineWrapper.id = 'timeline-wrapper';
        timelineContainer.appendChild(timelineWrapper);

        const totalVideoDuration = videoTimeline.video_clips.reduce((acc, clip) => {
            return acc + (clip.trim ? clip.trim.duration_seconds || 0 : 0);
        }, 0);
        
        const totalTransitionDuration = videoTimeline.transitions.reduce((acc, transition) => {
            return acc + (transition && transition.type !== 'none' ? transition.duration_seconds || 0 : 0);
        }, 0);

        const totalDuration = totalVideoDuration + totalTransitionDuration;

        if (totalDuration <= 0) {
            timelineContainer.innerHTML = '<p>No clips with positive duration found in timeline.</p>';
            return;
        }

        timelineWrapper.style.width = `${totalDuration * 100}px`;

        // Pre-calculate clip start times based on sequential layout
        const clip_start_times = [];
        let accumulatedTime = 0;
        for (let i = 0; i < videoTimeline.video_clips.length; i++) {
            clip_start_times.push(accumulatedTime);
            const clipDuration = videoTimeline.video_clips[i].trim?.duration_seconds || 0;
            accumulatedTime += clipDuration;
            if (i < videoTimeline.video_clips.length - 1) {
                const transition = videoTimeline.transitions[i];
                if (transition && transition.type !== 'none') {
                    accumulatedTime += transition.duration_seconds || 0;
                }
            }
        }

        // Timeline Ruler
        const rulerTrack = createTrack('Time');
        const rulerContainer = rulerTrack.querySelector('.clips-container');
        rulerContainer.classList.add('ruler-container');
        for (let i = 0; i <= totalDuration; i++) { // every second
            const marker = document.createElement('div');
            marker.classList.add('ruler-marker');
            marker.style.left = `${(i / totalDuration) * 100}%`;
            if (i % 5 === 0) { // bigger marker every 5 seconds
                marker.classList.add('major');
                const label = document.createElement('span');
                label.classList.add('ruler-label');
                label.textContent = `${i}s`;
                marker.appendChild(label);
            }
            rulerContainer.appendChild(marker);
        }
        timelineWrapper.appendChild(rulerTrack);

        // Video Track & Transitions
        const videoTrackElement = createTrack('Video');
        const videoClipsContainer = videoTrackElement.querySelector('.clips-container');
        let currentTime = 0;
        videoTimeline.video_clips.forEach((clip, index) => {
            const clipElement = createClipElement(clip, currentTime, totalDuration, 'video');
            videoClipsContainer.appendChild(clipElement);
            const clipDuration = clip.trim ? clip.trim.duration_seconds || 0 : 0;
            currentTime += clipDuration;

            if (index < videoTimeline.video_clips.length - 1) {
                const transition = videoTimeline.transitions[index];
                if (transition && transition.type !== 'none') {
                    const transitionDuration = transition.duration_seconds || 0;
                    const transitionElement = createTransitionElement(transition, currentTime, totalDuration);
                    videoClipsContainer.appendChild(transitionElement);
                    currentTime += transitionDuration;
                }
            }
        });
        timelineWrapper.appendChild(videoTrackElement);

        // Audio Tracks
        const audioTracks = []; // Array of { container: HTMLElement, clips: [] }
        const processedAudioClips = (videoTimeline.audio_clips || []).map(clip => {
            const duration = clip.trim ? clip.trim.duration_seconds || 0 : 0;
            const anchorClipStartTime = clip_start_times[clip.start_at.video_clip_index];
            const startTime = anchorClipStartTime + clip.start_at.offset_seconds;
            return { clip, startTime, duration, endTime: startTime + duration };
        });
        processedAudioClips.sort((a, b) => a.startTime - b.startTime || a.duration - b.duration);

        processedAudioClips.forEach(processedClip => {
            const { clip, startTime, endTime } = processedClip;
            let placed = false;
            for (const track of audioTracks) {
                let overlaps = false;
                for (const existingClip of track.clips) {
                    if (startTime < existingClip.endTime && endTime > existingClip.startTime) {
                        overlaps = true;
                        break;
                    }
                }
                if (!overlaps) {
                    const clipElement = createClipElement(clip, startTime, totalDuration, 'audio');
                    track.container.appendChild(clipElement);
                    track.clips.push(processedClip);
                    placed = true;
                    break;
                }
            }

            if (!placed) {
                const newTrackElement = createTrack('Audio');
                const newClipsContainer = newTrackElement.querySelector('.clips-container');
                newClipsContainer.classList.add('audio-clips-container');
                const clipElement = createClipElement(clip, startTime, totalDuration, 'audio');
                newClipsContainer.appendChild(clipElement);
                timelineWrapper.appendChild(newTrackElement);
                audioTracks.push({
                    container: newClipsContainer,
                    clips: [processedClip]
                });
            }
        });
    }

    function createTrack(title) {
        const trackElement = document.createElement('div');
        trackElement.classList.add('track');

        const trackTitle = document.createElement('div');
        trackTitle.classList.add('track-title');
        trackTitle.textContent = title;
        trackElement.appendChild(trackTitle);

        const clipsContainer = document.createElement('div');
        clipsContainer.classList.add('clips-container');
        trackElement.appendChild(clipsContainer);

        return trackElement;
    }

    function createClipElement(clip, startTime, totalDuration, type) {
        const clipElement = document.createElement('div');
        clipElement.classList.add('clip');

        const duration = clip.trim ? clip.trim.duration_seconds || 0 : 0;
        clipElement.style.left = `${(startTime / totalDuration) * 100}%`;
        clipElement.style.width = `${(duration / totalDuration) * 100}%`;

        if (type === 'video') {
            clipElement.classList.add('video-clip');

            const nameElement = document.createElement('div');
            nameElement.classList.add('clip-name');
            let name = 'Unnamed Clip';
            if (clip.asset) {
                name = clip.asset.file_name;
            } else if (clip.first_frame_asset) {
                name = clip.first_frame_asset.file_name;
            } else if (clip.placeholder) {
                name = clip.placeholder;
            }
            nameElement.textContent = name;
            clipElement.appendChild(nameElement);

            const mediaContainer = document.createElement('div');
            mediaContainer.classList.add('media-container');
            clipElement.appendChild(mediaContainer);

            if (isVideoView) {
                const assetToShow = clip.asset;
                if (assetToShow) {
                    const mediaElement = document.createElement('video');
                    mediaElement.src = `/users/${userId}/assets/${assetToShow.id}/view?version=${assetToShow.current_version}`;
                    mediaElement.classList.add('clip-content');
                    mediaElement.controls = true;
                    mediaContainer.appendChild(mediaElement);
                } else if (clip.placeholder) {
                    const placeholder = document.createElement('div');
                    placeholder.classList.add('placeholder');
                    placeholder.textContent = clip.placeholder;
                    mediaContainer.appendChild(placeholder);
                }
            } else { // Image view
                mediaContainer.style.flexDirection = 'row';
                mediaContainer.style.justifyContent = 'space-between';
                let contentAdded = false;
                if (clip.first_frame_asset) {
                    const firstFrameImg = document.createElement('img');
                    firstFrameImg.src = `/users/${userId}/assets/${clip.first_frame_asset.id}/view?version=${clip.first_frame_asset.current_version}`;
                    firstFrameImg.classList.add('clip-content', 'frame-image');
                    mediaContainer.appendChild(firstFrameImg);
                    contentAdded = true;
                }
                if (clip.last_frame_asset) {
                    const lastFrameImg = document.createElement('img');
                    lastFrameImg.src = `/users/${userId}/assets/${clip.last_frame_asset.id}/view?version=${clip.last_frame_asset.current_version}`;
                    lastFrameImg.classList.add('clip-content', 'frame-image');
                    mediaContainer.appendChild(lastFrameImg);
                    contentAdded = true;
                }
                if (!contentAdded && clip.placeholder) {
                    const placeholder = document.createElement('div');
                    placeholder.classList.add('placeholder');
                    placeholder.textContent = clip.placeholder;
                    mediaContainer.appendChild(placeholder);
                }
            }
        } else { // audio
            clipElement.classList.add('audio-clip');
            if (clip.asset) {
                const nameElement = document.createElement('div');
                nameElement.classList.add('clip-name');
                nameElement.textContent = clip.asset.file_name;
                clipElement.appendChild(nameElement);

                const audioElement = document.createElement('audio');
                audioElement.src = `/users/${userId}/assets/${clip.asset.id}/view?version=${clip.asset.current_version}`;
                audioElement.controls = true;
                audioElement.style.width = '100%';
                clipElement.appendChild(audioElement);
            } else if (clip.placeholder) {
                const placeholder = document.createElement('div');
                placeholder.classList.add('placeholder');
                placeholder.textContent = clip.placeholder;
                clipElement.appendChild(placeholder);
            }

            if (clip.fade_in_duration_seconds > 0) {
                const fadeIn = document.createElement('div');
                fadeIn.classList.add('fade', 'fade-in');
                
                const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                svg.setAttribute('width', '100%');
                svg.setAttribute('height', '100%');
                svg.setAttribute('viewBox', '0 0 100 40');
                svg.setAttribute('preserveAspectRatio', 'none');

                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                path.setAttribute('d', 'M 0 40 C 50 40, 50 0, 100 0');
                path.setAttribute('stroke', 'white');
                path.setAttribute('stroke-width', '2');
                path.setAttribute('fill', 'transparent');
                
                svg.appendChild(path);
                fadeIn.appendChild(svg);
                clipElement.appendChild(fadeIn);
            }
            if (clip.fade_out_duration_seconds > 0) {
                const fadeOut = document.createElement('div');
                fadeOut.classList.add('fade', 'fade-out');

                const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                svg.setAttribute('width', '100%');
                svg.setAttribute('height', '100%');
                svg.setAttribute('viewBox', '0 0 100 40');
                svg.setAttribute('preserveAspectRatio', 'none');

                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                path.setAttribute('d', 'M 0 0 C 50 0, 50 40, 100 40');
                path.setAttribute('stroke', 'white');
                path.setAttribute('stroke-width', '2');
                path.setAttribute('fill', 'transparent');

                svg.appendChild(path);
                fadeOut.appendChild(svg);
                clipElement.appendChild(fadeOut);
            }
        }
        
        clipElement.title = `Duration: ${duration}s`;

        return clipElement;
    }

    function createTransitionElement(transition, startTime, totalDuration) {
        const transitionElement = document.createElement('div');
        transitionElement.classList.add('transition');
        const transitionDuration = transition.duration_seconds || 0;
        transitionElement.style.left = `${(startTime / totalDuration) * 100}%`;
        transitionElement.style.width = `${(transitionDuration / totalDuration) * 100}%`;
        transitionElement.textContent = transition.type.toUpperCase();
        transitionElement.title = `Type: ${transition.type}, Duration: ${transitionDuration}s`;
        return transitionElement;
    }

    loadCanvas();
});