param(
    [string]$OutputDirectory = '',
    [switch]$Package
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $root 'outputs\fork-build' }
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)

Write-Host "[fork-build] root   = $root"
Write-Host "[fork-build] output = $OutputDirectory"

$buildScript = Join-Path $root 'scripts\Build.ps1'
if (-not (Test-Path -LiteralPath $buildScript -PathType Leaf)) { throw 'Upstream Build.ps1 is missing.' }

# Build.ps1 compiles every scripts/*.cs with the system .NET Framework compiler,
# runs offline self-tests and writes build-info.json with per-source hashes.
& $buildScript -OutputDirectory $OutputDirectory
if ($LASTEXITCODE -ne 0) { throw "Upstream build failed with exit code $LASTEXITCODE" }
Write-Host '[fork-build] upstream build and offline checks succeeded.'

if ($Package) {
    # Package.ps1 re-validates every source hash recorded in build-info.json
    # and prepares the portable Python engine. It needs network access.
    $packageScript = Join-Path $root 'scripts\Package.ps1'
    $packageOutput = Join-Path $root 'outputs\fork-release'
    & $packageScript -SkipBuild -BuildDirectory $OutputDirectory -OutputDirectory $packageOutput
    if ($LASTEXITCODE -ne 0) { throw "Packaging failed with exit code $LASTEXITCODE" }
    Write-Host "[fork-build] release package -> $packageOutput"
}
