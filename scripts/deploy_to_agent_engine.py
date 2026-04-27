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

import os
import sys
import shutil
import tempfile
from dotenv import load_dotenv
import vertexai
from vertexai import agent_engines

# 1. Load configuration
# Load from the absolute path to ensure it works after we change directory
root_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
env_file = os.path.join(root_dir, "demos/backend/.env.dev")
load_dotenv(env_file)

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")
STAGING_BUCKET = os.getenv("ASSET_SERVICE_GCS_BUCKET")

if not PROJECT_ID or not LOCATION or not STAGING_BUCKET:
    print("❌ Error: Missing required environment variables in .env.dev")
    sys.exit(1)

# Ensure staging_bucket starts with gs://
if not STAGING_BUCKET.startswith("gs://"):
    STAGING_BUCKET = f"gs://{STAGING_BUCKET}"

print(
    f"🚀 Initializing Vertex AI for project {PROJECT_ID} in {LOCATION} with bucket {STAGING_BUCKET}..."
)
vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

# 2. Setup path to import the agent
backend_src_path = os.path.join(root_dir, "demos/backend")
kit_src_path = os.path.join(root_dir, "mediagent_kit")

# We create a temporary directory to flatten the package structure for pickling and packaging.
# This ensures 'examples' and 'mediagent_kit' are top-level.
tmp_bundle_dir = tempfile.mkdtemp(prefix="agent_deploy_")
print(f"📁 Creating temporary deployment bundle at {tmp_bundle_dir}")

# Use copytree to move agents to the top level of the bundle
for item in os.listdir(backend_src_path):
    s = os.path.join(backend_src_path, item)
    d = os.path.join(tmp_bundle_dir, item)
    if os.path.isdir(s):
        shutil.copytree(s, d)
    else:
        shutil.copy2(s, d)

# Also copy mediagent_kit package directly
shutil.copytree(kit_src_path, os.path.join(tmp_bundle_dir, "mediagent_kit"))

# Add bundle to sys.path and change directory
sys.path.insert(0, tmp_bundle_dir)
os.chdir(tmp_bundle_dir)

# Import the agent object from the bundle
try:
    from ads_x.agent import root_agent
except ImportError as e:
    print(f"❌ Error importing agent from bundle: {e}")
    shutil.rmtree(tmp_bundle_dir)
    sys.exit(1)

# 3. Define requirements
requirements = [
    "google-cloud-aiplatform[agent_engines,adk] @ git+https://github.com/googleapis/python-aiplatform.git@main",
    "google-adk==1.20.0",
    "google-genai",
    "firebase-admin",
    "google-cloud-storage",
    "google-cloud-texttospeech",
    "fastapi",
    "uvicorn",
    "python-dotenv",
    "moviepy",
    "imageio-ffmpeg",
    "requests",
    "beautifulsoup4",
    "pydantic==2.12.3",
    "cloudpickle==3.1.2",
]

# 4. Define extra packages
extra_packages = [
    "ads_x",
    "mediagent_kit",
]

# 5. Define Environment Variables for the remote runtime
env_vars = {
    "IZUMI_PROJECT_ID": PROJECT_ID,
    "IZUMI_LOCATION": LOCATION,
    "ASSET_SERVICE_GCS_BUCKET": STAGING_BUCKET.replace("gs://", ""),
    "FIRESTORE_DATABASE_ID": os.getenv("FIRESTORE_DATABASE_ID", "(default)"),
    "APP_ENV": "prod",
}

print("📦 Packaging and deploying to Agent Engine...")

# 6. Deploy to Vertex AI Agent Engine
try:
    remote_agent = agent_engines.create(
        agent_engine=root_agent,
        display_name="Ads-X Agent",
        description="Cinematic Ad Generation Agent with Templated and Creative modes.",
        requirements=requirements,
        extra_packages=extra_packages,
        env_vars=env_vars,
        resource_limits={"cpu": "4", "memory": "8Gi"},
    )
    print(f"✅ Successfully deployed agent: {remote_agent.resource_name}")
    print(
        f"🔗 Agent Engine Resource: https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/agent-engine?project={PROJECT_ID}"
    )
finally:
    # Cleanup
    print(f"🧹 Cleaning up temporary bundle...")
    os.chdir(root_dir)
    shutil.rmtree(tmp_bundle_dir)
