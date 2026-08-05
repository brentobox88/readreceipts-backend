# Upload all images in a folder
$folder = "C:\ReceiptsToProcess"
$files = Get-ChildItem $folder -Filter *.jpg

foreach ($file in $files) {
    Write-Host "Uploading $($file.Name)..." -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/upload" -Method Post -Form @{
            file = $file
            business = "production"
        }
        Write-Host "  ? $($response.data.merchant) - $$($response.data.total)" -ForegroundColor Green
    } catch {
        Write-Host "  ? Failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}
