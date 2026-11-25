# Starts Deskmate once per character, takes screenshots, then restores the original character.
# Must run via explorer.exe (char_tour.lnk) so it sees the real %APPDATA%.
# Usage: char_tour.ps1 [id,id,...]   (default: all characters)

$Root = 'C:\Users\jywhy\Desktop\deskmate AI'
$Out  = Join-Path $Root 'logs\tour'
$App  = Join-Path $Root 'app\Deskmate.exe'
$Set  = Join-Path $env:APPDATA 'deskmate\settings.json'
New-Item -ItemType Directory -Force $Out | Out-Null
$log = Join-Path $Out 'tour.log'
"$(Get-Date) start" | Out-File $log -Encoding utf8
Add-Type -AssemblyName System.Drawing, System.Windows.Forms
Add-Type @'
using System; using System.Runtime.InteropServices;
public class W {
 [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y);
 [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
 [DllImport("user32.dll")] public static extern IntPtr GetDC(IntPtr h);
 public delegate bool EP(IntPtr h, IntPtr l);
 [DllImport("user32.dll")] public static extern bool EnumWindows(EP f, IntPtr l);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 [StructLayout(LayoutKind.Sequential)] public struct R { public int L,T,Rt,B; }
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
 public static string Wins(uint[] pids) { var sb = new System.Text.StringBuilder();
  EnumWindows((h,l)=>{ uint p; GetWindowThreadProcessId(h,out p); if (Array.IndexOf(pids,p)>=0 && IsWindowVisible(h)) { R r; GetWindowRect(h,out r); sb.Append(r.L+","+r.T+","+r.Rt+","+r.B+" "); } return true; }, IntPtr.Zero); return sb.ToString(); }
 [DllImport("user32.dll")] public static extern int ReleaseDC(IntPtr h, IntPtr dc);
 [DllImport("gdi32.dll")] public static extern bool BitBlt(IntPtr d,int x,int y,int w,int h,IntPtr s,int sx,int sy,int op);
}
'@
[W]::SetProcessDPIAware() | Out-Null
$vs = [System.Windows.Forms.SystemInformation]::VirtualScreen
function Shot($name) {
  $bmp = New-Object System.Drawing.Bitmap $vs.Width, $vs.Height
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $hd = $g.GetHdc(); $sd = [W]::GetDC([IntPtr]::Zero)
  [W]::BitBlt($hd, 0, 0, $vs.Width, $vs.Height, $sd, $vs.X, $vs.Y, 0x40CC0020) | Out-Null
  [W]::ReleaseDC([IntPtr]::Zero, $sd) | Out-Null; $g.ReleaseHdc($hd)
  $bmp.Save((Join-Path $Out "$name.png"), [System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose(); $bmp.Dispose()
}
$name = if ($args.Count) { $args[0] } else { 'now' }
Shot $name
"wins: " + [W]::Wins([uint32[]]@(Get-Process Deskmate | % Id)) | Out-File (Join-Path $Out "$name.txt") -Encoding utf8
