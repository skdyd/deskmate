# Copies character model files from Claude's virtualized AppData (MSIX LocalCache) to the real %APPDATA%\deskmate.
# Must be started through explorer.exe (see make via sync_characters.lnk) so it runs outside the MSIX container.
$src = Join-Path $env:LOCALAPPDATA 'Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\deskmate\character'
$dst = Join-Path $env:APPDATA 'deskmate\character'
$log = 'C:\Users\jywhy\Desktop\deskmate AI\logs\sync_characters.log'
"$(Get-Date) sync $src -> $dst" | Out-File $log -Encoding utf8
Get-ChildItem $src -Directory | ForEach-Object {
  $m = Join-Path $_.FullName 'model'
  if (Test-Path $m) {
    robocopy $m (Join-Path $dst "$($_.Name)\model") model.moc3 model.model3.json model.physics3.json *.orig *.canvas-orig *.clamp-orig /NJH /NJS /NP | Out-File $log -Append -Encoding utf8
  }
}
"done $(Get-Date)" | Out-File $log -Append -Encoding utf8
