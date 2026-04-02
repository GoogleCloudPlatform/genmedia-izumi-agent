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
import subprocess
import json
import argparse
from pathlib import Path

# --- Configuration ---
TERRAFORM_DIR = Path(__file__).parent.parent / "deployment" / "terraform"
PROJECT_ROOT = Path(__file__).parent.parent

# --- Helper Functions ---


def run_command(command, cwd, env=None, suppress_output=False):
    """Runs a command and handles errors."""
    print(f"\n▶️ Running command: '{' '.join(command)}' in {cwd}")
    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            text=True,
            capture_output=suppress_output,
            env=env,
        )
        if suppress_output:
            return process.stdout.strip()
        return process
    except FileNotFoundError:
        print(
            f"❌ Error: Command '{command[0]}' not found. Is it installed and in your PATH?"
        )
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running command: '{' '.join(command)}'")
        if not suppress_output:
            # The output is already streamed to stdout/stderr
            pass
        else:
            print(e.stdout)
            print(e.stderr, file=sys.stderr)
        sys.exit(1)


def prompt_user(prompt_text, default=None):
    """
    Prompts the user for input.
    If a default value is provided, it's displayed and used if the user enters nothing.
    If no default is provided, the user is prompted repeatedly until a non-empty value is entered.
    """
    if default is not None:
        response = input(f"❓ {prompt_text} (default: {default}): ").strip()
        return response if response else default
    else:
        while True:
            response = input(f"❓ {prompt_text}: ").strip()
            if response:
                return response
            print("❌ This field is required. Please enter a value.")


def confirm_action(prompt):
    """Asks for user confirmation."""
    return prompt_user(f"{prompt} [y/N]").lower() == "y"


def get_current_gcloud_user_email():
    """Fetches the email of the currently active gcloud user."""
    try:
        active_account = run_command(
            [
                "gcloud",
                "auth",
                "list",
                "--filter=status:ACTIVE",
                "--format=value(account)",
            ],
            cwd=PROJECT_ROOT,
            suppress_output=True,
        )
        if not active_account:
            raise ValueError("No active gcloud account found.")
        return active_account
    except Exception as e:
        raise ValueError(f"Failed to get active gcloud user: {e}")


# --- Core Logic ---


