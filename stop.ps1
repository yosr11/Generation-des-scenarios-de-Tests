# Arrête les services démarrés par start.ps1
$Root = $PSScriptRoot

if (Test-Path "$Root\.running_jobs") {
    Get-Content "$Root\.running_jobs" | ForEach-Object {
        $job = Get-Job -Id $_ -ErrorAction SilentlyContinue
        if ($job) {
            Stop-Job $job -ErrorAction SilentlyContinue
            Remove-Job $job -Force -ErrorAction SilentlyContinue
            Write-Host "Job $_ arrêté." -ForegroundColor Yellow
        }
    }
    Remove-Item "$Root\.running_jobs"
}

# Fallback : tuer les processus sur les ports 8000 et 3000
foreach ($port in 8000, 3000) {
    $pid_ = (netstat -ano | Select-String ":$port ") -replace '.*\s+(\d+)$','$1' | Select-Object -First 1
    if ($pid_) {
        Stop-Process -Id ([int]$pid_) -Force -ErrorAction SilentlyContinue
        Write-Host "Processus sur le port $port terminé (PID $pid_)." -ForegroundColor Yellow
    }
}

Write-Host "Arrêt terminé." -ForegroundColor Green
