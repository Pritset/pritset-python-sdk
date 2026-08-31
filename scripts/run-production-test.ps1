param(
    [string]$EnvFile = (Join-Path $PSScriptRoot '..\.env')
)

$ErrorActionPreference = 'Stop'
$knownNames = @(
    'PRITSET_BASE_URL',
    'PRITSET_ACCESS_TOKEN',
    'PRITSET_SECRET',
    'PRITSET_WEBHOOK_URL',
    'PRITSET_TEMPLATE_ID',
    'PRITSET_ALLOW_PRODUCTION',
    'PRITSET_PRODUCTION_TEST_USER_CONFIRMED',
    'PRITSET_TEST_RUN_PREFIX',
    'PRITSET_TEMPLATE_PATH'
)
$previous = @{}

try {
    $resolvedEnvFile = (Resolve-Path -LiteralPath $EnvFile).Path
    foreach ($line in Get-Content -LiteralPath $resolvedEnvFile) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) {
            continue
        }
        $separator = $trimmed.IndexOf('=')
        if ($separator -lt 1) {
            throw "Invalid environment line in $resolvedEnvFile."
        }
        $name = $trimmed.Substring(0, $separator).Trim()
        if ($name -notin $knownNames) {
            continue
        }
        $value = $trimmed.Substring($separator + 1).Trim()
        if ($value.Length -ge 2 -and $value[0] -eq '"' -and $value[$value.Length - 1] -eq '"') {
            $value = $value.Substring(1, $value.Length - 2)
        }
        if (-not $previous.ContainsKey($name)) {
            $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        }
        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }

    $confirmation = Read-Host 'Type RUN-PRODUCTION-TEST to continue'
    if ($confirmation -cne 'RUN-PRODUCTION-TEST') {
        throw 'Production test canceled.'
    }

    $repository = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
    Push-Location -LiteralPath $repository
    try {
        python scripts/production_lifecycle.py
        if ($LASTEXITCODE -ne 0) {
            throw "Production lifecycle exited with code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    foreach ($name in $previous.Keys) {
        [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process')
    }
}
