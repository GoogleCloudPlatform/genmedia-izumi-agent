# GenMedia Kit API Specification

**Version**: 1.0
**Date**: 2025-11-20
**Status**: Draft

## 1. Introduction

The GenMedia Kit API provides a comprehensive suite of tools for managing digital assets, generating media using Google's generative AI models (Gemini, Imagen, Veo, Lyria), creating multimedia canvases, and stitching videos.

The API is designed around a resource-oriented architecture. Key concepts include:

- **Assets**: Managed files (images, video, audio) with automatic versioning.
- **Canvases**: Structured representations of multimedia content, either as HTML layouts or Video Timelines.
- **Jobs**: Asynchronous tasks for long-running operations like media generation and video rendering.

## 2. Authentication & Addressing

Currently, the API uses path-based user identification. All endpoints require a `{user_id}` path parameter.

- **Base URL**: `(Defined by deployment)`
- **User Scope**: Resources are scoped to a specific `user_id`.

## 3. Resources

### 3.1. Assets

Assets are the fundamental building blocks. An Asset represents a file (image, video, audio) and tracks its history through versions.

#### Create Asset

Uploads a file to create a new asset or a new version of an existing asset.

- **Endpoint**: `POST /users/{user_id}/assets`
- **Content-Type**: `multipart/form-data`
- **Logic**:
  - If an asset with the provided `file_name` already exists for this user, a **new version** is created and appended to the asset's history.
  - If it does not exist, a new Asset record is created (version 1).
  - Files are stored in Google Cloud Storage (GCS).

**Parameters:**

- `file`: (File, Required) The binary file content.
- `file_name`: (String, Required) The logical name of the file (e.g., "my_image.png").
- `mime_type`: (String, Required) The MIME type (e.g., "image/png").

**Response:** `Asset` object.

```json
{
  "id": "uuid-string",
  "user_id": "user-123",
  "mime_type": "image/png",
  "file_name": "my_image.png",
  "current_version": 1,
  "versions": [
    {
      "asset_id": "uuid-string",
      "version_number": 1,
      "gcs_uri": "gs://bucket/path/to/file",
      "create_time": "2023-10-27T10:00:00Z",
      "image_generate_config": null,
      "music_generate_config": null,
      "video_generate_config": null,
      "speech_generate_config": null,
      "text_generate_config": null
    }
  ]
}
```

| Field             | Type         | Description                                                  |
| :---------------- | :----------- | :----------------------------------------------------------- |
| `id`              | String       | Unique identifier for the asset.                             |
| `user_id`         | String       | The ID of the user who owns the asset.                       |
| `mime_type`       | String       | The MIME type of the asset (e.g., "image/png").              |
| `file_name`       | String       | The logical filename. Used for lookups and display.          |
| `current_version` | Integer      | The latest version number of the asset.                      |
| `versions`        | List[Object] | History of asset versions. See **AssetVersion** model below. |

#### List Assets

Retrieves a list of all assets owned by the user.

- **Endpoint**: `GET /users/{user_id}/assets`
- **Response**: List of `Asset` objects.

#### Get Asset

Retrieves metadata for a specific asset.

- **Endpoint**: `GET /users/{user_id}/assets/{asset_id}`
- **Response**: `Asset` object.

#### Update Asset

Updates asset metadata (currently only `file_name`).

- **Endpoint**: `PATCH /users/{user_id}/assets/{asset_id}`
- **Body**: `AssetUpdate`
  ```json
  { "file_name": "new_name.png" }
  ```
- **Response**: Updated `Asset` object.

#### Delete Asset

Permanently removes an asset and all its version history from the database and GCS.

- **Endpoint**: `DELETE /users/{user_id}/assets/{asset_id}`
- **Response**: `204 No Content`.

#### Download Asset

Downloads the binary content of an asset.

- **Endpoint**: `GET /users/{user_id}/assets/{asset_id}/download`
- **Query Params**:
  - `version`: (Int, Optional) Specific version number to download. Defaults to the latest version.
- **Response**: Binary stream with `Content-Disposition: attachment`.

#### View Asset

Stream an asset for browser display.

- **Endpoint**: `GET /users/{user_id}/assets/{asset_id}/view`
- **Query Params**:
  - `version`: (Int, Optional) Specific version. Defaults to latest (redirects to specific version URL).
- **Response**: Binary stream with `Cache-Control` headers.

---

### 3.2. Media Generation (Async Jobs)

