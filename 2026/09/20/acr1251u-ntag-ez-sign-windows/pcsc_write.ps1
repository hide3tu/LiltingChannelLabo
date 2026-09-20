$sig = @'
[DllImport("winscard.dll", CharSet=CharSet.Unicode, SetLastError=true)]
public static extern int SCardEstablishContext(uint s, IntPtr a, IntPtr b, out IntPtr ctx);
[DllImport("winscard.dll", CharSet=CharSet.Unicode, SetLastError=true)]
public static extern int SCardListReaders(IntPtr ctx, string g, char[] r, ref uint len);
[DllImport("winscard.dll", CharSet=CharSet.Unicode, SetLastError=true)]
public static extern int SCardConnect(IntPtr ctx, string reader, uint share, uint protocols, out IntPtr card, out uint activeProto);
[DllImport("winscard.dll", CharSet=CharSet.Unicode, SetLastError=true)]
public static extern int SCardStatus(IntPtr card, char[] rn, ref uint rnLen, out uint state, out uint proto, byte[] atr, ref uint atrLen);
[DllImport("winscard.dll", SetLastError=true)]
public static extern int SCardTransmit(IntPtr card, IntPtr pioSend, byte[] send, uint sendLen, IntPtr pioRecv, byte[] recv, ref uint recvLen);
[DllImport("winscard.dll", SetLastError=true)]
public static extern int SCardDisconnect(IntPtr card, uint disposition);
'@
$t = Add-Type -MemberDefinition $sig -Name WSW -Namespace PCSCW -PassThru
function Hexs([byte[]]$b, [int]$n) { if ($n -le 0) { return '' } ; (($b[0..($n-1)]) | ForEach-Object { '{0:X2}' -f $_ }) -join ' ' }

$ctx = [IntPtr]::Zero
[void]$t::SCardEstablishContext(2, [IntPtr]::Zero, [IntPtr]::Zero, [ref]$ctx)
$len = 0
[void]$t::SCardListReaders($ctx, $null, $null, [ref]$len)
$bb = New-Object char[] $len
[void]$t::SCardListReaders($ctx, $null, $bb, [ref]$len)
$reader = (-join $bb).Split([char]0) | Where-Object { $_ } | Select-Object -First 1
"READER: [$reader]"

$card = [IntPtr]::Zero; $proto = 0
$rc = $t::SCardConnect($ctx, $reader, 2, 3, [ref]$card, [ref]$proto)
"SCardConnect rc=0x{0:X8} proto=$proto" -f $rc
if ($rc -ne 0) { "カードが載っていない可能性があります"; exit 1 }
$rn = New-Object char[] 256; $rnLen = 256; $st = 0; $pr = 0
$atr = New-Object byte[] 64; $atrLen = 64
[void]$t::SCardStatus($card, $rn, [ref]$rnLen, [ref]$st, [ref]$pr, $atr, [ref]$atrLen)
"ATR : " + (Hexs $atr $atrLen)

$pci = [System.Runtime.InteropServices.Marshal]::AllocHGlobal(8)
[System.Runtime.InteropServices.Marshal]::WriteInt32($pci, 0, $proto)
[System.Runtime.InteropServices.Marshal]::WriteInt32($pci, 4, 8)
function Apdu([string]$label, [byte[]]$cmd) {
  $recv = New-Object byte[] 258; $rl = 258
  $rc = $script:t::SCardTransmit($script:card, $script:pci, $cmd, $cmd.Length, [IntPtr]::Zero, $recv, [ref]$rl)
  if ($rc -ne 0) { Write-Host ("{0,-28} rc=0x{1:X8}" -f $label, $rc); return $null }
  $sw = Hexs $recv[($rl-2)..($rl-1)] 2
  $data = if ($rl -gt 2) { Hexs $recv ($rl-2) } else { '' }
  Write-Host ("{0,-28} SW={1}  {2}" -f $label, $sw, $data)
  if ($rl -gt 2) { return $recv[0..($rl-3)] } else { return $null }
}

# NDEF: URI record  https://lilting.ch/
# 03 <len> D1 01 0C 55 04 "lilting.ch/" FE
$uri = "lilting.ch/"
$uriBytes = [System.Text.Encoding]::ASCII.GetBytes($uri)
$rec = @(0xD1, 0x01, ($uriBytes.Length + 1), 0x55, 0x04) + $uriBytes
$tlv = @(0x03, $rec.Length) + $rec + @(0xFE)
while ($tlv.Count % 4 -ne 0) { $tlv += 0x00 }
"書き込むNDEF ($($tlv.Count) バイト): " + (($tlv | ForEach-Object { '{0:X2}' -f $_ }) -join ' ')

"`n=== 書き込み（ページ4から） ==="
$page = 4
for ($i = 0; $i -lt $tlv.Count; $i += 4) {
  $chunk = [byte[]]($tlv[$i..($i+3)])
  $cmd = [byte[]](0xFF,0xD6,0x00,$page,0x04) + $chunk
  [void](Apdu ("page {0:X2} <- {1}" -f $page, ((($chunk) | ForEach-Object { '{0:X2}' -f $_ }) -join ' ')) $cmd)
  $page++
}

"`n=== 読み戻し ==="
[void](Apdu "page 04-07" ([byte[]](0xFF,0xB0,0x00,0x04,0x10)))
[void](Apdu "page 08-0B" ([byte[]](0xFF,0xB0,0x00,0x08,0x10)))
[void]$t::SCardDisconnect($card, 0)
