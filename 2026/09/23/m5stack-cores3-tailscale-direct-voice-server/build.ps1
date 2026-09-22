param([string]$Image = 'espressif/idf:v6.0')
$ErrorActionPreference = 'Stop'
$projectPath = $PSScriptRoot
# The published snapshot builds independently of the original repository layout.
& docker run --rm --mount "type=bind,source=$projectPath,target=/project" `
    --workdir /project `
    --env IDF_GIT_SAFE_DIR=/project $Image idf.py build
if ($LASTEXITCODE -ne 0) { throw "ESP-IDF build failed ($LASTEXITCODE)" }
