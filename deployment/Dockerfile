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

# Stage 1: Build the frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/demos/frontend
COPY demos/frontend/package*.json ./
RUN npm install
COPY demos/frontend ./
RUN npm run build

# Stage 2: Build the backend
FROM python:3.12.9-slim
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.9.16 /uv /uvx /bin/

# Add a non-root user
RUN adduser --disabled-password --gecos "" myuser

# Install ffmpeg and git (required for git dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl git && apt-get clean && rm -rf /var/lib/apt/lists/*

# Add a build argument for the application environment
ARG APP_ENV=dev
# Set the application environment
ENV APP_ENV=${APP_ENV}

# Copy dependency definition and the local mediagent_kit dependency
COPY demos/backend/pyproject.toml /app/demos/backend/
COPY demos/backend/uv.lock /app/demos/backend/
COPY mediagent_kit /app/mediagent_kit
COPY pyproject.toml /app/
COPY uv.lock /app/

# Install dependencies (uv sync will look at ../.. as per tool.uv.sources in pyproject.toml)
WORKDIR /app/demos/backend
RUN uv sync --no-dev --no-cache

# Copy the rest of the application files
COPY demos/backend /app/demos/backend

# Copy frontend build artifacts
COPY --from=frontend-builder /app/demos/frontend/dist /app/demos/backend/dist

# Change ownership
RUN chown -R myuser:myuser /app

# Switch to the non-root user
USER myuser

# Set the Python path to include /app so mediagent_kit is importable
ENV PYTHONPATH "${PYTHONPATH}:/app"

# Run the application
CMD ["sh", "-c", "/app/demos/backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port $PORT"]