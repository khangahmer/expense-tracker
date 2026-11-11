$ErrorActionPreference = "Stop"
$steps = @("ruff check .", "ruff format --check .", "mypy", "pytest -q")
foreach ($step in $steps) {
    Write-Host ">> $step" -ForegroundColor Cyan
    Invoke-Expression $step
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED: $step" -ForegroundColor Red
        exit 1
    }
}
Write-Host "All checks passed" -ForegroundColor Green