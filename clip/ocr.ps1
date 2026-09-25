# OCR intégré à Windows (Windows.Media.Ocr, sans installation) : texte lisible dans des images.
# Usage : powershell -NoProfile -ExecutionPolicy Bypass -File ocr.ps1 image1.png image2.png ...
# Sortie : une ligne JSON par image {"f": chemin, "lignes": [texte, ...]}
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Images)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, [Type]$type) {
    $t = $asTask.MakeGenericMethod($type).Invoke($null, @($op)); $t.Wait(-1) | Out-Null; $t.Result
}
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if (-not $engine) { Write-Output '{"erreur": "OCR Windows indisponible"}'; exit 1 }
foreach ($img in $Images) {
    try {
        $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync((Resolve-Path $img).Path)) ([Windows.Storage.StorageFile])
        $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
        $dec = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bmp = Await ($dec.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $res = Await ($engine.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult])
        $lignes = @($res.Lines | ForEach-Object { $_.Text })
        $stream.Dispose()
        [pscustomobject]@{ f = $img; lignes = $lignes } | ConvertTo-Json -Compress
    } catch {
        [pscustomobject]@{ f = $img; erreur = $_.Exception.Message } | ConvertTo-Json -Compress
    }
}
