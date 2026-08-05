$month = (Get-Date).ToString("yyyy-MM")
$url = "http://localhost:8000/export/csv"
Invoke-RestMethod -Uri $url -Method Get -OutFile "receipts_$month.csv"
Write-Host "? Monthly report created: receipts_$month.csv" -ForegroundColor Green
