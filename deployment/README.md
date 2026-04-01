# 🚀 Deploying GenMedia Izumi Agent to GCP

Welcome to the deployment guide for the **GenMedia Izumi Agent**! This workspace provides open-source, reference implementations of multimodal creative agents built on Vertex AI.

This guide will walk you through setting up your Google Cloud Platform (GCP) environment and deploying the headless API server using **Terraform** and **Cloud Build**.

---

## 📋 Prerequisites

Before you begin, ensure you have the following tools installed and authenticated on your local machine:

| Tool | Purpose | Install Link |
| :--- | :--- | :--- |
| **Google Cloud SDK (`gcloud`)** | Interacting with GCP Services | [Install](https://cloud.google.com/sdk/docs/install) |
| **Terraform** | Automated Cloud Infrastructure | [Install](https://developer.hashicorp.com/terraform/install) |
| **Python 3.11+** | Running setup wrapper scripts | [Install](https://python.org) |

> [!IMPORTANT]
> **Authentication Check:**
> Ensure you have run:
> ```bash
> gcloud auth login
> gcloud auth application-default login
> ```

---

## ⚡ Quick Start: 3-Step Deployment

Deploying is a standard sequence of cloning the workspace, provisioning cloud infrastructure, and pushing the server build.

### 1️⃣ Clone the Repository
Clone this monorepo to your local machine:
```bash
git clone https://github.com/GoogleCloudPlatform/genmedia-izumi-agent.git
cd genmedia-izumi-agent
```

### 2️⃣ Provision Cloud Infrastructure
We use a lightweight Python wrapper to instantiate Terraform. This script will prompt you for your GCP Project ID and automatically generate your deployment secrets.

```bash
python scripts/setup_gcp_project.py --app_env staging
```
*Upon completion, a `.env` file will be generated in `demos/backend/` with your localized cloud bucket bindings.*

### 3️⃣ Deploy to Cloud Run
Once the infrastructure is live, deploy the FastAPI backend container using Google Cloud Build:

```bash
./scripts/deploy-to-cloud-run.sh --app_env staging
```

🎉 **Success!** The shell will print the final HTTPS endpoint of your serverless AI agent hub.

---

## 🛠️ Architecture Deep Dive

If you want to understand what's happening under the hood, this repository treats **Infrastructure as Code (IaC)** as a primary citizen.

### 🔐 Infrastructure Provisioning (`Terraform`)
The resources deployed in `deployment/terraform` include:
- **APIs**: Enables Vertex AI, Cloud Run, Firestore, and Identity-Aware Proxy.
- **Identity & Least Privilege (IAM)**:
    - `Cloud Run Execution SA`: Scoped only to Vertex AI + Cloud Storage.
    - `Cloud Build SA`: Scoped to push images and run deployments.
- **Persistent State**:
    - Firestore collections for async job tracking.
    - Cloud Storage Buckets for transient `.mp4` stitching buffers.

### 🚢 The Continuous Build Graph (`cloudbuild.yaml`)
Triggering `./scripts/deploy-to-cloud-run.sh` launches a standard Cloud Build event:
1. **Container Package**: It builds the serverless environment pulling from `deployment/Dockerfile`.
2. **Push to Registry**: Pushes the image to Artifact Registry.
3. **Rolling Revision Upgrade**: Safely updates the live Cloud Run endpoint to use the new image.

---

## 🧹 Tearing Down Resources

To securely remove all Google Cloud resources provisioned for a staging environment and avoid egress billing, run:

```bash
python scripts/setup_gcp_project.py --app_env staging --destroy
```

> [!CAUTION]
> **Irreversible Deletion:**
> This command uses Terraform to forcibly destroy cloud pools. Database archives and persistent object contents will be deleted forever.