These endpoints trigger long-running generative AI tasks. They return a **Job** object immediately (`202 Accepted`). You must poll the **Jobs API** to get the result.

**Common Response for all Generation Endpoints:** `Job` object.

```json
{
  "id": "job-uuid",
  "user_id": "user-123",
  "job_type": "IMAGE_GENERATION",
  "status": "PENDING",
  "created_at": "2023-10-27T10:00:00Z",
  "updated_at": "2023-10-27T10:00:00Z",
  "job_input": { ... },
  "result_asset_id": null,
  "result_asset": null,
  "error_message": null
}
```

| Field             | Type   | Description                                                                                                                     |
| :---------------- | :----- | :------------------------------------------------------------------------------------------------------------------------------ |
| `id`              | String | Unique identifier for the job.                                                                                                  |
| `user_id`         | String | The user who submitted the job.                                                                                                 |
| `job_type`        | String | Type of job: `IMAGE_GENERATION`, `VIDEO_GENERATION`, `MUSIC_GENERATION`, `SPEECH_SINGLE_SPEAKER_GENERATION`, `VIDEO_STITCHING`. |
| `status`          | String | Current status: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`.                                                                    |
| `created_at`      | String | ISO 8601 timestamp of creation.                                                                                                 |
| `updated_at`      | String | ISO 8601 timestamp of last update.                                                                                              |
| `job_input`       | Object | Copy of the parameters passed to the generation request.                                                                        |
| `result_asset_id` | String | (When COMPLETED) ID of the generated asset.                                                                                     |
| `result_asset`    | Asset  | (When COMPLETED) The full asset object.                                                                                         |
| `error_message`   | String | (When FAILED) Description of the error.                                                                                         |

#### Generate Music (Lyria)

Generates audio using Google's Lyria model.

- **Endpoint**: `POST /users/{user_id}/media:generate-music`
- **Body**: `GenerateMusicRequest`
  ```json
  {
    "prompt": "Upbeat jazz with a piano solo",
    "file_name": "jazz_track.mp3",
    "model": "lyria-002",
    "negative_prompt": "drums"
  }
  ```

#### Generate Image (Imagen)

Generates images using the Imagen model family.

- **Endpoint**: `POST /users/{user_id}/media:generate-image-with-imagen`
- **Body**: `GenerateImageWithImagenRequest`
  ```json
  {
    "prompt": "A futuristic city",
    "aspect_ratio": "16:9",
    "model": "imagen-4.0-generate-001",
    "file_name": "city.png"
  }
  ```

#### Generate Image (Gemini)

Generates images using the Gemini model. Supports reference images for style/subject consistency.

- **Endpoint**: `POST /users/{user_id}/media:generate-image-with-gemini`
- **Body**: `GenerateImageWithGeminiRequest`

  ```json
  {
    "prompt": "A cat in the style of this painting",
    "aspect_ratio": "1:1",
    "model": "gemini-2.5-flash-image", // Default is "gemini-2.5-flash-image" or "gemini-3-pro-image-preview"
    "file_name": "cat_art.png",
    "reference_image_filenames": ["painting.png"]
  }
  ```

  - `reference_image_filenames`: Must match `file_name` of existing user assets.

**Parameters:**
| Field | Type | Description |
| :--- | :--- | :--- |
| `prompt` | String | The text prompt describing the desired image. |
| `aspect_ratio` | String | The desired aspect ratio of the image (e.g., "1:1", "16:9"). |
| `model` | String | The Gemini model to use for image generation. Valid values: `gemini-2.5-flash-image`, `gemini-3-pro-image-preview`. Default is `gemini-2.5-flash-image`. |
| `file_name` | String | The desired filename for the generated image asset. |
| `reference_image_filenames` | List[String] | Optional. List of filenames of existing assets to use as reference images. |

#### Generate Video (Veo)

Generates video using the Veo model. Supports text-to-video and image-to-video.

- **Endpoint**: `POST /users/{user_id}/media:generate-video`
- **Body**: `GenerateVideoRequest`
  ```json
  {
    "prompt": "A drone shot of a mountain",
    "file_name": "mountain.mp4",
    "model": "veo-3.1-generate-preview",
    "duration_seconds": 6,
    "aspect_ratio": "16:9",
    "first_frame_filename": "start_image.png" // Optional: Image-to-Video
  }
  ```

#### Generate Speech (TTS)

Generates speech from text using Gemini TTS.

- **Endpoint**: `POST /users/{user_id}/media:generate-speech-single-speaker`
- **Body**: `GenerateSpeechSingleSpeakerRequest`
  ```json
  {
    "prompt": "Speak excitedly",
    "text": "Hello world!",
    "voice_name": "Aoede",
    "model": "gemini-2.5-flash-preview-tts",
    "file_name": "hello.mp3"
  }
  ```

---

### 3.3. Canvases

Canvases represent structured content. A canvas can contain:

1.  **HTML Content**: For visual layouts and storyboards.
2.  **Video Timeline**: A structured definition of a video sequence (clips, transitions, audio) used for stitching.

#### List Canvases

- **Endpoint**: `GET /users/{user_id}/canvases`
- **Response**: List of `CanvasInfo`.

```json
[
  {
    "id": "canvas-uuid",
    "title": "My Project",
    "user_id": "user-123",
    "canvas_type": "video_timeline"
  }
]
```

| Field         | Type   | Description                        |
| :------------ | :----- | :--------------------------------- |
| `id`          | String | Unique identifier for the canvas.  |
| `title`       | String | Title of the canvas.               |
| `user_id`     | String | Owner ID.                          |
| `canvas_type` | String | Either `video_timeline` or `html`. |

#### Get Canvas

- **Endpoint**: `GET /users/{user_id}/canvases/{canvas_id}`
- **Response**: Full `Canvas` object.

```json
{
  "id": "canvas-uuid",
  "title": "My Project",
  "user_id": "user-123",
  "video_timeline": { ... }, // See VideoTimeline model
  "html": {
      "content": "<html>...</html>",
      "asset_ids": ["asset-id-1", "asset-id-2"]
  }
}
```

| Field            | Type   | Description                                                                  |
| :--------------- | :----- | :--------------------------------------------------------------------------- |
| `id`             | String | Unique identifier.                                                           |
| `title`          | String | Title of the canvas.                                                         |
| `user_id`        | String | Owner ID.                                                                    |
| `video_timeline` | Object | Optional. Contains the video editing structure. See **VideoTimeline** model. |
| `html`           | Object | Optional. Contains raw HTML content and referenced asset IDs.                |

#### Update Canvas

Update the title, HTML content, or video timeline.

- **Endpoint**: `PATCH /users/{user_id}/canvases/{canvas_id}`
- **Body**: `CanvasUpdate`
  ```json
  {
    "title": "My New Project",
    "html": { "content": "<html>...</html>" },
    "video_timeline": { ... }
  }
  ```

#### View Canvas (HTML Render)

Renders the HTML content of a canvas.

- **Endpoint**: `GET /users/{user_id}/canvases/{canvas_id}/view`
- **Logic**:
  - Parses the stored HTML.
  - **Asset Resolution**: Finds tags like `<img src="asset://my_image.png">`.
  - Replaces them with the actual API URL: `/users/{user_id}/assets/{asset_id}/view`.
- **Response**: `text/html`

---

### 3.4. Video Stitching (Async Job)

Compiles a `VideoTimeline` defined in a Canvas into a single video file using FFmpeg.

#### Stitch Video

- **Endpoint**: `POST /users/{user_id}/canvases/{canvas_id}:stitch`
- **Logic**:
  - Validates the canvas has a `video_timeline`.
  - Submits a background job to:
    1.  Download referenced assets.
    2.  Generate placeholder clips for missing assets.
    3.  Apply trims, transitions, and audio mixing via FFmpeg.
    4.  Save the result as a new Asset.
- **Response**: `Job` object (`202 Accepted`). See **Media Generation** section for `Job` response structure.

---

### 3.5. Jobs

Endpoints to track the status of asynchronous operations (Media Generation and Video Stitching).

#### Get Job

- **Endpoint**: `GET /users/{user_id}/jobs/{job_id}`
- **Response**: `Job` object.

#### List Jobs

- **Endpoint**: `GET /users/{user_id}/jobs`
- **Query Params**: `status`, `limit`, `offset`.
- **Response**: List of `Job` objects.

---

### 3.6. Sessions

Endpoints to manage and retrieve user sessions.

#### List Sessions

Retrieves a list of all sessions associated with a specific user across all applications.

- **Endpoint**: `GET /users/{user_id}/sessions`
- **Response**: List of `Session` objects.
- **Filtering Logic**: Sessions with IDs starting with `eval-` (evaluation sessions) are automatically filtered out from the response.

```json
[
  {
    "id": "session-uuid",
    "app_name": "my-app",
    "user_id": "user-123",
    "state": { ... },
    "events": [ ... ],
    "last_update_time": 1732752000.0
  }
]
```

| Field              | Type         | Description                                         |
| :----------------- | :----------- | :-------------------------------------------------- |
| `id`               | String       | Unique identifier for the session.                  |
| `app_name`         | String       | The name of the application the session belongs to. |
| `user_id`          | String       | The ID of the user.                                 |
| `state`            | Object       | The current state of the session.                   |
| `events`           | List[Object] | A list of events that occurred in the session.      |
| `last_update_time` | Float        | Timestamp of the last update.                       |

---

## 4. Detailed Data Models

### AssetVersion

Represents a specific historical version of an asset.

```json
{
  "asset_id": "uuid",
  "version_number": 1,
  "gcs_uri": "gs://bucket/path",
  "create_time": "2023-10-27T10:00:00Z",
  "image_generate_config": {
    "model": "imagen-4.0-generate-001",
    "prompt": "A city",
    "aspect_ratio": "16:9"
  },
  "music_generate_config": null,
  "video_generate_config": null,
  "speech_generate_config": null,
  "duration_seconds": 5.0
}
```

| Field               | Type    | Description                                                                                                    |
| :------------------ | :------ | :------------------------------------------------------------------------------------------------------------- |
| `asset_id`          | String  | ID of the parent asset.                                                                                        |
| `version_number`    | Integer | The version number (1, 2, 3...).                                                                               |
| `gcs_uri`           | String  | Google Cloud Storage URI of the file.                                                                          |
| `create_time`       | String  | Timestamp when this version was created.                                                                       |
| `*_generate_config` | Object  | Metadata about the AI model/prompt used to generate this version. Null if uploaded manually or not applicable. |
| `duration_seconds`  | Float   | The duration of the media in seconds, if applicable (e.g., for video or audio).                                |

### VideoTimeline

Defines the structure for video stitching.

```json
{
  "title": "My Movie",
  "video_clips": [
    {
      "asset_id": "uuid",
      "trim": { "offset_seconds": 0, "duration_seconds": 5 },
      "volume": 1.0,
      "placeholder": "Scene description if missing"
    }
  ],
  "transitions": [{ "type": "fade", "duration_seconds": 1.0 }],
  "audio_clips": [
    {
      "asset_id": "uuid",
      "start_at": { "video_clip_index": 0, "offset_seconds": 0 },
      "volume": 0.8,
      "fade_in_duration_seconds": 2.0
    }
  ],
  "transition_in": null,
  "transition_out": { "type": "fade", "duration_seconds": 1.0 }
}
```

| Field               | Type   | Description                                                             |
| :------------------ | :----- | :---------------------------------------------------------------------- |
| `title`             | String | Title of the timeline.                                                  |
| `video_clips`       | List   | Sequence of video clips.                                                |
| `transitions`       | List   | Transitions between video clips. Must be length `len(video_clips) - 1`. |
| `audio_clips`       | List   | Background audio or voiceovers.                                         |
| `transition_in/out` | Object | Optional fade in/out effects for the whole video.                       |

### VideoClip

A single segment in the video track.

| Field         | Type   | Description                                                                                      |
| :------------ | :----- | :----------------------------------------------------------------------------------------------- |
| `asset_id`    | String | ID of the video asset. Null for placeholder.                                                     |
| `trim`        | Object | `{ "offset_seconds": float, "duration_seconds": float }`. Selects a portion of the source asset. |
| `volume`      | Float  | Audio volume multiplier (1.0 = normal).                                                          |
| `placeholder` | String | Text to display if asset is missing.                                                             |

### AudioClip

A segment in the audio track.

| Field         | Type   | Description                                                                                                      |
| :------------ | :----- | :--------------------------------------------------------------------------------------------------------------- |
| `asset_id`    | String | ID of the audio asset.                                                                                           |
| `start_at`    | Object | `{ "video_clip_index": int, "offset_seconds": float }`. Anchors audio to a specific point in the video sequence. |
| `trim`        | Object | Selects a portion of the source asset.                                                                           |
| `volume`      | Float  | Audio volume multiplier.                                                                                         |
| `fade_in/out` | Float  | Duration of fade effects in seconds.                                                                             |
