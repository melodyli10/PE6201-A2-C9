param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot ".env"

if (-not (Test-Path -LiteralPath $envPath)) {
    throw "Missing .env. Create it at the repository root before running."
}

$keyLine = Get-Content -LiteralPath $envPath |
    Where-Object { $_ -match '^OPENROUTER_API_KEY=' } |
    Select-Object -First 1

if (-not $keyLine) {
    throw "OPENROUTER_API_KEY is missing from .env."
}

$apiKey = ($keyLine -split '=', 2)[1].Trim()
if (-not $apiKey -or $apiKey -eq "REPLACE_WITH_YOUR_OPENROUTER_KEY") {
    throw "Replace the placeholder OPENROUTER_API_KEY in .env before running."
}

Push-Location $repoRoot
try {
    & $Python -m unittest eval.test_harness
    if ($LASTEXITCODE -ne 0) {
        throw "Unit tests failed; the paid live run was not started."
    }

    $dryRunOutput = & $Python -m eval.harness `
        --suite d4 `
        --backend scripted `
        --trial-mode battery `
        --model "google/gemini-2.5-pro" `
        --prompt-version v2-final `
        --dry-run 2>&1

    $dryRunOutput | Write-Output
    if ($LASTEXITCODE -ne 0 -or
        ($dryRunOutput -join "`n") -notmatch 'cases=35, negatives=10, trials=65') {
        throw "Dry run did not confirm 35 cases, 10 negatives and 65 trials. The paid live run was not started."
    }

    & $Python -m eval.harness `
        --suite d4 `
        --backend live `
        --trial-mode battery `
        --model "google/gemini-2.5-pro" `
        --prompt-version v2-final `
        --allow-live

    if ($LASTEXITCODE -ne 0) {
        throw "Gemini live battery failed. Keep any generated result directory for diagnosis."
    }
}
finally {
    Pop-Location
}
