function Get-LocalIpAddresses {
    $addresses = @()
    try {
        $addresses = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
            Where-Object { $_.IPAddress -notlike '169.254*' -and $_.IPAddress -ne '127.0.0.1' } |
            Select-Object -ExpandProperty IPAddress
    } catch {
        $addresses = @()
    }
    return @($addresses)
}

function Test-TcpPort {
    param([string]$HostName, [int]$Port, [double]$TimeoutSeconds = 2)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $async = $client.BeginConnect($HostName, $Port, $null, $null)
        $ok = $async.AsyncWaitHandle.WaitOne([int]($TimeoutSeconds * 1000), $false)
        if (-not $ok) {
            $client.Close()
            return [pscustomobject]@{ host = $HostName; port = $Port; status = 'port_unreachable'; message = 'timeout'; next_action = 'Verify host, firewall, and service listener.' }
        }
        $client.EndConnect($async)
        $client.Close()
        return [pscustomobject]@{ host = $HostName; port = $Port; status = 'ok'; message = 'port reachable'; next_action = $null }
    } catch {
        return [pscustomobject]@{ host = $HostName; port = $Port; status = 'port_unreachable'; message = $_.Exception.Message; next_action = 'Verify host, firewall, and service listener.' }
    }
}

function Test-HttpEndpoint {
    param([string]$Url, [double]$TimeoutSeconds = 2)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec ([int][Math]::Ceiling($TimeoutSeconds)) -ErrorAction Stop
        return [pscustomobject]@{ url = $Url; status = 'ok'; http_status = $response.StatusCode; message = 'http reachable'; next_action = $null }
    } catch {
        return [pscustomobject]@{ url = $Url; status = 'remote_unreachable'; message = $_.Exception.Message; next_action = 'Verify endpoint and network route.' }
    }
}
