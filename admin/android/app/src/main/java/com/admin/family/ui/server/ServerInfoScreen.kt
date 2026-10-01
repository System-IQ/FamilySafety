package com.admin.family.ui.server

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Cloud
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.admin.family.ui.theme.Danger
import com.admin.family.ui.theme.Success
import com.admin.family.ui.theme.Warning

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ServerInfoScreen(
    vm: ServerInfoViewModel,
    onBack: () -> Unit,
) {
    val ui by vm.ui.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Server Info") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = vm::refresh) {
                        Icon(Icons.Filled.Refresh, contentDescription = "Refresh")
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

            // ── Agent connection ──
            AgentCard(ui)

            // ── Token setup (only if not saved) ──
            if (!ui.tokenSaved) {
                TokenSetupCard(ui, vm)
            } else {
                TokenManageCard(ui, vm)
            }

            // ── Status ──
            ui.status?.let { StatusCard(it) }

            // ── Actions ──
            ActionsCard(ui, vm)

            // ── Last message ──
            ui.lastMessage?.let { LastMessageCard(it, ui.phase) }

            Spacer(Modifier.height(20.dp))
        }
    }
}

@Composable
private fun AgentCard(ui: ServerInfoUiState) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Row(
            Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            val (label, color) = when {
                ui.agentReachable -> "Agent reachable" to Success
                else -> "Agent unreachable" to Danger
            }
            Box(
                Modifier
                    .size(10.dp)
                    .background(color, RoundedCornerShape(50)),
            )
            Spacer(Modifier.width(10.dp))
            Column {
                Text(
                    label,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = color,
                )
                Text(
                    "127.0.0.1:9999",
                    style = MaterialTheme.typography.labelSmall,
                    fontFamily = FontFamily.Monospace,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun TokenSetupCard(ui: ServerInfoUiState, vm: ServerInfoViewModel) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                "Control Token",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                "Paste the token from Termux:  cat ~/.fsserver/control-token",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            OutlinedTextField(
                value = ui.tokenInput,
                onValueChange = vm::onTokenInputChanged,
                label = { Text("Token (64 hex chars)") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End,
            ) {
                Button(
                    onClick = vm::saveToken,
                    enabled = ui.tokenInput.length >= 32,
                ) {
                    Text("Save token")
                }
            }
        }
    }
}

@Composable
private fun TokenManageCard(ui: ServerInfoUiState, vm: ServerInfoViewModel) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Row(
            Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = Success)
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Text("Token saved", fontWeight = FontWeight.SemiBold)
                Text(
                    "••••••••  ·  shared with fs-control",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            TextButton(onClick = vm::clearToken) {
                Text("Clear")
            }
        }
    }
}

@Composable
private fun StatusCard(status: com.admin.family.data.api.ControlStatus) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(
                "Server Status",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            StatusRow(
                label = "Overall",
                value = if (status.running) "RUNNING" else "STOPPED",
                color = if (status.running) Success else Warning,
            )
            StatusRow(
                label = "Backend (port 8000)",
                value = if (status.backend) "UP" else "DOWN",
                color = if (status.backend) Success else Danger,
            )
            StatusRow(
                label = "Tailscale IP",
                value = status.tailscaleIp.ifBlank { "—" },
                color = if (status.tailscaleIp.isNotBlank()) Success else MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun StatusRow(label: String, value: String, color: androidx.compose.ui.graphics.Color) {
    Row(Modifier.fillMaxWidth()) {
        Text(
            label,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.weight(1f))
        Text(
            value,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.SemiBold,
            color = color,
        )
    }
}

@Composable
private fun ActionsCard(ui: ServerInfoUiState, vm: ServerInfoViewModel) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                "Controls",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(
                    onClick = vm::startServer,
                    enabled = ui.tokenSaved && !ui.isBusy &&
                            (ui.status?.running != true),
                    modifier = Modifier.weight(1f),
                ) {
                    if (ui.phase is ServerInfoPhase.Starting) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(16.dp),
                            strokeWidth = 2.dp,
                            color = MaterialTheme.colorScheme.onPrimary,
                        )
                        Spacer(Modifier.width(6.dp))
                        Text("Starting…")
                    } else {
                        Icon(Icons.Filled.PlayArrow, contentDescription = null)
                        Spacer(Modifier.width(6.dp))
                        Text("Start")
                    }
                }
                Button(
                    onClick = vm::stopServer,
                    enabled = ui.tokenSaved && !ui.isBusy &&
                            (ui.status?.running == true),
                    modifier = Modifier.weight(1f),
                ) {
                    if (ui.phase is ServerInfoPhase.Stopping) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(16.dp),
                            strokeWidth = 2.dp,
                            color = MaterialTheme.colorScheme.onPrimary,
                        )
                        Spacer(Modifier.width(6.dp))
                        Text("Stopping…")
                    } else {
                        Icon(Icons.Filled.Stop, contentDescription = null)
                        Spacer(Modifier.width(6.dp))
                        Text("Stop")
                    }
                }
            }
            Text(
                "Commands run in Termux (fs-control agent). " +
                        "Stop keeps the agent alive so you can restart.",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun LastMessageCard(message: String, phase: ServerInfoPhase) {
    val (color, icon) = when (phase) {
        is ServerInfoPhase.Error -> Danger to Icons.Filled.Error
        else -> Warning to Icons.Filled.Cloud
    }
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = color.copy(alpha = 0.12f),
        ),
    ) {
        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(10.dp))
            Text(message, style = MaterialTheme.typography.bodySmall, color = color)
        }
    }
}
