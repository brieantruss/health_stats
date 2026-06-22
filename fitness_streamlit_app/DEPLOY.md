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
