# To run from Task Scheduler
# Add the command: powershell.exe
# With these arguments: -ExecutionPolicy Bypass -File "D:\data\kapipy_downloads\run-changesets.ps1" -f config_filename.yaml -c
# (substituting the correct configuration file name)
# Set the 'start in' directory to the directory this file and changesets.py is in. e.g. D:\data\kapipy_downloads

# --- SETTINGS ---
$pythonPath = "C:/ArcGIS/Server/framework/runtime/ArcGIS/bin/Python/envs/arcgispro-py3-clone/python.exe"
$pythonFile = "changesets.py"
$logDir     = Join-Path (Get-Location) "data\logs"

# --- TIMESTAMP (safe: yyyyMMdd_HHmmss) ---
$timestamp  = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile    = Join-Path $logDir ("error_logs_{0}.log" -f $timestamp)

# --- ENSURE LOG DIRECTORY EXISTS ---
if (-not (Test-Path $logDir)) {
    New-Item -Path $logDir -ItemType Directory | Out-Null
}

# Run Python and capture only stderr
$processOutput = & $pythonPath (Join-Path (Get-Location) $pythonFile) @args *>&1
if ($LASTEXITCODE -ne 0) {
    if (-not (Test-Path $logDir)) {
        New-Item -Path $logDir -ItemType Directory | Out-Null
    }
    $processOutput | Out-File -FilePath $logFile -Encoding UTF8
}
