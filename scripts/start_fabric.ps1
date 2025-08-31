# PowerShell script to start a local Fabric dev network (placeholder)
# Requires Hyperledger Fabric samples and binaries available on PATH.
param(
    [string]$NetworkPath = "$env:USERPROFILE\fabric-samples\test-network"
)

if (-not (Test-Path $NetworkPath)) {
  Write-Host "Fabric samples not found at $NetworkPath" -ForegroundColor Yellow
  exit 0
}

Push-Location $NetworkPath
./network.bat down
./network.bat up createChannel -c mychannel -ca
Pop-Location
Write-Host "Fabric dev network started (mychannel)." -ForegroundColor Green
