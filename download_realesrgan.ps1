# Download and setup Real-ESRGAN for Windows
Write-Host "Downloading Real-ESRGAN for Windows..." -ForegroundColor Green

$downloadUrl = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip"
$zipFile = "realesrgan-windows.zip"
$extractPath = "realesrgan-temp"
$binFolder = "bin"

# Download
Write-Host "Step 1: Downloading..." -ForegroundColor Yellow
Invoke-WebRequest -Uri $downloadUrl -OutFile $zipFile -UseBasicParsing

# Extract
Write-Host "Step 2: Extracting..." -ForegroundColor Yellow
Expand-Archive -Path $zipFile -DestinationPath $extractPath -Force

# Copy executable to bin folder
Write-Host "Step 3: Copying files to bin folder..." -ForegroundColor Yellow
Copy-Item "$extractPath\realesrgan-ncnn-vulkan.exe" -Destination "$binFolder\realesrgan-ncnn-vulkan.exe" -Force

# Copy models if they exist
if (Test-Path "$extractPath\models") {
    Write-Host "Step 4: Copying models..." -ForegroundColor Yellow
    if (-not (Test-Path "$binFolder\models")) {
        New-Item -ItemType Directory -Path "$binFolder\models" -Force | Out-Null
    }
    Copy-Item "$extractPath\models\*" -Destination "$binFolder\models\" -Recurse -Force
}

# Cleanup
Write-Host "Step 5: Cleaning up..." -ForegroundColor Yellow
Remove-Item $zipFile -Force
Remove-Item $extractPath -Recurse -Force

Write-Host ""
Write-Host "Real-ESRGAN installed successfully!" -ForegroundColor Green
Write-Host "Location: $binFolder\realesrgan-ncnn-vulkan.exe" -ForegroundColor Cyan

# Verify
Write-Host ""
Write-Host "Verifying installation..." -ForegroundColor Yellow
& "$binFolder\realesrgan-ncnn-vulkan.exe" --help

Write-Host ""
Write-Host "You can now run your Flask app!" -ForegroundColor Green
