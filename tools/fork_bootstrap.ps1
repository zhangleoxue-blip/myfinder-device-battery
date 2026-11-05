param(
    [Parameter(Mandatory=$true)][string]$OriginUrl,
    [switch]$SkipPush
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $configPath = Join-Path $root 'fork-config.json'
    $config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $config.fork.origin = $OriginUrl
    $utf8 = New-Object Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($configPath, ($config | ConvertTo-Json -Depth 6), $utf8)
    Write-Host "[fork-bootstrap] fork-config.json -> origin = $OriginUrl"

    $remotes = @(git remote)
    if ($remotes -contains 'origin') { git remote set-url origin $OriginUrl }
    else { git remote add origin $OriginUrl }
    Write-Host '[fork-bootstrap] origin remote configured.'

    if ($SkipPush) {
        Write-Host '[fork-bootstrap] push skipped (-SkipPush); run git push -u origin fork/main when ready.'
    } else {
        git push -u origin fork/main
        if ($LASTEXITCODE -ne 0) { throw "push failed with exit code $LASTEXITCODE" }
        Write-Host '[fork-bootstrap] fork/main pushed.'
    }

    Write-Host '[fork-bootstrap] Next steps in the GitHub UI:'
    Write-Host '  1. Settings > Actions > General > Workflow permissions = Read and write.'
    Write-Host '  2. Actions tab > enable the "Fork upstream sync" workflow (scheduled workflows are disabled by default on forks).'
    Write-Host '  3. Commit the updated fork-config.json on fork/main.'
} finally { Pop-Location }
