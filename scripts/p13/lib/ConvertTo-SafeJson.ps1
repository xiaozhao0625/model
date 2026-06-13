function ConvertTo-SafeObject {
    param([Parameter(ValueFromPipeline = $true)]$InputObject)
    process {
        $sensitive = '(?i)(password|passwd|pwd|secret|token|api[_-]?key|apikey|access[_-]?key|private[_-]?key|credential|DATABASE_URL)'
        if ($null -eq $InputObject) { return $null }
        if ($InputObject -is [string]) {
            if ($InputObject -match $sensitive -or $InputObject -match '://[^:/@\s]+:[^@\s]+@') {
                return '[REDACTED]'
            }
            return $InputObject
        }
        if ($InputObject -is [bool] -or $InputObject -is [int] -or $InputObject -is [long] -or $InputObject -is [double] -or $InputObject -is [decimal] -or $InputObject -is [datetime]) {
            return $InputObject
        }
        if ($InputObject -is [System.Collections.IDictionary]) {
            $safe = [ordered]@{}
            foreach ($key in $InputObject.Keys) {
                if ([string]$key -match $sensitive) {
                    $safe[$key] = '[REDACTED]'
                } else {
                    $safe[$key] = ConvertTo-SafeObject $InputObject[$key]
                }
            }
            return [pscustomobject]$safe
        }
        if ($InputObject -is [System.Collections.IEnumerable] -and -not ($InputObject -is [string])) {
            $items = @()
            foreach ($item in $InputObject) { $items += ConvertTo-SafeObject $item }
            return $items
        }
        if ($InputObject -is [psobject]) {
            $safe = [ordered]@{}
            foreach ($prop in $InputObject.PSObject.Properties) {
                if ($prop.Name -match $sensitive) {
                    $safe[$prop.Name] = '[REDACTED]'
                } else {
                    $safe[$prop.Name] = ConvertTo-SafeObject $prop.Value
                }
            }
            return [pscustomobject]$safe
        }
        return $InputObject
    }
}

function ConvertTo-SafeJson {
    param(
        [Parameter(Mandatory = $true, ValueFromPipeline = $true)]$InputObject,
        [int]$Depth = 10
    )
    process {
        ConvertTo-SafeObject $InputObject | ConvertTo-Json -Depth $Depth
    }
}

function Save-SafeJson {
    param(
        [Parameter(Mandatory = $true)]$InputObject,
        [Parameter(Mandatory = $true)][string]$Path,
        [int]$Depth = 10
    )
    $parent = Split-Path -Parent $Path
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    if ($InputObject -is [array] -and $InputObject.Count -eq 0) {
        '[]' | Set-Content -LiteralPath $Path -Encoding UTF8
        return
    }
    ConvertTo-SafeJson -InputObject $InputObject -Depth $Depth | Set-Content -LiteralPath $Path -Encoding UTF8
}
