package com.admin.family.ui.server

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.BatteryFull
import androidx.compose.material.icons.filled.Cloud
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.NetworkCheck
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.SdCard
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material.icons.filled.Storage
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.repeatOnLifecycle
import com.admin.family.data.api.dto.SystemMetrics
import com.admin.family.ui.theme.Danger
import com.admin.family.ui.theme.Success
import com.admin.family.ui.theme.Warning
import kotlin.math.roundToInt

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ServerDashboardScreen(
    vm: ServerDashboardViewModel,
    onBack: () -> Unit,
) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    val lifecycleOwner = LocalLifecycleOwner.current

    androidx.compose.runtime.LaunchedEffect(lifecycleOwner) {
        lifecycleOwner.lifecycle.repeatOnLifecycle(Lifecycle.State.RESUMED) {
            vm.onScreenVisible()
            try {
                kotlinx.coroutines.awaitCancellation()
            } finally {
                vm.onScreenHidden()
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Server Dashboard") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = vm::toggleAutoRefresh) {
                        Icon(
                            Icons.Filled.Refresh,
                            contentDescription = "Toggle auto-refresh",
                            tint = if (ui.autoRefresh) Success else MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
},
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Spacer(Modifier.height(4.dp))

            when (val s = ui.state) {
                is DashboardState.Loading -> LoadingCard()
                is DashboardState.Failed -> {
                    FailedCard(s.message)
                    RetryButton(vm)
                }
                is DashboardState.Ready -> {
                    ConnectionCard(
                        serverUrl = ui.serverUrl,
                        lastUpdate = s.lastUpdateMillis,
                        autoRefresh = ui.autoRefresh,
                        stale = s.consecutiveFails > 0,
                    )
                    BatteryCard(s.metrics)
                    CpuMemoryCard(s.metrics)
                    StorageCard(s.metrics)
                    NetworkCard(s.metrics)
                    BackendCard(s.metrics)
                    Spacer(Modifier.height(20.dp))
                }
            }
        }
    }
}

// ────────────────────────────────────────────────────────────
// Cards
// ────────────────────────────────────────────────────────────

