param(
    [ValidatePattern('^[E-Z]$')]
    [string]$Drive = 'R'
)

$ErrorActionPreference = 'Stop'
$admissionProject = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$admissionDriveRoot = "${Drive}:\"
if (Test-Path $admissionDriveRoot) {
    throw "Ổ ${Drive}: đang được sử dụng. Chọn ký tự khác với -Drive."
}
if (-not (Test-Path (Join-Path $admissionProject '.venv\Scripts\python.exe'))) {
    throw 'Cần tạo .venv và cài package cùng nhóm spark,dev trước khi cấu hình.'
}

subst "${Drive}:" $admissionProject
if ($LASTEXITCODE -ne 0) {
    throw 'Không tạo được đường dẫn ổ đĩa cho Spark.'
}
$admissionJarDirectory = Join-Path $admissionDriveRoot 'artifacts\windows'
New-Item -ItemType Directory -Force $admissionJarDirectory | Out-Null
$admissionJar = Join-Path $admissionJarDirectory 'hadoop-bare-naked-local-fs-0.1.0.jar'
$admissionExpectedHash = 'E0CC30FB0531EB0B59468DC0ABF5B257533D2365B5E9F45E795EDD707AA78C62'
if (-not (Test-Path $admissionJar)) {
    Invoke-WebRequest 'https://repo.maven.apache.org/maven2/com/globalmentor/hadoop-bare-naked-local-fs/0.1.0/hadoop-bare-naked-local-fs-0.1.0.jar' -OutFile $admissionJar
}
if ((Get-FileHash $admissionJar -Algorithm SHA256).Hash -ne $admissionExpectedHash) {
    throw 'Checksum của thư viện filesystem không khớp phiên bản đã kiểm chứng.'
}

$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = Join-Path $admissionDriveRoot 'src'
$env:SPARK_HOME = Join-Path $admissionDriveRoot '.venv\Lib\site-packages\pyspark'
$env:PYSPARK_PYTHON = Join-Path $admissionDriveRoot '.venv\Scripts\python.exe'
$env:ADMISSION_WINDOWS_FS_JAR = $admissionJar
$env:PATH = (Join-Path $admissionDriveRoot '.venv\Scripts') + ';' + $env:PATH
Set-Location $admissionDriveRoot
Write-Output "Đã cấu hình Spark local qua ổ ${Drive}:. Chạy .venv\Scripts\python.exe để dùng môi trường dự án."
