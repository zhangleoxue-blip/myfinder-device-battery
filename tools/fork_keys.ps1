param(
    [string]$PublicKeyPath = '',
    [string]$PrivateKeyPath = ''
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

# The PUBLIC key must be committed: the overlay patch replayer and CI both need
# it to rebuild UpdateTrust.PublicKeyXml after every upstream rebase.
# The PRIVATE key must stay outside the repository (logs/ is gitignored) and is
# only ever injected into the release job through the RELEASE_SIGNING_KEY secret.
if (-not $PublicKeyPath)  { $PublicKeyPath  = Join-Path $root 'overlay\keys\public.xml' }
if (-not $PrivateKeyPath) { $PrivateKeyPath = Join-Path $root 'logs\fork\keys\private.xml' }
$PublicKeyPath  = [IO.Path]::GetFullPath($PublicKeyPath)
$PrivateKeyPath = [IO.Path]::GetFullPath($PrivateKeyPath)

if ((Test-Path -LiteralPath $PrivateKeyPath) -or (Test-Path -LiteralPath $PublicKeyPath)) {
    throw 'Key files already exist. Remove them manually before regenerating (rotating the key invalidates every signed Release).'
}
New-Item -ItemType Directory -Path (Split-Path -Parent $PublicKeyPath)  -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path -Parent $PrivateKeyPath) -Force | Out-Null

$rsa = New-Object Security.Cryptography.RSACryptoServiceProvider(2048)
try {
    $rsa.PersistKeyInCsp = $false
    $utf8 = New-Object Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($PrivateKeyPath, $rsa.ToXmlString($true),  $utf8)
    [IO.File]::WriteAllText($PublicKeyPath,  $rsa.ToXmlString($false), $utf8)
} finally { $rsa.Dispose() }

Write-Host "[fork-keys] public  -> $PublicKeyPath  (commit this file)"
Write-Host "[fork-keys] private -> $PrivateKeyPath  (NEVER commit)"
Write-Host '[fork-keys] Next: python tools/fork_overlay.py apply'
Write-Host '[fork-keys] Then:  gh secret set RELEASE_SIGNING_KEY < "<private.xml path>"'
Write-Host '[fork-keys] Enabling overlay/patches/trust-key.json intentionally breaks upstream-signed updates.'
