# Install unified Connect pipeline smoke into Fusion 360 Scripts folder.
# Removes legacy per-milestone runners (m5/m6/m7_connect_smoke.py).

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PluginDir = Join-Path $RepoRoot "fusion360-unified-cabinet-plugin"
$FusionScripts = Join-Path $env:APPDATA "Autodesk\Autodesk Fusion 360\API\Scripts"

if (-not (Test-Path $PluginDir)) {
    throw "Plugin folder not found: $PluginDir"
}
if (-not (Test-Path $FusionScripts)) {
    New-Item -ItemType Directory -Path $FusionScripts -Force | Out-Null
}

$Sources = @(
    @{ Name = "connect_pipeline_smoke.py"; Path = Join-Path $PluginDir "connect_pipeline_smoke.py" },
    @{ Name = "smoke_connect_helpers.py"; Path = Join-Path $PluginDir "tests\smoke_connect_helpers.py" }
)

$Legacy = @(
    "m5_connect_smoke.py",
    "m6_connect_smoke.py",
    "m7_connect_smoke.py"
)

Write-Host "Fusion Scripts: $FusionScripts"
Write-Host ""

foreach ($legacyName in $Legacy) {
    $legacyPath = Join-Path $FusionScripts $legacyName
    if (Test-Path $legacyPath) {
        Remove-Item $legacyPath -Force
        Write-Host "Removed legacy: $legacyName"
    }
}

foreach ($item in $Sources) {
    if (-not (Test-Path $item.Path)) {
        throw "Missing source file: $($item.Path)"
    }
    $dest = Join-Path $FusionScripts $item.Name
    Copy-Item -Path $item.Path -Destination $dest -Force
    Write-Host "Installed: $($item.Name)"
}

Write-Host ""
Write-Host "Done. In Fusion: Scripts and Add-Ins -> Run -> connect_pipeline_smoke"
Write-Host "Results JSON: $PluginDir\tests\output\connect_pipeline_fusion_smoke_results.json"
