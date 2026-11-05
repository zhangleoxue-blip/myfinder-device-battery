param([string]$OutputDirectory = '')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $root 'logs\fork\keys' }
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$privateKey = Join-Path $OutputDirectory 'private.xml'
$publicKey = Join-Path $OutputDirectory 'public.xml'
if ((Test-Path -LiteralPath $privateKey) -or (Test-Path -LiteralPath $publicKey)) {
    throw 'Key files already exist. Remove them manually before regenerating.'
}

$rsa = New-Object Security.Cryptography.RSACryptoServiceProvider(2048)
try {
    $rsa.PersistKeyInCsp = $false
    $utf8 = New-Object Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($privateKey, $rsa.ToXmlString($true), $utf8)
    [IO.File]::WriteAllText($publicKey, $rsa.ToXmlString($false), $utf8)
} finally { $rsa.Dispose() }

Write-Host "[fork-keys] public  -> $publicKey"
Write-Host "[fork-keys] private -> $privateKey"
Write-Host '[fork-keys] logs/ is gitignored upstream; never commit private.xml.'
Write-Host '[fork-keys] Enabling overlay/patches/trust-key.json will break upstream-signed updates.'
