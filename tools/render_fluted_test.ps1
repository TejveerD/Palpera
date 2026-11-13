# Final-quality test stretch for the fluted sequence (run from C:\Users\tejve\Palpera).
#   powershell -ExecutionPolicy Bypass -File tools\render_fluted_test.ps1
# Writes PNGs to renders\fl_test\seq\. Re-running skips frames already done.
$blender = Get-ChildItem "C:\Program Files\Blender Foundation\*\blender.exe" -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
if (-not $blender) { Write-Error "blender.exe not found under C:\Program Files\Blender Foundation"; exit 1 }
Write-Host "Using $blender"
$env:EXP = "fl_site"
$env:EXP_POD = "F2EFE6"
$env:EXP_POD_GLASS = "0"
$env:EXP_RES = "1600x900"
$env:EXP_SAMPLES = "256"
$env:EXP_DEVICE = "GPU"
$env:EXP_SEQ = "299"
# Stretch A: start of the move, glass in view (banding, ghosting at slow speed).
# Stretch B: the middle of the move, where the camera moves fastest.
$env:EXP_FRAMES = "1-30,136-165"
$env:EXP_OUT = "$PSScriptRoot\..\renders\fl_test"
& $blender -b --factory-startup -P "$PSScriptRoot\palpera_fluted.py" 2>&1 |
    Select-String "EXP|Error|Traceback"
