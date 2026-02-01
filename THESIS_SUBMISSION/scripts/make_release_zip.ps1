param(
    [string]$OutputPath = "release.zip"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Push-Location $repoRoot
try {
    $files = git ls-files
    if (-not $files) {
        throw "No tracked files found. Ensure this is a git repository with committed files."
    }

    if (Test-Path $OutputPath) {
        Remove-Item $OutputPath -Force
    }

    Compress-Archive -Path $files -DestinationPath $OutputPath -Force
    Write-Host "Created $OutputPath"
}
finally {
    Pop-Location
}
