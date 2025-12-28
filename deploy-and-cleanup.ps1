#!/usr/bin/env pwsh
# Deploy to Cloud Run and cleanup old builds/images

Write-Host "Starting deployment and cleanup..." -ForegroundColor Cyan

# Configuration
$PROJECT_ID = "smart-link-updater"
$SERVICE_NAME = "video-enhancer"
$REGION = "us-central1"

# Step 1: Deploy to Cloud Run
Write-Host ""
Write-Host "Deploying to Cloud Run..." -ForegroundColor Yellow
gcloud builds submit --config cloudbuild.yaml

if ($LASTEXITCODE -ne 0) {
    Write-Host "Deployment failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Deployment successful!" -ForegroundColor Green

# Step 2: Cleanup old images
Write-Host ""
Write-Host "Cleaning up old images from Container Registry..." -ForegroundColor Yellow

# Get all images for this service
$images = gcloud container images list-tags "gcr.io/$PROJECT_ID/$SERVICE_NAME" --format="get(digest)" --filter="NOT tags:*" 2>$null

if ($images) {
    $imageCount = ($images | Measure-Object).Count
    Write-Host "Found $imageCount untagged images to delete..." -ForegroundColor Cyan
    
    foreach ($digest in $images) {
        Write-Host "Deleting image: $digest" -ForegroundColor Gray
        gcloud container images delete "gcr.io/$PROJECT_ID/${SERVICE_NAME}@$digest" --quiet 2>$null
    }
    
    Write-Host "Untagged images cleaned up!" -ForegroundColor Green
} else {
    Write-Host "No untagged images found." -ForegroundColor Gray
}

# Keep only the current image, delete all others
Write-Host "Cleaning up old tagged images (keeping only current)..." -ForegroundColor Cyan
$allTaggedImages = gcloud container images list-tags "gcr.io/$PROJECT_ID/$SERVICE_NAME" --format="get(digest)" --sort-by="~timestamp" 2>$null

if ($allTaggedImages) {
    $imageArray = @($allTaggedImages)
    if ($imageArray.Count -gt 1) {
        $toDelete = $imageArray[1..($imageArray.Count - 1)]
        Write-Host "Deleting $($toDelete.Count) old tagged images..." -ForegroundColor Cyan
        
        foreach ($digest in $toDelete) {
            Write-Host "Deleting: $digest" -ForegroundColor Gray
            gcloud container images delete "gcr.io/$PROJECT_ID/${SERVICE_NAME}@$digest" --quiet 2>$null
        }
        
        Write-Host "Old tagged images cleaned up!" -ForegroundColor Green
    } else {
        Write-Host "Only $($imageArray.Count) tagged images found, nothing to delete." -ForegroundColor Gray
    }
}

# Step 3: Cleanup old Cloud Build logs (keep last 10)
Write-Host ""
Write-Host "Cleaning up old Cloud Build logs..." -ForegroundColor Yellow
$builds = gcloud builds list --limit=100 --format="get(id)" --sort-by="~createTime" 2>$null

if ($builds) {
    $buildArray = @($builds)
    if ($buildArray.Count -gt 10) {
        $toDelete = $buildArray[10..($buildArray.Count - 1)]
        Write-Host "Found $($toDelete.Count) old builds to delete..." -ForegroundColor Cyan
        
        # Note: Cloud Build history cannot be deleted via CLI
        Write-Host "Note: Cloud Build history is automatically managed by Google Cloud." -ForegroundColor Gray
        Write-Host "Old builds will be automatically deleted after 120 days." -ForegroundColor Gray
    } else {
        Write-Host "Only $($buildArray.Count) builds found." -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Deployment and cleanup complete!" -ForegroundColor Green
$serviceUrl = "https://${SERVICE_NAME}-601738079869.${REGION}.run.app"
Write-Host "Service URL: $serviceUrl" -ForegroundColor Cyan
