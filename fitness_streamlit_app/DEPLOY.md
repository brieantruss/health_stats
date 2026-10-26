# Streamlit Fitness UI Cloud Run Deployment Guide

To deploy the Streamlit workout entry app serverless on Google Cloud Run for $0 (scaling to zero when inactive), follow these simple steps.

## Prerequisites
1. Installed and configured Google Cloud SDK (`gcloud`).
2. Your GCP VM running on a static external IP.

## Deployment Steps

Run the following command from the `fitness_streamlit_app` directory, replacing `<YOUR_GCP_PROJECT_ID>` and `<YOUR_VM_EXTERNAL_IP>` with your actual values:

```bash
gcloud run deploy fitness-streamlit-ui \
    --source . \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --min-instances 0 \
    --max-instances 1 \
    --memory 256Mi \
    --cpu 1 \
    --set-env-vars API_BASE_URL="http://<YOUR_VM_EXTERNAL_IP>:5001"
```

## Cloud Run Free Tier Scaling Benefits
- `--min-instances 0`: Tells Cloud Run to scale down to 0 instances when no workouts are being entered, costing $0.
- `--memory 256Mi` and `--cpu 1`: Configures minimal footprint to fit safely within GCP's permanent free tier monthly allowance.

## Deploy from GitHub Actions

The **Deploy Fitness Tracker** workflow can deploy the API, the UI, or both from
the repository's **Actions** tab. Choose **Run workflow** and select the target.
The API job pulls `main` on the VM and restarts `fitness-api.service`; the UI job
builds and deploys `fitness_streamlit_app` to Cloud Run.

### One-time setup

1. In the VM's browser SSH terminal, install narrowly scoped passwordless sudo
   rules for the workflow's API pull and restart:

   ```bash
   sudo tee /etc/sudoers.d/fitness-api-deploy >/dev/null <<'EOF'
   btruss ALL=(briean) NOPASSWD: /usr/bin/git -C /home/briean/health_stats pull --ff-only origin main
   btruss ALL=(root) NOPASSWD: /usr/bin/systemctl restart fitness-api.service, /usr/bin/systemctl is-active fitness-api.service
   EOF
   sudo chmod 440 /etc/sudoers.d/fitness-api-deploy
   sudo visudo -cf /etc/sudoers.d/fitness-api-deploy
   ```

2. In the same VM terminal, create a dedicated SSH key for GitHub Actions and
   authorize its public key for the `btruss` login:

   ```bash
   ssh-keygen -t ed25519 -f /home/btruss/github-actions-fitness -N '' -C github-actions-fitness
   mkdir -p /home/btruss/.ssh
   chmod 700 /home/btruss/.ssh
   cat /home/btruss/github-actions-fitness.pub >> /home/btruss/.ssh/authorized_keys
   chmod 600 /home/btruss/.ssh/authorized_keys
   cat /home/btruss/github-actions-fitness
   sudo cat /etc/ssh/ssh_host_ed25519_key.pub
   ```

   Copy the **private key** from the first `cat` output for the GitHub secret
   below. Copy the SSH **host public key** from the second output; prefix it
   with `146.148.87.26 ` to make the `API_VM_KNOWN_HOSTS` value. Keep the private
   key secret.

3. Open the repository's **Settings → Secrets and variables → Actions**.
   Create these repository secrets:

   | Secret | Value |
   | --- | --- |
   | `API_VM_HOST` | `146.148.87.26` |
   | `API_VM_USER` | `btruss` |
   | `API_VM_SSH_PRIVATE_KEY` | Private key copied in step 2 |
   | `API_VM_KNOWN_HOSTS` | `146.148.87.26 ssh-ed25519 <host-public-key>` |

4. In Google Cloud Shell, run the following once to create GitHub Actions
   Workload Identity Federation and a deploy service account:

   ```bash
   PROJECT_ID=my-data-479716
   PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
   POOL_ID=github-actions
   PROVIDER_ID=health-stats
   SERVICE_ACCOUNT=fitness-tracker-deployer
   SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com"

   gcloud services enable iam.googleapis.com iamcredentials.googleapis.com \
     run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
     --project "$PROJECT_ID"
   gcloud iam service-accounts create "$SERVICE_ACCOUNT" --project "$PROJECT_ID"
   gcloud projects add-iam-policy-binding "$PROJECT_ID" \
     --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" --role=roles/run.admin
   gcloud projects add-iam-policy-binding "$PROJECT_ID" \
     --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" --role=roles/cloudbuild.builds.editor
   gcloud projects add-iam-policy-binding "$PROJECT_ID" \
     --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" --role=roles/artifactregistry.writer
   gcloud projects add-iam-policy-binding "$PROJECT_ID" \
     --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" --role=roles/serviceusage.serviceUsageConsumer
   gcloud iam service-accounts add-iam-policy-binding \
     "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
     --project "$PROJECT_ID" \
     --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
     --role=roles/iam.serviceAccountUser
   gcloud projects add-iam-policy-binding "$PROJECT_ID" \
     --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
     --role=roles/run.builder
   gcloud iam workload-identity-pools create "$POOL_ID" \
     --project "$PROJECT_ID" --location global --display-name="GitHub Actions"
   gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
     --project "$PROJECT_ID" --location global \
     --workload-identity-pool "$POOL_ID" \
     --display-name="Health Stats GitHub Actions" \
     --issuer-uri="https://token.actions.githubusercontent.com" \
     --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
     --attribute-condition="assertion.repository == 'brieantruss/health_stats' && assertion.ref == 'refs/heads/main'"
   gcloud iam service-accounts add-iam-policy-binding "$SERVICE_ACCOUNT_EMAIL" \
     --project "$PROJECT_ID" \
     --role=roles/iam.workloadIdentityUser \
     --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/brieantruss/health_stats"
   printf 'Provider: projects/%s/locations/global/workloadIdentityPools/%s/providers/%s\nService account: %s\n' \
     "$PROJECT_NUMBER" "$POOL_ID" "$PROVIDER_ID" "$SERVICE_ACCOUNT_EMAIL"
   ```

5. Back in **Settings → Secrets and variables → Actions**, add the printed
   provider and service-account values as repository secrets
   `GCP_WORKLOAD_IDENTITY_PROVIDER` and `GCP_DEPLOY_SERVICE_ACCOUNT`. Add these
   repository variables:

   | Variable | Value |
   | --- | --- |
   | `GCP_PROJECT_ID` | `my-data-479716` |
   | `API_BASE_URL` | `http://146.148.87.26:5001` |

6. Delete the temporary private-key file from the VM after saving it in
   GitHub:

   ```bash
   rm /home/btruss/github-actions-fitness
   ```

After setup, use the repository's **Actions → Deploy Fitness Tracker → Run
workflow** page and choose **both** for a full deployment, **api** for an API
pull/restart only, or **ui** for a Cloud Run deployment only.
