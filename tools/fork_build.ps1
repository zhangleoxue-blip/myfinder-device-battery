param(
    [string]$OutputDirectory = '',
    [switch]$Package,
    [string]$PythonDir = '',
    [switch]$AllowMissingPwsh
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $root 'outputs\fork-build' }
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)

# Upstream tests/Run.ps1 and Publish-DevicePack.ps1 resolve the interpreter
# with `Get-Command python`. On some Windows machines that hits the Microsoft
# Store stub in WindowsApps, which is not a real interpreter. Prepend a working
# Python for this process only; child powershell.exe processes inherit PATH.
if (-not $PythonDir) {
    $candidates = @(
        'C:\Users\admin\.workbuddy\binaries\python\envs\default\Scripts',
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python314'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312')
    )
    foreach ($dir in $candidates) {
        if (Test-Path -LiteralPath (Join-Path $dir 'python.exe')) { $PythonDir = $dir; break }
    }
}
if ($PythonDir) {
    $env:PATH = $PythonDir + ';' + $env:PATH
    Write-Host "[fork-build] python PATH = $PythonDir"
}

# .NET Framework's ProcessStartInfo.EnvironmentVariables is a case-insensitive
# Hashtable. If both HTTP_PROXY and http_proxy exist, starting a child process
# throws "An item with the same key has already been added". Direct HTTPS works
# on this machine, so clear every proxy variable before the upstream tests run.
foreach ($name in @('HTTP_PROXY','http_proxy','HTTPS_PROXY','https_proxy',
                    'ALL_PROXY','all_proxy','NO_PROXY','no_proxy')) {
    Remove-Item -LiteralPath ('Env:' + $name) -ErrorAction SilentlyContinue
}

Write-Host "[fork-build] root   = $root"
Write-Host "[fork-build] output = $OutputDirectory"

$buildScript = Join-Path $root 'scripts\Build.ps1'
if (-not (Test-Path -LiteralPath $buildScript -PathType Leaf)) { throw 'Upstream Build.ps1 is missing.' }

$hasPwsh = [bool](Get-Command pwsh.exe -ErrorAction SilentlyContinue)
if (-not $hasPwsh) {
    Write-Host '[fork-build] NOTE: pwsh.exe (PowerShell 7) is absent; upstream installer regressions need it.'
}

# Build.ps1 compiles every scripts/*.cs with the system .NET Framework compiler,
# runs offline self-tests and writes build-info.json AFTER the full regression.
$buildFailed = $false
$buildError = ''
try {
    & $buildScript -OutputDirectory $OutputDirectory
    if ($LASTEXITCODE -ne 0) { $buildFailed = $true; $buildError = "exit code $LASTEXITCODE" }
} catch {
    $buildFailed = $true
    $buildError = $_.Exception.Message
}

if ($buildFailed) {
    $appExe = Join-Path $OutputDirectory 'AtkMouseBattery.exe'
    $probeExe = Join-Path $OutputDirectory 'AtkBatteryProbe.exe'
    $compiled = (Test-Path -LiteralPath $appExe -PathType Leaf) -and (Test-Path -LiteralPath $probeExe -PathType Leaf)
    if ($AllowMissingPwsh -and (-not $hasPwsh) -and $compiled) {
        Write-Warning "[fork-build] PARTIAL SUCCESS: compilation and offline self-tests finished; full regression needs PowerShell 7. Reason: $buildError"
        Write-Warning '[fork-build] build-info.json was NOT produced. Do not package from this output; use CI or install PowerShell 7.'
    } else {
        throw "Upstream build failed: $buildError"
    }
} else {
    Write-Host '[fork-build] upstream build and full regression succeeded.'
}

if ($Package) {
    if ($buildFailed) { throw 'Packaging requires a fully validated build; install PowerShell 7 or use CI.' }
    # Package.ps1 re-validates every source hash recorded in build-info.json
    # and prepares the portable Python engine. It needs network access.
    $packageScript = Join-Path $root 'scripts\Package.ps1'
    $packageOutput = Join-Path $root 'outputs\fork-release'
    & $packageScript -SkipBuild -BuildDirectory $OutputDirectory -OutputDirectory $packageOutput
    if ($LASTEXITCODE -ne 0) { throw "Packaging failed with exit code $LASTEXITCODE" }
    Write-Host "[fork-build] release package -> $packageOutput"
}
