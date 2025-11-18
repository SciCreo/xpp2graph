param(
    [string]$EnvPath = ".env"
)

if (-not (Test-Path $EnvPath)) {
    Write-Error "Environment file '$EnvPath' not found."
    exit 1
}

Get-Content $EnvPath | ForEach-Object {
    $line = $_.Trim()
    if ([string]::IsNullOrWhiteSpace($line)) {
        return
    }
    if ($line.StartsWith("#")) {
        return
    }

    $parts = $line -split "=", 2
    if ($parts.Length -ne 2) {
        Write-Warning "Skipping malformed line: $line"
        return
    }

    $key = $parts[0].Trim()
    $value = $parts[1]

    [Environment]::SetEnvironmentVariable($key, $value, "Process")
    Write-Host "Set $key"
}

Write-Host "Environment variables loaded from $EnvPath."


