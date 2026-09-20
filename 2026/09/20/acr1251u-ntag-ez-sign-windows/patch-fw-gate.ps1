# ACR1251 FW Update Tool の版数ゲートを書き換える。
#
# 更新処理は (num & 0x700) が特定の値かどうかで対象を絞る。
#   C4版: 0x700 を要求（7xx系）
#   M2版: 0x400 を要求（4xx系）
# num はリーダーが返す版数文字列の先頭3桁を16進として読んだ値で、
# 例えば "541.00" なら 0x541 になる。
#
# ここでは M2側のゲート (ldc.i4 0x700 / and / ldc.i4 0x400) を探し、
# 末尾の定数を実機の版数系統へ差し替える。
# オリジナルは変更せず、複製に対して当てる。

[CmdletBinding()]
param(
  # ACR1251CL_FW431.2.zip 等を展開したディレクトリ（exe と InitFile.ini と Patch/ がある場所）
  [Parameter(Mandatory = $true)][string]$ToolDir,
  # パッチ版の出力先ディレクトリ
  [Parameter(Mandatory = $true)][string]$OutDir,
  # 実機の版数の上位ニブル。541.00 なら 5
  [ValidateRange(0, 15)][int]$TargetFamily = 5
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $ToolDir)) { throw "ToolDir が見つからない: $ToolDir" }
$srcExe = Get-ChildItem $ToolDir -Filter '*.exe' | Select-Object -First 1
if (-not $srcExe) { throw "$ToolDir に exe が無い" }

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
Copy-Item (Join-Path $ToolDir '*') -Destination $OutDir -Recurse -Force
$exe = Join-Path $OutDir $srcExe.Name

Write-Host ("オリジナル : {0}" -f $srcExe.FullName)
Write-Host ("SHA-256    : {0}" -f (Get-FileHash $srcExe.FullName -Algorithm SHA256).Hash)

$bytes = [System.IO.File]::ReadAllBytes($exe)

# ldc.i4 0x700 / and / ldc.i4 0x400
$m2Gate = [byte[]](0x20, 0x00, 0x07, 0x00, 0x00, 0x5F, 0x20, 0x00, 0x04, 0x00, 0x00)
# ldc.i4 0x700 / and / ldc.i4 0x700  （C4側。触らない）
$c4Gate = [byte[]](0x20, 0x00, 0x07, 0x00, 0x00, 0x5F, 0x20, 0x00, 0x07, 0x00, 0x00)

function Find-Pattern([byte[]]$haystack, [byte[]]$needle) {
  $hits = @()
  for ($i = 0; $i -le $haystack.Length - $needle.Length; $i++) {
    $match = $true
    for ($j = 0; $j -lt $needle.Length; $j++) {
      if ($haystack[$i + $j] -ne $needle[$j]) { $match = $false; break }
    }
    if ($match) { $hits += $i }
  }
  return , $hits
}

$m2 = Find-Pattern $bytes $m2Gate
$c4 = Find-Pattern $bytes $c4Gate

Write-Host ("M2ゲート   : {0}" -f (($m2 | ForEach-Object { '0x{0:X6}' -f $_ }) -join ', '))
Write-Host ("C4ゲート   : {0}" -f (($c4 | ForEach-Object { '0x{0:X6}' -f $_ }) -join ', '))

if ($m2.Count -eq 0) { throw 'M2ゲートのパターンが見つからない。ツールの版が違う可能性がある' }

# ldc.i4 のオペランドはリトルエンディアン4バイト。下位バイトが +8 の位置にある
foreach ($offset in $m2) { $bytes[$offset + 8] = [byte]$TargetFamily }
[System.IO.File]::WriteAllBytes($exe, $bytes)

Write-Host ''
Write-Host ("書き換え   : {0} 箇所  0x400 -> 0x{1:X}00" -f $m2.Count, $TargetFamily)
Write-Host ("出力       : {0}" -f $exe)
Write-Host ("サイズ     : {0} bytes" -f (Get-Item $exe).Length)
Write-Host ("SHA-256    : {0}" -f (Get-FileHash $exe -Algorithm SHA256).Hash)
