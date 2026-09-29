package com.admin.family.ui.server

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.PlayArrow
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
fun ServerControlScreen(
    vm: ServerControlViewModel,
    onBack: () -> Unit,
) {
    val ui by vm.state.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Server Control") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            // ---- Status card ----
            StatusCard(ui.state)

            // ---- Auth key section ----
            AuthKeySection(ui, vm)

            // ---- Controls ----
            ControlsSection(ui, vm)

            // ---- Info ----
            InfoSection(ui)
        }
    }
}

@Composable
private fun StatusCard(state: ServerState) {
    val (label, color) = when (state) {
        is ServerState.Stopped -> "Stopped" to MaterialTheme.colorScheme.onSurfaceVariant
        is ServerState.Starting -> "Starting…" to Warning
        is ServerState.Running -> "Running" to Success
        is ServerState.Failed -> "Failed" to Danger
    }
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Status", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(label, color = color, style = MaterialTheme.typography.titleLarge)
            if (state is ServerState.Running) {
                Text("Tailnet IP: ${state.tailnetIp}", fontFamily = FontFamily.Monospace)
            }
            if (state is ServerState.Failed) {
                Text(state.message, color = Danger, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun AuthKeySection(ui: ServerControlUiState, vm: ServerControlViewModel) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("Tailscale Auth Key", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)

            if (ui.authKeySaved) {
                Text("✓ Saved (hidden)", color = Success)
                TextButton(onClick = vm::clearAuthKey) {
                    Text("Clear key")
                }
            } else {
                OutlinedTextField(
                    value = ui.authKeyInput,
                    onValueChange = vm::onAuthKeyChanged,
                    label = { Text("tskey-auth-…") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                Button(
                    onClick = vm::saveAuthKey,
                    enabled = ui.authKeyInput.isNotBlank(),
                    modifier = Modifier.align(Alignment.End),
                ) {
                    Text("Save key")
                }
            }
        }
    }
}

@Composable
private fun ControlsSection(ui: ServerControlUiState, vm: ServerControlViewModel) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("Controls", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(
                    onClick = vm::startServer,
                    enabled = ui.authKeySaved &&
                            ui.state !is ServerState.Running &&
                            ui.state !is ServerState.Starting,
                    modifier = Modifier.weight(1f),
                ) {
                    Icon(Icons.Filled.PlayArrow, contentDescription = null)
                    Spacer(Modifier.width(4.dp))
                    Text("Start")
                }
                Button(
                    onClick = vm::stopServer,
                    enabled = ui.state is ServerState.Running ||
                            ui.state is ServerState.Starting,
                    modifier = Modifier.weight(1f),
                ) {
                    Icon(Icons.Filled.Stop, contentDescription = null)
                    Spacer(Modifier.width(4.dp))
                    Text("Stop")
                }
            }
        }
    }
}

@Composable
private fun InfoSection(ui: ServerControlUiState) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text("Config", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text("Hostname: ${ui.hostname}")
            Text("Proxy: :${ui.proxyPort} → ${ui.proxyTarget}")
            Spacer(Modifier.height(6.dp))
            Text(
                "The device will appear as '${ui.hostname}' in your tailnet. " +
                "The Child app can reach it at http://<tailnet-ip>:${ui.proxyPort}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
