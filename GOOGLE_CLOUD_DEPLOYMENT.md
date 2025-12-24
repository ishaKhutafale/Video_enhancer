# Google Cloud Deployment Guide

## Prerequisites

1. **Google Cloud Account**
   - Sign up at https://cloud.google.com
   - Get $300 free credits for new users

2. **Install Google Cloud CLI**
   ```powershell
   # Install using winget
   winget install Google.CloudSDK
   
   # Restart terminal, then initialize
   gcloud init
   ```

3. **Create a Google Cloud Project**
   ```powershell
   # Set project name (use your own)
   gcloud projects create video-enhancer-app --name="Video Enhancer"
   
   # Set as active project
   gcloud config set project video-enhancer-app
   ```

---

## Quick Deployment (Automated)

### Option 1: Deploy with Cloud Build (Recommended)

```powershell
# 1. Enable required APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com

# 2. Submit build and deploy
gcloud builds submit --config cloudbuild.yaml

# 3. Get your service URL
gcloud run services describe video-enhancer --region us-central1 --format 'value(status.url)'
```

Your app will be live at: `https://video-enhancer-XXXXX-uc.a.run.app`

---

## Manual Deployment (Step-by-Step)

### Step 1: Enable APIs

```powershell
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### Step 2: Build Docker Image

```powershell
# Set your project ID
$PROJECT_ID = "video-enhancer-app"

# Build image
gcloud builds submit --tag gcr.io/$PROJECT_ID/video-enhancer
```

### Step 3: Deploy to Cloud Run

```powershell
gcloud run deploy video-enhancer `
  --image gcr.io/$PROJECT_ID/video-enhancer `
  --platform managed `
  --region us-central1 `
  --allow-unauthenticated `
  --memory 4Gi `
  --cpu 2 `
  --timeout 3600 `
  --max-instances 5
```

---

## Configuration Options

### Memory and CPU

Video processing needs more resources:

```powershell
# Update service configuration
gcloud run services update video-enhancer `
  --region us-central1 `
  --memory 8Gi `
  --cpu 4
```

### Timeout

Increase for longer videos:

```powershell
gcloud run services update video-enhancer `
  --region us-central1 `
  --timeout 3600  # 1 hour
```

### Concurrency

Control how many requests per instance:

```powershell
gcloud run services update video-enhancer `
  --region us-central1 `
  --concurrency 1  # Process one video at a time
```

---

## Environment Variables (Optional)

Add custom environment variables:

```powershell
gcloud run services update video-enhancer `
  --region us-central1 `
  --set-env-vars "MAX_VIDEO_SIZE=100MB,ENABLE_GPU=false"
```

---

## Update Your Android App

After deployment, update the backend URL in your Android app:

**File:** `RetrofitClient.kt`

```kotlin
// Replace with your Cloud Run URL
const val BASE_URL = "https://video-enhancer-XXXXX-uc.a.run.app/"
```

---

## Monitor Your App

### View Logs

```powershell
gcloud run services logs read video-enhancer --region us-central1
```

### Check Service Status

```powershell
gcloud run services describe video-enhancer --region us-central1
```

### View Metrics

Visit: https://console.cloud.google.com/run

---

## Cost Optimization

### Cloud Run Pricing (Free Tier)

- **2 million requests/month** - FREE
- **360,000 GB-seconds/month** - FREE
- **180,000 vCPU-seconds/month** - FREE

Beyond free tier:
- $0.00002400 per request
- $0.00001800 per GB-second
- $0.00002400 per vCPU-second

### Reduce Costs

1. **Limit max instances**
   ```powershell
   gcloud run services update video-enhancer --max-instances 2
   ```

2. **Set minimum instances to 0** (default - scales to zero when idle)

3. **Use smaller memory** if possible
   ```powershell
   gcloud run services update video-enhancer --memory 2Gi
   ```

---

## Troubleshooting

### Build Fails

**Issue:** Docker build timeout
```powershell
# Increase build timeout
gcloud builds submit --timeout=20m --tag gcr.io/$PROJECT_ID/video-enhancer
```

### Service Crashes

**Issue:** Out of memory
```powershell
# Increase memory
gcloud run services update video-enhancer --memory 8Gi
```

**Issue:** Timeout on long videos
```powershell
# Increase timeout
gcloud run services update video-enhancer --timeout 3600
```

### Permission Denied

```powershell
# Grant yourself permissions
gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="user:YOUR_EMAIL@gmail.com" `
  --role="roles/run.admin"
```

---

## Local Testing with Docker

Test your Docker image locally before deploying:

```powershell
# Build image
docker build -t video-enhancer .

# Run container
docker run -p 8080:8080 video-enhancer

# Test at http://localhost:8080
```

---

## CI/CD (Continuous Deployment)

### Automatic Deployment on Git Push

1. **Connect GitHub Repository**
   ```powershell
   gcloud beta run deploy video-enhancer `
     --source . `
     --region us-central1
   ```

2. **Set up Cloud Build Trigger**
   - Go to Cloud Build → Triggers
   - Connect your GitHub repository
   - Set trigger on `app-integrated` branch push
   - Use `cloudbuild.yaml`

---

## Custom Domain (Optional)

Map your own domain:

```powershell
# Add domain mapping
gcloud run domain-mappings create `
  --service video-enhancer `
  --domain video.yourdomain.com `
  --region us-central1
```

Then add DNS records as instructed by Cloud Run.

---

## Cleanup (Delete Everything)

```powershell
# Delete Cloud Run service
gcloud run services delete video-enhancer --region us-central1

# Delete container images
gcloud container images delete gcr.io/$PROJECT_ID/video-enhancer

# Delete project (removes everything)
gcloud projects delete video-enhancer-app
```

---

## Security Best Practices

### 1. Enable Authentication

Remove `--allow-unauthenticated` if you want to protect your API:

```powershell
gcloud run services update video-enhancer `
  --region us-central1 `
  --no-allow-unauthenticated
```

### 2. Add API Key Protection

Update `app.py` to require API keys:

```python
API_KEY = os.environ.get("API_KEY", "your-secret-key")

@app.before_request
def check_api_key():
    if request.endpoint != 'index':  # Skip for homepage
        key = request.headers.get('X-API-Key')
        if key != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401
```

Then set environment variable:

```powershell
gcloud run services update video-enhancer `
  --set-env-vars "API_KEY=your-generated-secret-key"
```

---

## Performance Tips

1. **Use Cloud Storage** for large videos (instead of local disk)
2. **Enable CDN** for faster downloads
3. **Use GPU instances** (requires specific configuration)
4. **Implement caching** for repeated requests
5. **Add queue system** for batch processing

---

## Next Steps

1. ✅ Deploy your app
2. ✅ Test with a sample video
3. ✅ Update Android app with Cloud Run URL
4. ✅ Monitor logs and performance
5. ✅ Set up custom domain (optional)
6. ✅ Implement authentication (optional)

---

## Support

- **Cloud Run Docs:** https://cloud.google.com/run/docs
- **Pricing Calculator:** https://cloud.google.com/products/calculator
- **Community Support:** https://stackoverflow.com/questions/tagged/google-cloud-run

Your video enhancer is now production-ready! 🚀
