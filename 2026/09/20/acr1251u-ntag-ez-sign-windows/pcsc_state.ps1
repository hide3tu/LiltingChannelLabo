Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class PcscState {
  [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
  public struct READERSTATE {
    public string szReader;
    public IntPtr pvUserData;
    public uint dwCurrentState;
    public uint dwEventState;
    public uint cbAtr;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst=36)] public byte[] rgbAtr;
  }
  [DllImport("winscard.dll", CharSet=CharSet.Unicode)]
  public static extern int SCardEstablishContext(uint s, IntPtr a, IntPtr b, out IntPtr ctx);
  [DllImport("winscard.dll", CharSet=CharSet.Unicode)]
  public static extern int SCardListReaders(IntPtr ctx, string g, char[] r, ref uint len);
  [DllImport("winscard.dll", CharSet=CharSet.Unicode)]
  public static extern int SCardGetStatusChange(IntPtr ctx, uint to, [In,Out] READERSTATE[] st, uint n);

  public static string Run() {
    IntPtr ctx;
    SCardEstablishContext(2, IntPtr.Zero, IntPtr.Zero, out ctx);
    uint len = 0;
    SCardListReaders(ctx, null, null, ref len);
    char[] buf = new char[len];
    SCardListReaders(ctx, null, buf, ref len);
    string reader = new string(buf).Split('\0')[0];

    READERSTATE[] st = new READERSTATE[1];
    st[0].szReader = reader;
    st[0].dwCurrentState = 0;
    st[0].rgbAtr = new byte[36];
    int rc = SCardGetStatusChange(ctx, 1500, st, 1);
    uint e = st[0].dwEventState;
    string flags = "";
    if ((e & 0x0004) != 0) flags += "UNKNOWN ";
    if ((e & 0x0008) != 0) flags += "UNAVAILABLE ";
    if ((e & 0x0010) != 0) flags += "EMPTY ";
    if ((e & 0x0020) != 0) flags += "PRESENT ";
    if ((e & 0x0040) != 0) flags += "ATRMATCH ";
    if ((e & 0x0100) != 0) flags += "INUSE ";
    if ((e & 0x0200) != 0) flags += "MUTE ";
    if ((e & 0x0400) != 0) flags += "UNPOWERED ";
    string atr = "";
    for (int i = 0; i < st[0].cbAtr; i++) atr += st[0].rgbAtr[i].ToString("X2") + " ";
    return string.Format("reader=[{0}]\nrc=0x{1:X8}\neventState=0x{2:X8}  [{3}]\ncbAtr={4}\nATR={5}",
      reader, rc, e, flags.Trim(), st[0].cbAtr, atr.Trim());
  }
}
'@
[PcscState]::Run()
