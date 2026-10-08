[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$VideoPath,
    [Parameter(Mandatory)][string]$OutputDirectory,
    [ValidateRange(0.1, 3600)][double]$IntervalSeconds = 5,
    [ValidateRange(1, 10000)][int]$MaxFrames = 120,
    [ValidateRange(2, 31)][int]$JpegQuality = 3,
    [string]$FfmpegPath,
    [string]$FfprobePath
)

$ErrorActionPreference = 'Stop'
$video = (Resolve-Path -LiteralPath $VideoPath).Path
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$output = (Resolve-Path -LiteralPath $OutputDirectory).Path

if (-not $FfmpegPath) {
    $command = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($command) { $FfmpegPath = $command.Source }
}
if (-not $FfmpegPath -or -not (Test-Path -LiteralPath $FfmpegPath)) {
    $python = Get-Command python -ErrorAction SilentlyContinue
    $fallback = Join-Path $PSScriptRoot 'extract_frames_cv.py'
    if (-not $python -or -not (Test-Path -LiteralPath $fallback)) {
        throw 'Neither FFmpeg nor the Python/OpenCV fallback is available.'
    }
    & $python.Source $fallback $video $output --interval $IntervalSeconds --max-frames $MaxFrames
    if ($LASTEXITCODE -ne 0) { throw "OpenCV frame extraction failed with exit code $LASTEXITCODE." }
    return
}
if (-not $FfprobePath) {
    $probe = Get-Command ffprobe -ErrorAction SilentlyContinue
    if ($probe) { $FfprobePath = $probe.Source }
}

$pattern = Join-Path $output 'frame-%06d.jpg'
& $FfmpegPath -hide_banner -loglevel error -i $video -vf "fps=1/$IntervalSeconds" `
    -frames:v $MaxFrames -q:v $JpegQuality -y $pattern
if ($LASTEXITCODE -ne 0) { throw "FFmpeg failed with exit code $LASTEXITCODE." }

$duration = $null
if ($FfprobePath -and (Test-Path -LiteralPath $FfprobePath)) {
    $rawDuration = & $FfprobePath -v error -show_entries format=duration -of default=nw=1:nk=1 $video
    if ($LASTEXITCODE -eq 0) {
        $duration = [double]::Parse($rawDuration.Trim(), [Globalization.CultureInfo]::InvariantCulture)
    }
}

$frames = @(Get-ChildItem -LiteralPath $output -Filter 'frame-*.jpg' -File | Sort-Object Name)
$records = for ($index = 0; $index -lt $frames.Count; $index++) {
    [ordered]@{
        index = $index + 1
        timestamp_s = [Math]::Round($index * $IntervalSeconds, 3)
        file = $frames[$index].FullName
    }
}
$manifest = [ordered]@{
    source = $video
    duration_s = $duration
    sampling = @{ mode = 'interval'; interval_s = $IntervalSeconds; max_frames = $MaxFrames }
    frame_count = $frames.Count
    frames = @($records)
}
$manifestPath = Join-Path $output 'frames-manifest.json'
[IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
$manifestPath
