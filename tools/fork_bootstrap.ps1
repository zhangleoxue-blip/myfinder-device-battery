param(
    [Parameter(Mandatory=$true)][string]$OriginUrl,
    [switch]$SkipPush,
    [switch]$NonInteractive,
    [string]$ProxyUrl = ''
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

# PowerShell launched outside Git Bash has no git on PATH on this machine,
# and the global http.proxy points at an offline local port.
$gitExe = 'C:\Users\admin\AppData\Local\Programs\WorkBuddy\resources\vendor\PortableGit\mingw64\bin\git.exe'
if (-not (Test-Path -LiteralPath $gitExe)) {
    $found = Get-Command git -ErrorAction SilentlyContinue
    if (-not $found) { throw 'git executable not found; install Git or edit this script.' }
    $gitExe = $found.Source
}
# Default path clears every proxy (direct HTTPS works on some networks).
# With -ProxyUrl, route git through an explicit local proxy such as Clash 7890.
if ($ProxyUrl) {
    $gitProxyArgs = @('-c', "http.proxy=$ProxyUrl", '-c', "https.proxy=$ProxyUrl")
    Write-Host "[fork-bootstrap] git proxy = $ProxyUrl"
} else {
    foreach ($name in @('HTTP_PROXY','http_proxy','HTTPS_PROXY','https_proxy','ALL_PROXY','all_proxy')) {
        Remove-Item -LiteralPath ('Env:' + $name) -ErrorAction SilentlyContinue
    }
    $gitProxyArgs = @('-c', 'http.proxy=', '-c', 'https.proxy=')
    Write-Host '[fork-bootstrap] git proxy = direct'
}
if ($NonInteractive) {
    $env:GIT_TERMINAL_PROMPT = '0'
    $env:GCM_INTERACTIVE = 'never'
}

Push-Location $root
try {
    # Patch only the origin value so the rest of the JSON formatting survives.
    $configPath = Join-Path $root 'fork-config.json'
    $text = [IO.File]::ReadAllText($configPath)
    $pattern = '("origin"\s*:\s*")[^"]*(")'
    if ($text -notmatch $pattern) { throw 'fork.origin key not found in fork-config.json.' }
    $replacement = '${1}' + $OriginUrl + '${2}'
    $updated = [regex]::Replace($text, $pattern, $replacement)
    [IO.File]::WriteAllText($configPath, $updated, (New-Object Text.UTF8Encoding($false)))
    Write-Host "[fork-bootstrap] fork-config.json -> origin = $OriginUrl"

    $remotes = @(& $gitExe remote)
    if ($remotes -contains 'origin') { & $gitExe remote set-url origin $OriginUrl }
    else { & $gitExe remote add origin $OriginUrl }
    Write-Host '[fork-bootstrap] origin remote configured.'

    if ($SkipPush) {
        Write-Host '[fork-bootstrap] push skipped (-SkipPush).'
        Write-Host '[fork-bootstrap] Run again without -SkipPush to push; Git Credential Manager will open a sign-in window.'
    } else {
        & $gitExe @gitProxyArgs push -u origin fork/main
        if ($LASTEXITCODE -ne 0) { throw "push failed with exit code $LASTEXITCODE" }
        Write-Host '[fork-bootstrap] fork/main pushed.'
    }

    Write-Host '[fork-bootstrap] Next steps in the GitHub UI:'
    Write-Host '  1. Settings > Actions > General > Workflow permissions = Read and write.'
    Write-Host '  2. Actions tab > enable the "Fork upstream sync" workflow (scheduled workflows are disabled by default on forks).'
    Write-Host '  3. Commit the updated fork-config.json on fork/main.'
} finally { Pop-Location }
