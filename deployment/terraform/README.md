<div align="center">
  <h1>Terraform Infrastructure Configuration 🌍</h1>
  <p><strong>Declarative Cloud Architecture for GenMedia Agents</strong></p>
</div>

---

## 📖 Overview

The `deployment/terraform` directory contains the Infrastructure as Code (IaC) definitions required to provision the Google Cloud Platform (GCP) resources for the GenMedia Izumi Agent workspace. 

These scripts are automatically orchestrated by the `scripts/setup_gcp_project.py` python wrapper to initialize variables seamlessly, but can also be run natively with `terraform init` and `terraform apply` by advanced users.

## 🧱 Module Architecture

Resources are logically separated across declarative definitions to maintain clean separation of concerns:

### Foundation & Identity
- **`providers.tf`**: Sets up the Google and Google-Beta providers.
- **`apis.tf`**: Automatically enables all necessary GCP Service APIs (Artifact Registry, Cloud Run, Vertex AI, Firestore, IAP).
- **`variables.tf`**: The parameter inputs (e.g. `project_id`, `location`, `app_env`).
- **`iam.tf`**: Provisions restricted least-privilege service accounts:
    - **Cloud Run Execution SA**: Granted access to Vertex AI, Cloud Storage, and Firestore.
    - **Cloud Build Trigger SA**: Granted access to deploy Cloud Run updates.

### Services & Storage
- **`artifact_registry.tf`**: Creates the Docker image repository where Cloud Build pushes the `deployment/Dockerfile` assets.
- **`cloud_run.tf`**: Sets up the serverless Cloud Run endpoint executing the FastAPI `main.py` router. Scaled down to standard compute configurations.
- **`firestore.tf`**: Configures the Native Firestore database schemas and security rules.
- **`iap.tf`**: Integrates **Identity-Aware Proxy (IAP)** to harden the Cloud Run endpoint behind Google OAuth2, ensuring only designated enterprise users can access orchestrator tool suites.
- **`storage.tf`**: Provisions Google Cloud Storage buckets for temporary `.mp4` video assemblies and media hydration.
- **`outputs.tf`**: Returns the functional URLs and service accounts to the terminal upon completion.

---

> [!IMPORTANT]
> **State Management Disclaimer:**
> State tracking can be run locally using `terraform.tfstate`, or elevated to a GCS bucket pool for synchronized team development by defining a `backend.tf`. The `setup_gcp_project.py` script automatically configures standard remote state bucketing for you!
