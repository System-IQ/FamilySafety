package com.admin.family.ui.controlroom

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.Cloud
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.admin.family.data.api.dto.DeviceDto
import com.admin.family.ui.theme.Danger
import com.admin.family.ui.theme.Success
import com.admin.family.ui.theme.Warning

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ControlRoomScreen(
    vm: ControlRoomViewModel,
    onOpenSettings: () -> Unit,
    onOpenServer: () -> Unit,
    onLogout: () -> Unit,
) {
    val state by vm.state.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Family Guard — Control Room") },
                actions = {
                    IconButton(onClick = vm::refresh) {
                        Icon(Icons.Filled.Refresh, contentDescription = "Refresh")
                    }
                    IconButton(onClick = onOpenServer) {
                        Icon(Icons.Filled.Cloud, contentDescription = "Server")
                    }
                    IconButton(onClick = onOpenSettings) {
                        Icon(Icons.Filled.Settings, contentDescription = "Settings")
                    }
                    IconButton(onClick = onLogout) {
                        Icon(
                            Icons.AutoMirrored.Filled.Logout,
                            contentDescription = "Sign out",
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
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            when (val s = state) {
                is ControlRoomState.Loading -> {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        CircularProgressIndicator(modifier = Modifier.size(20.dp))
                        Spacer(Modifier.width(12.dp))
                        Text("Loading…")
                    }
                }
                is ControlRoomState.Unauthorized -> {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = androidx.compose.material3.CardDefaults.cardColors(
                            containerColor = Danger.copy(alpha = 0.15f),
                        ),
                    ) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(
                                "Session expired",
                                color = Danger,
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.SemiBold,
                            )
                            Text(
                                "Please sign in again.",
                                style = MaterialTheme.typography.bodyMedium,
                            )
                            androidx.compose.material3.Button(
                                onClick = onLogout,
                                modifier = Modifier.fillMaxWidth(),
                            ) {
                                Text("Sign in")
                            }
                        }
                    }
                }
                is ControlRoomState.Failed -> {
                    Text(
                        text = "Error: ${s.message}",
                        color = Danger,
                        style = MaterialTheme.typography.bodyLarge,
                    )
                }
                is ControlRoomState.Ready -> {
                    ServerSummary(s)
                    Text(
                        "Devices (${s.devices.size})",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                    )
                    if (s.devices.isEmpty()) {
                        Text(
                            "No devices yet.",
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    } else {
                        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            items(s.devices, key = { it.deviceId }) { DeviceCard(it) }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ServerSummary(state: ControlRoomState.Ready) {
    val db = state.health.checks.database
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text("Server", style = MaterialTheme.typography.titleMedium)
            Text("Status: ${state.health.status.uppercase()}")
            Text("Environment: ${state.health.environment}")
            Text("Uptime: ${"%.1f".format(state.health.uptimeSeconds)}s")
            Text(
                text = if (db.ok) "Database: OK" else "Database: FAIL (${db.error})",
                color = if (db.ok) Success else Danger,
            )
        }
    }
}

@Composable
private fun DeviceCard(device: DeviceDto) {
    val statusColor = when (device.connectionState) {
        "online" -> Success
        "weak", "intermittent" -> Warning
        "offline" -> Danger
        else -> MaterialTheme.colorScheme.onSurface
    }
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(device.deviceName, style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.width(8.dp))
                Text("(${device.connectionState})", color = statusColor)
            }
            Text("Battery: ${device.battery.levelPercent}% " +
                    if (device.battery.charging) "(charging)" else "")
            Text("Last seen: ${device.lastSeen}")
            Text("Management: ${device.managementState}")
            Text("Android ${device.androidVersion} • app ${device.appVersion}")
        }
    }
}
