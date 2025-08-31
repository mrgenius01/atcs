# PowerShell helper to backup Postgres volume (simple pg_dump)
param(
  [string]$Out = "backup.sql"
)

docker compose exec db pg_dump -U postgres secure_atcs > $Out
Write-Host "Backup written to $Out"
