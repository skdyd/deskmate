param([string]$Dir)
Add-Type -AssemblyName System.Drawing, System.Windows.Forms
$screens = [System.Windows.Forms.Screen]::AllScreens | Sort-Object { $_.Bounds.X }
$bmps = foreach ($s in $screens) { $b = New-Object System.Drawing.Bitmap $s.Bounds.Width, $s.Bounds.Height; $g = [System.Drawing.Graphics]::FromImage($b); $g.CopyFromScreen($s.Bounds.Location, [System.Drawing.Point]::Empty, $s.Bounds.Size); $g.Dispose(); $b }
$mouse = [System.Windows.Forms.Cursor]::Position
$mi = 0; for ($i = 0; $i -lt $screens.Count; $i++) { if ($screens[$i].Bounds.Contains($mouse)) { $mi = $i } }
$jpg = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | ? MimeType -eq 'image/jpeg'
$ep = New-Object System.Drawing.Imaging.EncoderParameters 1; $ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter ([System.Drawing.Imaging.Encoder]::Quality), 60L
function Save-Variant($name, $list, $totalW) {
  $aspect = 0.0; foreach ($b in $list) { $aspect += $b.Width / $b.Height }
  $h = [int][math]::Round($totalW / $aspect)
  $ws = @(); foreach ($b in $list) { $ws += [int][math]::Round($h * $b.Width / $b.Height) }
  $out = New-Object System.Drawing.Bitmap ([int](($ws | Measure -Sum).Sum)), ([int]$h)
  $g = [System.Drawing.Graphics]::FromImage($out); $g.InterpolationMode = 'HighQualityBicubic'; $x = 0
  for ($i = 0; $i -lt $list.Count; $i++) { $g.DrawImage($list[$i], $x, 0, $ws[$i], $h); $x += $ws[$i] }
  $g.Dispose(); $p = Join-Path $Dir "$name.jpg"; $out.Save($p, $jpg, $ep); "$name $($out.Width)x$($out.Height) $((Get-Item $p).Length) bytes"
}
Save-Variant 'A_both_2048' $bmps 2048
Save-Variant 'B_mouse_1024' @($bmps[$mi]) 1024
Save-Variant 'B2_mouse_1280' @($bmps[$mi]) 1280
Save-Variant 'B3_mouse_2048' @($bmps[$mi]) 2048
Save-Variant 'C_both_1600' $bmps 1600
"screens: $($screens.Count) mouse on #$mi"

