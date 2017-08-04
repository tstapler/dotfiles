param (
    [parameter(ValueFromPipeline=$True)]
    [System.Double]$time = 0
)
Write-Host "The Time Is" $time
$origin = New-Object -Type DateTime -ArgumentList 1970, 1, 1, 0, 0, 0, 0
Write-Host $origin.AddSeconds($time)  