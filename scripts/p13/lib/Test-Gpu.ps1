function Test-Gpu {
    $cmd = Get-Command nvidia-smi -ErrorAction SilentlyContinue
    if (-not $cmd) {
        return [pscustomobject]@{
            status = 'missing'
            nvidia_smi_available = $false
            gpu_names = @()
            driver_version = $null
            message = 'nvidia-smi not found'
            next_action = 'Install NVIDIA driver manually.'
        }
    }
    try {
        $query = & nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>&1
        $gpus = @()
        foreach ($line in $query) {
            $parts = $line -split ','
            if ($parts.Count -ge 3) {
                $gpus += [pscustomobject]@{
                    name = $parts[0].Trim()
                    driver_version = $parts[1].Trim()
                    memory_total = $parts[2].Trim()
                }
            }
        }
        return [pscustomobject]@{
            status = 'ok'
            nvidia_smi_available = $true
            gpu_names = @($gpus | ForEach-Object { $_.name })
            driver_version = $(if ($gpus.Count -gt 0) { $gpus[0].driver_version } else { $null })
            gpus = $gpus
            message = 'GPU query completed'
            next_action = $null
        }
    } catch {
        return [pscustomobject]@{
            status = 'error'
            nvidia_smi_available = $true
            gpu_names = @()
            driver_version = $null
            message = $_.Exception.Message
            next_action = 'Review NVIDIA driver installation.'
        }
    }
}
