$sig = @'
[DllImport("winscard.dll", CharSet=CharSet.Unicode, SetLastError=true)]
public static extern int SCardEstablishContext(uint dwScope, IntPtr r1, IntPtr r2, out IntPtr ctx);
[DllImport("winscard.dll", CharSet=CharSet.Unicode, SetLastError=true)]
public static extern int SCardListReaders(IntPtr ctx, string groups, char[] readers, ref uint len);
[DllImport("winscard.dll", CharSet=CharSet.Unicode, SetLastError=true)]
public static extern int SCardConnect(IntPtr ctx, string reader, uint share, uint protocols, out IntPtr card, out uint activeProto);
[DllImport("winscard.dll", SetLastError=true)]
public static extern int SCardControl(IntPtr card, uint ctlCode, byte[] inBuf, uint inLen, byte[] outBuf, uint outLen, out uint returned);
[DllImport("winscard.dll", SetLastError=true)]
public static extern int SCardDisconnect(IntPtr card, uint disposition);
'@
$t = Add-Type -MemberDefinition $sig -Name WS5 -Namespace PCSC5 -PassThru

$ctx = [IntPtr]::Zero
[void]$t::SCardEstablishContext(2, [IntPtr]::Zero, [IntPtr]::Zero, [ref]$ctx)
$len = 0
[void]$t::SCardListReaders($ctx, $null, $null, [ref]$len)
$b = New-Object char[] $len
[void]$t::SCardListReaders($ctx, $null, $b, [ref]$len)
$reader = (-join $b).Split([char]0) | Where-Object { $_ } | Select-Object -First 1
"READER: [$reader]"

$card = [IntPtr]::Zero; $proto = 0
$rc = $t::SCardConnect($ctx, $reader, 3, 0, [ref]$card, [ref]$proto)
if ($rc -ne 0) { "SCardConnect(DIRECT) rc=0x{0:X8}" -f $rc; exit 1 }

$CTL = 0x003136B0   # SCARD_CTL_CODE(3500)

function Esc([string]$label, [byte[]]$cmd) {
  $out = New-Object byte[] 256
  $ret = 0
  $rc = $script:t::SCardControl($script:card, $script:CTL, $cmd, $cmd.Length, $out, $out.Length, [ref]$ret)
  $cmdHex = ($cmd | ForEach-Object { '{0:X2}' -f $_ }) -join ' '
  if ($rc -eq 0 -and $ret -gt 0) {
    $bytes = $out[0..($ret-1)]
    $hex = ($bytes | ForEach-Object { '{0:X2}' -f $_ }) -join ' '
    $ascii = -join ($bytes | ForEach-Object { if ($_ -ge 32 -and $_ -lt 127) { [char]$_ } else { '.' } })
    "{0,-34} [{1}]`n    -> {2}   |{3}|" -f $label, $cmdHex, $hex, $ascii
  } else {
    "{0,-34} [{1}]`n    -> rc=0x{2:X8}" -f $label, $cmdHex, $rc
  }
}

Esc "ACR122 Get Firmware"            ([byte[]](0xFF,0x00,0x48,0x00,0x00))
Esc "ACR122 Get PICC Oper Param"     ([byte[]](0xFF,0x00,0x50,0x00,0x00))
Esc "ACR1251 Get Firmware"           ([byte[]](0xE0,0x00,0x00,0x18,0x00))
Esc "ACR1251 Get Serial"             ([byte[]](0xE0,0x00,0x00,0x33,0x00))
Esc "ACR1251 Read PICC Oper Param"   ([byte[]](0xE0,0x00,0x00,0x20,0x00))
Esc "ACR1251 Read Auto PICC Polling" ([byte[]](0xE0,0x00,0x00,0x23,0x00))
Esc "ACR1251 Read Antenna status"    ([byte[]](0xE0,0x00,0x00,0x25,0x00))

[void]$t::SCardDisconnect($card, 0)
