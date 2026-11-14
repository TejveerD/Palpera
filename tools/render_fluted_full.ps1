# Full fluted render for the site: the 450-frame camera move and the three
# colour stills (sand on brown, graphite on smoke, silver on clear).
# Run from C:\Users\tejve\Palpera:
#   powershell -ExecutionPolicy Bypass -File tools\render_fluted_full.ps1
# Writes JPEGs (quality 98) to renders\fl_full\. Re-running skips frames already done.
$blender = Get-ChildItem "C:\Program Files\Blender Foundation\*\blender.exe" -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
if (-not $blender) { Write-Error "blender.exe not found under C:\Program Files\Blender Foundation"; exit 1 }
Write-Host "Using $blender"
$script = "$PSScriptRoot\palpera_fluted.py"
$out = "$PSScriptRoot\..\renders\fl_full"
$env:EXP = "fl_site"
$env:EXP_POD_GLASS = "0"
$env:EXP_RES = "1600x900"
$env:EXP_SAMPLES = "256"
$env:EXP_DEVICE = "GPU"
$env:EXP_FORMAT = "JPEG"
$env:EXP_JPEG_Q = "98"

# 1. The camera move: white pod on the green frame, 450 frames.
$env:EXP_POD = "F2EFE6"; $env:EXP_FRAME = "green"; $env:EXP_POD_METAL = "0"
$env:EXP_SEQ = "450"; $env:EXP_OUT = $out
& $blender -b --factory-startup -P $script 2>&1 | Select-String "EXP|Error|Traceback"
Remove-Item Env:EXP_SEQ

# 2. Colour stills at the close-up (also writes anchors.json).
$env:EXP_T = "1"
foreach ($c in @(@("sand", "D8C7A8", "brown", "0"), @("graphite", "3A3D45", "smoke", "0"), @("silver", "C9CCD3", "clear", "1"))) {
    $env:EXP_POD = $c[1]; $env:EXP_FRAME = $c[2]; $env:EXP_POD_METAL = $c[3]
    $env:EXP_OUT = "$out\stills\$($c[0])"
    & $blender -b --factory-startup -P $script 2>&1 | Select-String "EXP|Error|Traceback"
}
Write-Host "Done. Upload the folder renders\fl_full."