def run_dependency_checks():
    """Checks for required command-line tools and authentication."""
    print("--- Running Dependency Checks ---")

    run_command(["gcloud", "--version"], cwd=PROJECT_ROOT)

    # Check gcloud auth
    try:
        active_account = get_current_gcloud_user_email()
        print(f"✅ gcloud user authenticated as: {active_account}")
    except ValueError as e:
        print(f"❌ gcloud authentication check failed: {e}", file=sys.stderr)
        print(
            "Please run `gcloud auth login` and `gcloud auth application-default login`.",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(
            f"❌ An unexpected error occurred during gcloud authentication check: {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Check for firestore emulator
    components = run_command(
        ["gcloud", "components", "list", "--format=json"],
        cwd=PROJECT_ROOT,
        suppress_output=True,
    )
    if "cloud-firestore-emulator" not in components:
        print("❌ Firestore emulator component not found.", file=sys.stderr)
        print(
            "Please run `gcloud components install cloud-firestore-emulator`.",
            file=sys.stderr,
        )
        sys.exit(1)
    print("✅ All dependencies are installed and configured.")


def setup_local_environment():
    """Guides the user through setting up a local environment."""
    print("\n--- Setting up Local Environment (`.env.local`) ---")

    project_id = prompt_user(
        "Enter the Google Cloud Project ID for this environment (e.g., my-gcp-project-123)"
    )
    bucket_name = prompt_user(
        f"Enter the desired GCS bucket name for assets storage (e.g., my-local-assets)"
    )
    location = prompt_user(
        "Enter the desired Google Cloud location for your services",
        default="us-central1",
    )
    firestore_db = prompt_user(
        "Enter the Firestore Database ID (leave blank for standard '(default)')",
        default="",
    )

    # Verify project access
    print(f"Verifying access to project '{project_id}'...")
    run_command(
        ["gcloud", "projects", "describe", project_id],
        cwd=PROJECT_ROOT,
        suppress_output=True,
    )
    print("✅ Project access confirmed.")

    # Check and create bucket
    try:
        run_command(
            ["gcloud", "storage", "buckets", "describe", f"gs://{bucket_name}"],
            cwd=PROJECT_ROOT,
            suppress_output=True,
        )
        print(f"✅ GCS bucket 'gs://{bucket_name}' already exists.")
    except SystemExit:  # gcloud command will exit(1) if bucket not found
        print(f"Bucket 'gs://{bucket_name}' not found.")
        if confirm_action("Create it now?"):
            run_command(
                [
                    "gcloud",
                    "storage",
                    "buckets",
                    "create",
                    f"gs://{bucket_name}",
                    "--project",
                    project_id,
                    f"--location={location}",
                ],
                cwd=PROJECT_ROOT,
            )
            print(f"✅ Bucket 'gs://{bucket_name}' created.")
        else:
            print(
                "Aborting. Please create the bucket manually and re-run the script.",
                file=sys.stderr,
            )
            sys.exit(1)

    env_content = f"""# Generated by setup_gcp_project.py for local development
GOOGLE_GENAI_USE_VERTEXAI=True
GOOGLE_CLOUD_PROJECT={project_id}
GOOGLE_CLOUD_LOCATION={location}
ASSET_SERVICE_GCS_BUCKET={bucket_name}
# Leave blank to use your project's default database (Required for cloud connection!). 
# Note: If connecting to live GCP (no emulator), create the database in the Cloud Console first!
# If you ran cloud setup before, set it to your named database (e.g., genmedia-agents-dev)
FIRESTORE_DATABASE_ID={firestore_db}
"""
    env_file = PROJECT_ROOT / "demos" / "backend" / ".env.local"
    if env_file.exists() and not confirm_action(
        f".env.local already exists. Overwrite?"
    ):
        print("Aborting.", file=sys.stderr)
        sys.exit(1)

    env_file.write_text(env_content)
    print(f"✅ Successfully created/updated `.env.local`.")


def setup_cloud_environment(app_env):
    """Orchestrates Terraform to provision a cloud environment."""
    print(f"\n--- Setting up Cloud Environment: {app_env} ---")

    # 1. Collect all variables from user first
    project_id = prompt_user(
        "Enter the Google Cloud Project ID where resources will be deployed (GOOGLE_CLOUD_PROJECT, e.g., my-gcp-project-123)"
    )
    asset_bucket = prompt_user(
        f"Enter the desired GCS bucket name for storing assets and Terraform state in the {app_env} environment (ASSET_SERVICE_GCS_BUCKET)",
        default=f"{project_id}-genmedia-agents-assets-{app_env}",
    )
    cloud_run_service_name = prompt_user(
        f"Enter the desired name for the Cloud Run service in the {app_env} environment (CLOUD_RUN_SERVICE_NAME)",
        default=f"genmedia-agents-backend-{app_env}",
    )
    location = prompt_user(
        "Enter the Google Cloud region where your services will be deployed (GOOGLE_CLOUD_LOCATION)",
        default="us-central1",
    )

    # Get current gcloud user for IAP default
    try:
        current_gcloud_user = get_current_gcloud_user_email()
    except ValueError:
        current_gcloud_user = None  # No default if user not found
        print(
            "⚠️ Could not determine current gcloud user for IAP default. Please enter manually.",
            file=sys.stderr,
        )

    iap_user_email = prompt_user(
        "Enter the email address of the user to grant access to GenMedia Agent backend on Cloud Run via IAP",
        default=current_gcloud_user,
    )

    # ARTIFACT_SERVICE_GCS_BUCKET is the same as ASSET_SERVICE_GCS_BUCKET
    artifact_bucket = asset_bucket
    tf_state_bucket = asset_bucket

    # 2. Configure and create backend bucket
    print(
        f"\nℹ️ Terraform state will be stored in the asset bucket: gs://{tf_state_bucket}"
    )
    try:
        run_command(
            ["gcloud", "storage", "buckets", "describe", f"gs://{tf_state_bucket}"],
            cwd=PROJECT_ROOT,
            suppress_output=True,
        )
        print(f"✅ Bucket 'gs://{tf_state_bucket}' already exists.")
        if not confirm_action(
            "Do you want to use this existing bucket for assets and Terraform state?"
        ):
            print("Aborting.", file=sys.stderr)
            sys.exit(1)
    except SystemExit:
        print(f"Bucket 'gs://{tf_state_bucket}' not found. Creating it now...")
        run_command(
            [
                "gcloud",
                "storage",
                "buckets",
                "create",
                f"gs://{tf_state_bucket}",
                "--project",
                project_id,
                f"--location={location}",
            ],
            cwd=PROJECT_ROOT,
        )
        print(f"✅ Bucket 'gs://{tf_state_bucket}' created.")

    backend_tf_path = TERRAFORM_DIR / "backend.tf"
    backend_tf_path.write_text(f"""
terraform {{
  backend "gcs" {{
    bucket  = "{tf_state_bucket}"
    prefix  = "terraform/state/{app_env}"
  }}
}}
""")
    print("✅ Terraform backend configured.")

    # 3. Generate Firestore Config
    firestore_db = f"genmedia-agents-{app_env}"
    generate_firestore_config()

    # 4. Run Terraform
    tf_vars = {
        "TF_VAR_google_cloud_project": project_id,
        "TF_VAR_google_cloud_location": location,
        "TF_VAR_asset_service_gcs_bucket": asset_bucket,
        "TF_VAR_artifact_service_gcs_bucket": artifact_bucket,
        "TF_VAR_cloud_run_service_name": cloud_run_service_name,
        "TF_VAR_firestore_database_id": firestore_db,
        "TF_VAR_app_env": app_env,
        "TF_VAR_iap_allowed_user_email": f"user:{iap_user_email}",
    }

    run_command(["terraform", "init", "-reconfigure"], cwd=TERRAFORM_DIR)
    run_command(
        ["terraform", "apply", "-auto-approve"],
        cwd=TERRAFORM_DIR,
        env={**os.environ, **tf_vars},
    )

    # 5. Get Outputs and write .env file
    print("Fetching outputs from Terraform...")
    outputs_json = run_command(
        ["terraform", "output", "-json"], cwd=TERRAFORM_DIR, suppress_output=True
    )
    outputs = json.loads(outputs_json)

    # 6. Grant Service Account User role to the current gcloud user
    print("\n--- Granting permissions to user ---")
    try:
        cloud_run_sa_email = outputs["CLOUD_RUN_SERVICE_ACCOUNT_EMAIL"]["value"]
        current_user = run_command(
            [
                "gcloud",
                "auth",
                "list",
                "--filter=status:ACTIVE",
                "--format=value(account)",
            ],
            cwd=PROJECT_ROOT,
            suppress_output=True,
        )
        if not current_user:
            print(
                "⚠️ Could not determine current gcloud user. Skipping permission grant.",
                file=sys.stderr,
            )
        else:
            print(
                f"Granting 'Service Account User' role on '{cloud_run_sa_email}' to user '{current_user}'..."
            )
            run_command(
                [
                    "gcloud",
                    "iam",
                    "service-accounts",
                    "add-iam-policy-binding",
                    cloud_run_sa_email,
                    f"--member=user:{current_user}",
                    "--role=roles/iam.serviceAccountUser",
                    f"--project={project_id}",
                ],
                cwd=PROJECT_ROOT,
            )
            print("✅ Permission granted.")
    except KeyError:
        print(
            "⚠️ 'CLOUD_RUN_SERVICE_ACCOUNT_EMAIL' not found in Terraform outputs. Skipping permission grant.",
            file=sys.stderr,
        )
    except Exception as e:
        print(f"❌ An error occurred while granting permissions: {e}", file=sys.stderr)
        print("Continuing with script...", file=sys.stderr)

    env_content = f"# Generated by setup_gcp_project.py for {app_env} environment\n"
    env_content += "GOOGLE_GENAI_USE_VERTEXAI=True\n"
    env_content += f"GOOGLE_CLOUD_PROJECT={project_id}\n"
    env_content += f"GOOGLE_CLOUD_LOCATION={location}\n"
    env_content += f"ARTIFACT_SERVICE_GCS_BUCKET={outputs['ARTIFACT_SERVICE_GCS_BUCKET']['value']}\n"
    env_content += (
        f"ASSET_SERVICE_GCS_BUCKET={outputs['ASSET_SERVICE_GCS_BUCKET']['value']}\n"
    )
    env_content += f"FIRESTORE_DATABASE_ID={firestore_db}\n"
    env_content += f"CLOUD_RUN_SERVICE_NAME={cloud_run_service_name}\n"
    env_content += f"TERRAFORM_STATE_GCS_BUCKET={tf_state_bucket}\n"
    if "CLOUD_RUN_SERVICE_ACCOUNT_EMAIL" in outputs:
        env_content += f"CLOUD_RUN_SERVICE_ACCOUNT_EMAIL={outputs['CLOUD_RUN_SERVICE_ACCOUNT_EMAIL']['value']}\n"
    if "CLOUD_BUILD_SERVICE_ACCOUNT_EMAIL" in outputs:
        env_content += f"CLOUD_BUILD_SERVICE_ACCOUNT_EMAIL={outputs['CLOUD_BUILD_SERVICE_ACCOUNT_EMAIL']['value']}\n"
    # Assuming CLOUD_RUN_SERVICE_URL is an output
    if "CLOUD_RUN_SERVICE_URL" in outputs:
        env_content += (
            f"CLOUD_RUN_SERVICE_URL={outputs['CLOUD_RUN_SERVICE_URL']['value']}\n"
        )

    env_file = PROJECT_ROOT / "demos" / "backend" / f".env.{app_env}"
    env_file.write_text(env_content)
    print(f"✅ Successfully created `.env.{app_env}` with Terraform outputs.")

    # 7. Print success message
    print("\n" + "=" * 80)
    print("✅ Infrastructure successfully provisioned!")
    print("=" * 80)
    print(f"\n🚀 The Cloud Run service '{cloud_run_service_name}' has been deployed.")
    if "CLOUD_RUN_SERVICE_URL" in outputs:
        print(f"   URL: {outputs['CLOUD_RUN_SERVICE_URL']['value']}")
    print(
        f"\n🔐 Access has been granted to '{iap_user_email}' via Identity-Aware Proxy (IAP). Please allow a few minutes for this to take effect."
    )
    print(
        "\nTo grant access to additional users, you can use either the Cloud Console or the gcloud CLI:"
    )
    print("\n1. Using Google Cloud Console:")
    print(
        f"   - Go to the Cloud Run service security settings: https://console.cloud.google.com/run/detail/{location}/{cloud_run_service_name}/security?project={project_id}"
    )
    print(
        "   - In the 'Authentication' > Require authentication > Identity Aware Proxy (IAP) section, click 'Edit policy'."
    )
    print("   - Add the email addresses of the users and click 'Save', then 'Save'.")
    print("\n2. Using gcloud CLI:")
    print(
        "   Run the following command, replacing 'user@example.com' with the desired user's email."
    )
    print(
        "   For more options on the '--member' flag (e.g., granting access to Google Groups, domains, or all users),"
    )
    print(
        "   refer to the gcloud documentation: https://cloud.google.com/sdk/gcloud/reference/beta/projects/add-iam-policy-binding#--member"
    )
    print("\n   gcloud beta iap web add-iam-policy-binding \\")
    print(f"     --project={project_id} \\")
    print(f"     --service={cloud_run_service_name} \\")
    print("     --resource-type=cloud-run \\")
    print(f"     --region={location} \\")
    print("     --member=user:user@example.com \\")
    print("     --role=roles/iap.httpsResourceAccessor")
    print("\n" + "=" * 80)


def destroy_cloud_environment(app_env):
    """Destroys the cloud environment provisioned by Terraform."""
    print(f"\n--- Destroying Cloud Environment: {app_env} ---")

    env_file = PROJECT_ROOT / "demos" / "backend" / f".env.{app_env}"
    if not env_file.exists():
        print(
            f"❌ Error: .env.{app_env} not found. Cannot destroy environment without its configuration.",
            file=sys.stderr,
        )
        print(f"Please ensure the file exists at: {env_file}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading configuration from {env_file}...")
    env_vars = {}
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                # Use partition to handle values that might contain '='
                key, _, value = line.partition("=")
                env_vars[key.strip()] = value.strip()

    project_id = env_vars.get("GOOGLE_CLOUD_PROJECT")
    location = env_vars.get("GOOGLE_CLOUD_LOCATION")
    asset_bucket = env_vars.get("ASSET_SERVICE_GCS_BUCKET")
    artifact_bucket = env_vars.get(
        "ARTIFACT_SERVICE_GCS_BUCKET", asset_bucket
    )  # Fallback for older .env files
    cloud_run_service_name = env_vars.get("CLOUD_RUN_SERVICE_NAME")
    firestore_db = env_vars.get("FIRESTORE_DATABASE_ID")
    tf_state_bucket = env_vars.get(
        "TERRAFORM_STATE_GCS_BUCKET", asset_bucket
    )  # Fallback for older .env files

    if not all(
        [
            project_id,
            location,
            asset_bucket,
            cloud_run_service_name,
            firestore_db,
            tf_state_bucket,
        ]
    ):
        print(
            f"❌ Error: Missing one or more required variables in .env.{app_env}.",
            file=sys.stderr,
        )
        print(
            "   Required: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, ASSET_SERVICE_GCS_BUCKET, CLOUD_RUN_SERVICE_NAME, FIRESTORE_DATABASE_ID, TERRAFORM_STATE_GCS_BUCKET",
            file=sys.stderr,
        )
        sys.exit(1)

    if not confirm_action(
        f"🛑 Are you absolutely sure you want to DESTROY ALL resources for environment '{app_env}' in project '{project_id}'? This action is irreversible."
    ):
        print("Destruction aborted by user.", file=sys.stderr)
        sys.exit(0)

    # 1. Configure backend
    backend_tf_path = TERRAFORM_DIR / "backend.tf"
    backend_tf_path.write_text(f"""
terraform {{
  backend "gcs" {{
    bucket  = "{tf_state_bucket}"
    prefix  = "terraform/state/{app_env}"
  }}
}}
""")
    print("✅ Terraform backend configured for destruction.")

    # 2. Generate Firestore config
    generate_firestore_config()

    # 3. Prepare Terraform variables
    tf_vars = {
        "TF_VAR_google_cloud_project": project_id,
        "TF_VAR_google_cloud_location": location,
        "TF_VAR_asset_service_gcs_bucket": asset_bucket,
        "TF_VAR_artifact_service_gcs_bucket": artifact_bucket,
        "TF_VAR_cloud_run_service_name": cloud_run_service_name,
        "TF_VAR_firestore_database_id": firestore_db,
        "TF_VAR_app_env": app_env,
        "TF_VAR_iap_allowed_user_email": "user:placeholder@example.com",
    }

    # 4. Run Terraform commands
    run_command(["terraform", "init", "-reconfigure"], cwd=TERRAFORM_DIR)
    run_command(
        ["terraform", "destroy", "-auto-approve"],
        cwd=TERRAFORM_DIR,
        env={**os.environ, **tf_vars},
    )

    print("\n" + "=" * 80)
    print(f"✅ Cloud environment '{app_env}' successfully destroyed!")
    print("=" * 80)


def generate_firestore_config():
    """Generates Terraform configuration for Firestore from JSON and rules files."""
    print("--- Generating Firestore Config ---")
    generated_tf_path = TERRAFORM_DIR / "firestore_generated.tf"

    content = "# AUTO-GENERATED by setup_gcp_project.py - DO NOT EDIT\n\n"

    # 1. Generate Index Resources from JSON
    all_indexes = []
    seen_indexes = set()

    def load_and_dedupe_indexes(file_path):
        if file_path.exists():
            with open(file_path, "r") as f:
                try:
                    data = json.load(f)
                    for index in data.get("indexes", []):
                        index_repr = json.dumps(index, sort_keys=True)
                        if index_repr not in seen_indexes:
                            all_indexes.append(index)
                            seen_indexes.add(index_repr)
                except json.JSONDecodeError:
                    print(
                        f"⚠️ Warning: Could not parse {file_path}. It might be empty or malformed. Skipping."
                    )

    # Load base indexes from mediagent_kit
    load_and_dedupe_indexes(PROJECT_ROOT / "mediagent_kit" / "firestore.indexes.json")

    # Load and merge project-specific indexes if they exist
    project_indexes_path = PROJECT_ROOT / "demos" / "backend" / "firestore.indexes.json"
    if project_indexes_path.exists():
        print("Found project-specific firestore.indexes.json, merging indexes.")
        load_and_dedupe_indexes(project_indexes_path)

    print("\n--- Final list of Firestore indexes to be applied ---")
    print(json.dumps(all_indexes, indent=2))
    print("-----------------------------------------------------\n")

    for i, index in enumerate(all_indexes):
        collection = index["collectionGroup"]
        query_scope = index["queryScope"]

        # Create a unique but descriptive resource name
        resource_name = f"index_{collection.lower()}_{i}"

        content += f'resource "google_firestore_index" "{resource_name}" {{\n'
        content += f'  collection = "{collection}"\n'
        content += f'  query_scope = "{query_scope}"\n'
        content += f"  database = var.firestore_database_id\n"
        content += f"  project = var.google_cloud_project\n"
        content += "  depends_on = [google_firestore_database.database]\n"

        for field in index.get("fields", []):
            field_path = field["fieldPath"]
            order = field.get("order")
            array_config = field.get("arrayConfig")

            content += "  fields {\n"
            content += f'    field_path = "{field_path}"\n'
            if order:
                content += f'    order = "{order}"\n'
            if array_config:
                content += f'    array_config = "{array_config}"\n'
            content += "  }\n"

        content += "}\n\n"

    # 2. Generate Ruleset Resource from rules file
    rules_path = PROJECT_ROOT / "demos" / "backend" / "firestore.rules"
    if not rules_path.is_file():
        print(
            "❌ Error: `firestore.rules` not found in the project root. This file is required.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Using project-specific `firestore.rules`.")
    rules_content = rules_path.read_text()
    # Use json.dumps to safely escape the string for HCL
    escaped_rules_content = json.dumps(rules_content)

    content += f"""
resource "google_firebaserules_ruleset" "ruleset" {{
  project = var.google_cloud_project
  source {{
    files {{
      content = {escaped_rules_content}
      name    = "firestore.rules"
    }}
  }}
}}

resource "google_firebaserules_release" "release" {{
  name          = "cloud.firestore/${{var.firestore_database_id}}" # This specific name is required for Firestore
  ruleset_name  = google_firebaserules_ruleset.ruleset.name
  project       = var.google_cloud_project

  # Ensure the database exists before trying to apply rules to it.
  depends_on = [google_firestore_database.database]
}}
"""
    generated_tf_path.write_text(content)
    print(f"✅ Generated Firestore configuration at {generated_tf_path}")


def cleanup():
    """Removes temporary generated files."""
    print("--- Cleaning up temporary files ---")
    (TERRAFORM_DIR / "backend.tf").unlink(missing_ok=True)
    (TERRAFORM_DIR / "firestore_generated.tf").unlink(missing_ok=True)
    print("✅ Cleanup complete.")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Manage GCP project for GenMedia Agent Demos."
    )
    parser.add_argument(
        "--app_env",
        default="local",
        help="The application environment to manage (e.g., local, dev, prod). Defaults to 'local'.",
    )
    parser.add_argument(
        "--destroy",
        action="store_true",
        help="Destroy the resources for the specified cloud environment. Use with --app_env.",
    )
    args = parser.parse_args()
    app_env = args.app_env

    try:
        run_dependency_checks()

        if args.destroy:
            if app_env == "local":
                print(
                    "❌ Destroy command is not applicable for the 'local' environment.",
                    file=sys.stderr,
                )
                sys.exit(1)
            destroy_cloud_environment(app_env)
            # After destroying, we can offer to remove the .env file
            env_file_to_remove = PROJECT_ROOT / "demos" / "backend" / f".env.{app_env}"
            if env_file_to_remove.exists():
                if confirm_action(f"Do you want to remove the .env.{app_env} file?"):
                    env_file_to_remove.unlink()
                    print(f"✅ Removed {env_file_to_remove}.")
        elif app_env == "local":
            env_file = PROJECT_ROOT / "demos" / "backend" / ".env.local"
            if env_file.exists() and not confirm_action(
                f".env.local already exists. Overwrite?"
            ):
                print("Aborting.", file=sys.stderr)
                sys.exit(1)
            setup_local_environment()
        else:  # This is for cloud environment setup
            env_file = PROJECT_ROOT / "demos" / "backend" / f".env.{app_env}"
            if env_file.exists():
                if not confirm_action(
                    f"The .env.{app_env} file already exists. Do you want to overwrite it and re-run the setup?"
                ):
                    print("Aborting setup as per user request.", file=sys.stderr)
                    sys.exit(0)  # Exit gracefully
            setup_cloud_environment(app_env)

    except SystemExit as e:
        # A bit more context for the user
        if e.code != 0:
            print(f"\nScript aborted with exit code {e.code}.", file=sys.stderr)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
    finally:
        cleanup()


if __name__ == "__main__":
    main()
