$sig = @'
[DllImport("winscard.dll", CharSet=CharSet.Unicode, SetLastError=true)]
public static extern int SCardEstablishContext(uint dwScope, IntPtr r1, IntPtr r2, out IntPtr ctx);
[DllImport("winscard.dll", CharSet=CharSet.Unicode, SetLastError=true)]
public static extern int SCardListReaders(IntPtr ctx, string groups, char[] readers, ref uint len);
[DllImport("winscard.dll", CharSet=CharSet.Unicode, SetLastError=true)]
public static extern int SCardConnect(IntPtr ctx, string reader, uint share, uint protocols, out IntPtr card, out uint activeProto);
[DllImport("winscard.dll", CharSet=CharSet.Unicode, SetLastError=true)]
public static extern int SCardStatus(IntPtr card, char[] readerName, ref uint readerLen, out uint state, out uint proto, byte[] atr, ref uint atrLen);
[DllImport("winscard.dll", SetLastError=true)]
public static extern int SCardTransmit(IntPtr card, IntPtr pioSend, byte[] send, uint sendLen, IntPtr pioRecv, byte[] recv, ref uint recvLen);
[DllImport("winscard.dll", SetLastError=true)]
public static extern int SCardDisconnect(IntPtr card, uint disposition);
'@
$t = Add-Type -MemberDefinition $sig -Name WS3 -Namespace PCSC3 -PassThru

function Hex([byte[]]$b, [int]$n) { if ($n -le 0) { return '' } ; (($b[0..($n-1)]) | ForEach-Object { '{0:X2}' -f $_ }) -join ' ' }

$ctx = [IntPtr]::Zero
[void]$t::SCardEstablishContext(2, [IntPtr]::Zero, [IntPtr]::Zero, [ref]$ctx)
$len = 0
[void]$t::SCardListReaders($ctx, $null, $null, [ref]$len)
$buf = New-Object char[] $len
[void]$t::SCardListReaders($ctx, $null, $buf, [ref]$len)
$reader = (-join $buf).Split([char]0) | Where-Object { $_ } | Select-Object -First 1

$card = [IntPtr]::Zero; $proto = 0
$rc = $t::SCardConnect($ctx, $reader, 2, 3, [ref]$card, [ref]$proto)   # SHARED, T0|T1
"SCardConnect rc=0x{0:X8} activeProtocol=$proto" -f $rc
if ($rc -ne 0) { "カードを認識できていない（0x8010000C = カードなし）"; exit 1 }

# ATR
$rn = New-Object char[] 256; $rnLen = 256; $st = 0; $pr = 0
$atr = New-Object byte[] 64; $atrLen = 64
$rc = $t::SCardStatus($card, $rn, [ref]$rnLen, [ref]$st, [ref]$pr, $atr, [ref]$atrLen)
"ATR  : " + (Hex $atr $atrLen)

# pioSendPci: SCARD_PCI_T0=1 / T1=2 structs are exported; build manually
$pci = [System.Runtime.InteropServices.Marshal]::AllocHGlobal(8)
[System.Runtime.InteropServices.Marshal]::WriteInt32($pci, 0, $proto)
[System.Runtime.InteropServices.Marshal]::WriteInt32($pci, 4, 8)

function Apdu([string]$label, [byte[]]$cmd) {
  $recv = New-Object byte[] 258; $rl = 258
  $rc = $script:t::SCardTransmit($script:card, $script:pci, $cmd, $cmd.Length, [IntPtr]::Zero, $recv, [ref]$rl)
  if ($rc -ne 0) { "{0,-22} rc=0x{1:X8}" -f $label, $rc; return }
  $sw = Hex $recv[($rl-2)..($rl-1)] 2
  $data = if ($rl -gt 2) { Hex $recv ($rl-2) } else { '' }
  "{0,-22} SW={1}  DATA={2}" -f $label, $sw, $data
}

Apdu "UID (FF CA 00 00 00)"   ([byte[]](0xFF,0xCA,0x00,0x00,0x00))
Apdu "ATS (FF CA 01 00 00)"   ([byte[]](0xFF,0xCA,0x01,0x00,0x00))
Apdu "page 00-03 (16B)"       ([byte[]](0xFF,0xB0,0x00,0x00,0x10))
Apdu "page 04-07 (16B)"       ([byte[]](0xFF,0xB0,0x00,0x04,0x10))
Apdu "page 08-0B (16B)"       ([byte[]](0xFF,0xB0,0x00,0x08,0x10))

[void]$t::SCardDisconnect($card, 0)
