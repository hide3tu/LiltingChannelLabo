Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class PcscWatch {
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

  public static string Watch(int seconds) {
    IntPtr ctx;
    SCardEstablishContext(2, IntPtr.Zero, IntPtr.Zero, out ctx);
    uint len = 0;
    SCardListReaders(ctx, null, null, ref len);
    char[] buf = new char[len];
    SCardListReaders(ctx, null, buf, ref len);
    string reader = new string(buf).Split('\0')[0];
    var sb = new System.Text.StringBuilder();
    sb.AppendLine("reader=[" + reader + "]");
    READERSTATE[] st = new READERSTATE[1];
    st[0].szReader = reader;
    st[0].dwCurrentState = 0;
    st[0].rgbAtr = new byte[36];
    DateTime end = DateTime.Now.AddSeconds(seconds);
    uint last = 0xFFFFFFFF;
    int events = 0;
    while (DateTime.Now < end) {
      int rc = SCardGetStatusChange(ctx, 400, st, 1);
      uint e = st[0].dwEventState;
      if ((e & 0xFFFF) != (last & 0xFFFF)) {
        string f = "";
        if ((e & 0x0010) != 0) f += "EMPTY ";
        if ((e & 0x0020) != 0) f += "PRESENT ";
        if ((e & 0x0200) != 0) f += "MUTE ";
        if ((e & 0x0400) != 0) f += "UNPOWERED ";
        string atr = "";
        for (int i = 0; i < st[0].cbAtr; i++) atr += st[0].rgbAtr[i].ToString("X2") + " ";
        sb.AppendLine(DateTime.Now.ToString("HH:mm:ss") + "  [" + f.Trim() + "]  ATR=" + atr.Trim());
        last = e;
        events++;
      }
      st[0].dwCurrentState = e & ~(uint)0x0002;
    }
    sb.AppendLine("状態変化: " + events + " 回");
    return sb.ToString();
  }
}
'@
"=== 15秒間監視します。カードをリーダーの上でゆっくり動かしてください ==="
[PcscWatch]::Watch(15)
