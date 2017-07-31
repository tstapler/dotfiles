$a = (Get-Date).ToUniversalTime().Date
$b = New-Object -Type DateTime -ArgumentList 1970, 1, 1, 0, 0, 0, 0
Write-Output ([Math]::Floor(([Timespan] $a.Subtract($b)).TotalSeconds))

