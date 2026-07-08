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

import argparse
import os
import re
import shutil
import sys
import tempfile
from dotenv import load_dotenv
import google.auth
import vertexai
from vertexai import agent_engines
from vertexai.agent_engines import AdkApp


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Izumi Agent to Vertex AI Agent Platform"
    )
    parser.add_argument(
        "--project",
        default=None,
        help="GCP project ID (defaults to active configured gcloud project)",
    )
    parser.add_argument(
        "--location",
        default="us-central1",
        help="GCP region (defaults to us-central1)",
    )
    parser.add_argument(
        "--agent-name",
        default="izumi-ads-x-agent",
        help="Name of the reasoning engine / agent engine instance",
    )
    parser.add_argument(
        "--app_env",
        default="dev",
        help="Application environment configuration to target (dev, staging, prod)",
    )
    parser.add_argument(
        "--service-account",
        default=None,
        help="GCP Service Account email to execute the reasoning engine under",
    )
    args = parser.parse_args()

    # 1. Load configuration
    root_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    env_file = os.path.join(root_dir, f"demos/backend/.env.{args.app_env}")

    if os.path.exists(env_file):
        print(f"🔌 Loading environment parameters from: {env_file}")
        load_dotenv(env_file, override=True)
    else:
        print(f"⚠️ Warning: Env file not found at {env_file}. Relying on system env.")

    project_id = args.project or os.getenv("GOOGLE_CLOUD_PROJECT")
    location = args.location or os.getenv("GOOGLE_CLOUD_LOCATION") or "us-central1"
    staging_bucket = os.getenv("ASSET_SERVICE_GCS_BUCKET")

    if not project_id:
        try:
            _, project_id = google.auth.default()
        except Exception:
            pass

    if not project_id:
        print(
            "❌ Error: Active GCP Project ID not specified. Set GOOGLE_CLOUD_PROJECT or pass --project."
        )
        sys.exit(1)

    if not staging_bucket:
        # Derive default bucket name standard
        staging_bucket = f"{project_id}-agent-engine"
        print(
            f"ℹ️ ASSET_SERVICE_GCS_BUCKET not specified. Defaulting to: {staging_bucket}"
        )

    if not staging_bucket.startswith("gs://"):
        staging_bucket = f"gs://{staging_bucket}"

    print("\n" + "=" * 60)
    print(f"🤖 DEPLOYING IZUMI ADK AGENT TO VERTEX AI AGENT PLATFORM")
    print("=" * 60)
    print(f"• Target Project ID:  {project_id}")
    print(f"• Target Region:      {location}")
    print(f"• Agent Display Name: {args.agent_name}")
    print(f"• Staging Bucket:     {staging_bucket}")
    print(f"• Env Target:         .env.{args.app_env}")
    print("=" * 60 + "\n")

    # Initialize Vertex AI
    print("🚀 Initializing Vertex AI connection...")
    vertexai.init(project=project_id, location=location, staging_bucket=staging_bucket)

    # 2. Package Structuring and Bundle Isolation
    backend_src_path = os.path.join(root_dir, "demos/backend")
    kit_src_path = os.path.join(root_dir, "mediagent_kit")

    tmp_bundle_dir = tempfile.mkdtemp(prefix="agent_deploy_")
    print(f"📁 Packaging monorepo structure into isolated bundle: {tmp_bundle_dir}")

    try:
        for item in os.listdir(backend_src_path):
            s = os.path.join(backend_src_path, item)
            d = os.path.join(tmp_bundle_dir, item)
            # Skip local virtualenvs or metadata outputs
            if item in [
                ".venv",
                "__pycache__",
                ".pytest_cache",
                "dist",
                "deployment_metadata.json",
            ]:
                continue
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)

        shutil.copytree(kit_src_path, os.path.join(tmp_bundle_dir, "mediagent_kit"))

        # Inject PYTHONPATH and load root_agent
        sys.path.insert(0, tmp_bundle_dir)
        os.chdir(tmp_bundle_dir)

        print("🔑 Importing root_agent from ads_x package...")
        try:
            from ads_x.agent import root_agent
        except ImportError as e:
            print(f"❌ Error: Could not import root_agent from packaged bundle: {e}")
            sys.exit(1)

        # Wrap agent inside AdkApp with full tracing capabilities
        app_for_engine = AdkApp(
            agent=root_agent,
        )

        # 3. Define remote environment variables to pass to Agent Platform runtime
        env_vars = {
            "IZUMI_PROJECT_ID": project_id,
            "IZUMI_LOCATION": location,
            "ASSET_SERVICE_GCS_BUCKET": staging_bucket.replace("gs://", ""),
            "FIRESTORE_DATABASE_ID": os.getenv("FIRESTORE_DATABASE_ID", "(default)"),
            "USE_CREATIVE_STUDIO": os.getenv("USE_CREATIVE_STUDIO", "False"),
            "CREATIVE_STUDIO_BACKEND_URL": os.getenv("CREATIVE_STUDIO_BACKEND_URL", ""),
            "CREATIVE_STUDIO_FRONTEND_URL": os.getenv(
                "CREATIVE_STUDIO_FRONTEND_URL", ""
            ),
            "CREATIVE_STUDIO_USER_AUTH_TOKEN_KEY": os.getenv(
                "CREATIVE_STUDIO_USER_AUTH_TOKEN_KEY", ""
            ),
            "USE_AGENT_ENGINE": "True",
            "APP_ENV": "prod",
            "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
            "OTEL_SEMCONV_STABILITY_OPT_IN": "gen_ai_latest_experimental",
            "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "EVENT_ONLY",
            "GOOGLE_CLOUD_LOCATION": "global",
        }

        requirements = [
            "google-cloud-aiplatform[agent_engines,adk]==1.159.0",
            "google-adk==1.29.0",
            "opentelemetry-exporter-gcp-trace",
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

        extra_packages = ["ads_x", "mediagent_kit", "utils", "config.py"]

        agent_config = {
            "agent_engine": app_for_engine,
            "display_name": args.agent_name,
            "description": "GenMedia Izumi Ads-X creative agent deployed natively to GCP Agent Platform.",
            "requirements": requirements,
            "extra_packages": extra_packages,
            "env_vars": env_vars,
            "resource_limits": {"cpu": "4", "memory": "8Gi"},
        }
        if args.service_account:
            agent_config["service_account"] = args.service_account

        # 4. Deploy (Create or Update)
        existing_engines = list(
            agent_engines.list(filter=f'display_name="{args.agent_name}"')
        )
        if existing_engines:
            print(
                f"🔄 Updating existing reasoning engine instance: {args.agent_name} ({existing_engines[0].resource_name})"
            )
            remote_agent = existing_engines[0].update(**agent_config)
        else:
            print(f"✨ Creating new reasoning engine instance: {args.agent_name}")
            remote_agent = agent_engines.create(**agent_config)

        engine_id = remote_agent.resource_name.split("/")[-1]
        print("\n" + "=" * 60)
        print("🎉 DEPLOYMENT SUCCESSFUL!")
        print("=" * 60)
        print(f"• Resource Name: {remote_agent.resource_name}")
        print(f"• Engine ID:     {engine_id}")
        print(
            f"• Console Link:  https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/agent-engine?project={project_id}"
        )
        print("=" * 60 + "\n")

        # 5. Sync configurations back locally
        if os.path.exists(env_file):
            print(f"⚙️ Synchronizing engine ID back to local configuration: {env_file}")
            with open(env_file, "r") as f:
                env_content = f.read()

            # Replace or append USE_AGENT_ENGINE and AGENT_ENGINE_ID
            if "USE_AGENT_ENGINE=" in env_content:
                env_content = re.sub(
                    r"USE_AGENT_ENGINE=\w+", "USE_AGENT_ENGINE=True", env_content
                )
            else:
                env_content += "\nUSE_AGENT_ENGINE=True"

            if "AGENT_ENGINE_ID=" in env_content:
                env_content = re.sub(
                    r"AGENT_ENGINE_ID=[^\n]*",
                    f"AGENT_ENGINE_ID={engine_id}",
                    env_content,
                )
            else:
                env_content += f"\nAGENT_ENGINE_ID={engine_id}"

            with open(env_file, "w") as f:
                f.write(env_content)
            print("✅ Environment configuration successfully updated.")

    finally:
        os.chdir(root_dir)
        print(f"🧹 Removing packaging temporary folder: {tmp_bundle_dir}")
        shutil.rmtree(tmp_bundle_dir)


if __name__ == "__main__":
    main()
