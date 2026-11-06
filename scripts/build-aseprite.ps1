[CmdletBinding()]
param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [ValidateRange(1,64)][int]$Jobs = 8
)
$ErrorActionPreference = 'Stop'
$buildRoot = Join-Path ([IO.Path]::GetFullPath($ProjectRoot)) '.local/aseprite'
$sourceDir = Join-Path $buildRoot 'source'
$depsDir = Join-Path $buildRoot 'deps'
$skiaDir = Join-Path $depsDir 'skia'
$buildDir = Join-Path $buildRoot 'build'
$logsDir = Join-Path $buildRoot 'logs'
New-Item -ItemType Directory -Force -Path $buildRoot,$depsDir,$logsDir | Out-Null

# The official release source archive includes all required submodules.
$sourceUrl = 'https://github.com/aseprite/aseprite/releases/download/v1.3.18.6/Aseprite-v1.3.18.6-Source.zip'
$skiaUrl = 'https://github.com/aseprite/skia/releases/download/m124-08a5439a6b/Skia-Windows-Release-x64.zip'
$sourceHash = 'fa9dd07a0c2a5ec91a4166333296bbb9e5c237933b59875d0cfee849d2358306'
$skiaHash = '5a371a4b2819bb4eb96e36cd75fa623585e1d5477e253a970302b6f2471b6934'
function Get-VerifiedArchive([string]$Url, [string]$Hash, [string]$Destination, [string]$Marker) {
    $archive = Join-Path $depsDir ($Url.Split('/')[-1])
    if (-not (Test-Path -LiteralPath $archive)) { Invoke-WebRequest -Uri $Url -OutFile $archive }
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Hash) {
        throw "SHA-256 mismatch: $archive"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $Destination $Marker))) {
        Expand-Archive -LiteralPath $archive -DestinationPath $Destination -Force
    }
}
Get-VerifiedArchive $sourceUrl $sourceHash $sourceDir 'third_party/tinyxml2/tinyxml2.cpp'
Get-VerifiedArchive $skiaUrl $skiaHash $skiaDir 'out/Release-x64/skia.lib'

$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
if (-not (Test-Path -LiteralPath $vswhere)) { throw 'Install Visual Studio 2022 Build Tools with Desktop development with C++ and Windows SDK 10.0.26100.0.' }
$vsPath = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vsPath) { throw 'Visual Studio C++ tools were not found.' }
$vsDevCmd = Join-Path $vsPath 'Common7/Tools/VsDevCmd.bat'
# cmd is used only to load the compiler environment, never for file operations.
$vsEnv = & $env:ComSpec /d /s /c "`"`"$vsDevCmd`" -no_logo -arch=x64 -host_arch=x64 >nul && set`""
if ($LASTEXITCODE -ne 0) { throw 'Loading the Visual Studio environment failed.' }
foreach ($line in $vsEnv) {
    $separator = $line.IndexOf('=')
    if ($separator -gt 0) { [Environment]::SetEnvironmentVariable($line.Substring(0,$separator), $line.Substring($separator+1), 'Process') }
}
$cmake = Join-Path $vsPath 'Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe'
$ninja = Join-Path $vsPath 'Common7/IDE/CommonExtensions/Microsoft/CMake/Ninja/ninja.exe'
if (-not (Test-Path -LiteralPath $cmake)) { $cmake = (Get-Command cmake -ErrorAction Stop).Source }
if (-not (Test-Path -LiteralPath $ninja)) { $ninja = (Get-Command ninja -ErrorAction Stop).Source }
$skiaLibDir = Join-Path $skiaDir 'out/Release-x64'
$configureLog = Join-Path $logsDir 'configure.log'
& $cmake -S $sourceDir -B $buildDir -G Ninja "-DCMAKE_MAKE_PROGRAM=$ninja" '-DCMAKE_BUILD_TYPE=RelWithDebInfo' '-DLAF_BACKEND=skia' "-DSKIA_DIR=$skiaDir" "-DSKIA_LIBRARY_DIR=$skiaLibDir" "-DSKIA_LIBRARY=$skiaLibDir/skia.lib" *> $configureLog
if ($LASTEXITCODE -ne 0) { Get-Content -LiteralPath $configureLog -Tail 80; throw "CMake failed; see $configureLog" }
$buildLog = Join-Path $logsDir 'build.log'
& $cmake --build $buildDir --target aseprite --parallel $Jobs *> $buildLog
if ($LASTEXITCODE -ne 0) { Get-Content -LiteralPath $buildLog -Tail 80; throw "Build failed; see $buildLog" }
$exe = Join-Path $buildDir 'bin/aseprite.exe'
$version = (& $exe --version | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Built Aseprite failed its version check.' }
[ordered]@{
    source_repository = 'https://github.com/aseprite/aseprite'
    source_tag = 'v1.3.18.6'
    source_commit = '331e898ef405d919539c03fd1675691cfa16c3a3'
    source_archive = $sourceUrl
    source_sha256 = $sourceHash
    skia_tag = 'm124-08a5439a6b'
    skia_archive = $skiaUrl
    skia_sha256 = $skiaHash
    visual_studio = $vsPath
    cmake_version = (& $cmake --version | Select-Object -First 1)
    ninja_version = (& $ninja --version | Out-String).Trim()
    configuration = 'RelWithDebInfo'
    backend = 'skia'
    executable = $exe
    executable_sha256 = (Get-FileHash -LiteralPath $exe).Hash.ToLowerInvariant()
    version = $version
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $buildRoot 'build-provenance.json') -Encoding utf8
Write-Output $version
Write-Output "Aseprite executable: $exe"
