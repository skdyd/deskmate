$src = Join-Path $env:LOCALAPPDATA 'Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\deskmate\character\sparkle\model\motions'
$dst = Join-Path $env:APPDATA 'deskmate\character\sparkle\model\motions'
robocopy $src $dst *.json *.orig /NJH /NJS /NP | Out-File 'C:\Users\jywhy\Desktop\deskmate AI\logs\copy_motions.log' -Encoding utf8
