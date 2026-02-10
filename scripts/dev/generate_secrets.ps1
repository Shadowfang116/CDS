$jwt = [Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }))
$enc = [Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }))

Write-Host "APP_SECRET_KEY=$jwt"
Write-Host "INTEGRATIONS_ENCRYPTION_KEY=$enc"