@Composable
private fun LoadingCard() {
    Card(modifier = Modifier.fillMaxWidth()) {
        Row(
            Modifier.padding(20.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            CircularProgressIndicator(modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
            Spacer(Modifier.width(12.dp))
            Text("Connecting to server…", style = MaterialTheme.typography.bodyLarge)
        }
    }
}

@Composable
private fun FailedCard(message: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Danger.copy(alpha = 0.15f)),
    ) {
        Row(
            Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Filled.Cloud, contentDescription = null, tint = Danger)
            Spacer(Modifier.width(12.dp))
            Column {
                Text("Disconnected", style = MaterialTheme.typography.titleMedium, color = Danger)
                Text(message, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun RetryButton(vm: ServerDashboardViewModel) {
    Button(onClick = vm::refreshNow, modifier = Modifier.fillMaxWidth()) {
        Icon(Icons.Filled.Refresh, contentDescription = null)
        Spacer(Modifier.width(8.dp))
        Text("Retry")
    }
}

@Composable
private fun ConnectionCard(
    serverUrl: String,
    lastUpdate: Long,
    autoRefresh: Boolean,
    stale: Boolean,
) {
    val color = if (stale) Warning else Success
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    Modifier
                        .size(10.dp)
                        .background(color, RoundedCornerShape(50)),
                )
                Spacer(Modifier.width(8.dp))
                Text(
                    if (stale) "STALE" else "CONNECTED",
                    color = color,
                    fontWeight = FontWeight.Bold,
                    style = MaterialTheme.typography.labelLarge,
                )
                Spacer(Modifier.weight(1f))
                if (autoRefresh) {
                    Text(
                        "LIVE",
                        color = Success,
                        style = MaterialTheme.typography.labelSmall,
                        modifier = Modifier
                            .background(Success.copy(alpha = 0.15f), RoundedCornerShape(4.dp))
                            .padding(horizontal = 6.dp, vertical = 2.dp),
                    )
                }
            }
            Text(
                serverUrl,
                style = MaterialTheme.typography.bodySmall,
                fontFamily = FontFamily.Monospace,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            val ago = ((System.currentTimeMillis() - lastUpdate) / 1000).coerceAtLeast(0)
            Text(
                "Updated ${ago}s ago",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun BatteryCard(m: SystemMetrics) {
    val pct = m.battery.percent
    val charging = m.battery.charging
    val temp = m.battery.temperatureC
    MetricCard(
        icon = Icons.Filled.BatteryFull,
        title = "Battery",
        value = pct?.let { "$it%" } ?: "—",
        progress = pct?.toFloat()?.div(100f),
        subtitle = buildString {
            if (charging == true) append("Charging")
            else if (charging == false) append("Discharging")
            if (temp != null) {
                if (isNotEmpty()) append(" · ")
                append("${temp}°C")
            }
        }.ifEmpty { null },
        color = when {
            pct == null -> MaterialTheme.colorScheme.onSurfaceVariant
            pct < 15 -> Danger
            pct < 30 -> Warning
            else -> Success
        },
    )
}

@Composable
private fun CpuMemoryCard(m: SystemMetrics) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            BarRow(
                icon = Icons.Filled.Speed,
                label = "CPU",
                valueText = "${m.cpu.percent}%",
                progress = (m.cpu.percent / 100.0).toFloat(),
                color = progressColor(m.cpu.percent),
                extra = "${m.cpu.cores} cores · load ${"%.2f".format(m.cpu.load1m)}",
            )
            HorizontalDivider()
            BarRow(
                icon = Icons.Filled.Memory,
                label = "RAM",
                valueText = "${m.memory.percent}%",
                progress = (m.memory.percent / 100.0).toFloat(),
                color = progressColor(m.memory.percent),
                extra = "${m.memory.usedMb.roundToInt()} / ${m.memory.totalMb.roundToInt()} MB",
            )
        }
    }
}

@Composable
private fun StorageCard(m: SystemMetrics) {
    MetricCard(
        icon = Icons.Filled.SdCard,
        title = "Storage",
        value = "${m.storage.percent}%",
        progress = (m.storage.percent / 100.0).toFloat(),
        subtitle = "${(m.storage.usedMb / 1024).roundToInt()} GB used · ${(m.storage.freeMb / 1024).roundToInt()} GB free",
        color = progressColor(m.storage.percent),
    )
}

@Composable
private fun NetworkCard(m: SystemMetrics) {
    if (m.network.unavailable) {
        Card(modifier = Modifier.fillMaxWidth()) {
            Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Filled.NetworkCheck, contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.width(12.dp))
                Column {
                    Text("Network I/O", style = MaterialTheme.typography.titleMedium)
                    Text("Not available (Android restricts /proc/net/dev)",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
        return
    }
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Filled.NetworkCheck, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text("Network I/O", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            }
            Text("↓ ${formatBps(m.network.rxRateBps)}   ↑ ${formatBps(m.network.txRateBps)}",
                fontFamily = FontFamily.Monospace)
            Text("Total: ↓ ${m.network.rxTotalMb} MB · ↑ ${m.network.txTotalMb} MB",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun BackendCard(m: SystemMetrics) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Filled.Storage, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text("Backend", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            }
            InfoLine("Process RSS", "${m.process.rssMb} MB")
            InfoLine("Threads", "${m.process.threads}")
            InfoLine("DB size", "${m.database.sizeMb} MB")
            InfoLine("Requests", "${m.requests.total} total · ${m.requests.errors} errors")
            InfoLine("Uptime", formatDuration(m.process.uptimeSeconds))
        }
    }
}

// ────────────────────────────────────────────────────────────
// Building blocks
// ────────────────────────────────────────────────────────────

@Composable
private fun MetricCard(
    icon: ImageVector,
    title: String,
    value: String,
    progress: Float?,
    subtitle: String?,
    color: Color,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(icon, contentDescription = null, tint = color)
                Spacer(Modifier.width(8.dp))
                Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.weight(1f))
                Text(value, color = color, fontWeight = FontWeight.Bold,
                    style = MaterialTheme.typography.titleLarge)
            }
            if (progress != null) {
                LinearProgressIndicator(
                    progress = { progress.coerceIn(0f, 1f) },
                    modifier = Modifier.fillMaxWidth(),
                    color = color,
                )
            }
            if (subtitle != null) {
                Text(subtitle, style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun BarRow(
    icon: ImageVector,
    label: String,
    valueText: String,
    progress: Float,
    color: Color,
    extra: String?,
) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text(label, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.weight(1f))
            Text(valueText, color = color, fontWeight = FontWeight.Bold)
        }
        LinearProgressIndicator(
            progress = { progress.coerceIn(0f, 1f) },
            modifier = Modifier.fillMaxWidth(),
            color = color,
        )
        if (extra != null) {
            Text(extra, style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun InfoLine(label: String, value: String) {
    Row(Modifier.fillMaxWidth()) {
        Text(label, style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.weight(1f))
        Text(value, style = MaterialTheme.typography.bodyMedium,
            fontFamily = FontFamily.Monospace)
    }
}

// ────────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────────

private fun progressColor(pct: Double): Color = when {
    pct < 50 -> Success
    pct < 80 -> Warning
    else -> Danger
}

private fun formatBps(bps: Double): String = when {
    bps < 1024 -> "${bps.roundToInt()} B/s"
    bps < 1024 * 1024 -> "${"%.1f".format(bps / 1024)} KB/s"
    else -> "${"%.2f".format(bps / (1024 * 1024))} MB/s"
}

private fun formatDuration(seconds: Double): String {
    val s = seconds.toInt()
    val h = s / 3600
    val m = (s % 3600) / 60
    val sec = s % 60
    return when {
        h > 0 -> "${h}h ${m}m"
        m > 0 -> "${m}m ${sec}s"
        else -> "${sec}s"
    }
}
