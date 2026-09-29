package com.admin.family.ui.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.admin.family.ui.theme.Danger
import com.admin.family.ui.theme.Success
import com.admin.family.ui.theme.Warning
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    viewModel: SettingsViewModel,
    onBack: () -> Unit,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings") },
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
            ConnectionSection(state)
            BackendSection(
                state = state,
                onInputChanged = viewModel::onUrlInputChanged,
                onSave = viewModel::save,
                onTest = viewModel::testConnection,
                onReset = viewModel::resetToDefaults,
            )
            InfoSection(state)
        }
    }
}

// ---------------------------------------------------------------
// Connection status card
// ---------------------------------------------------------------

@Composable
private fun ConnectionSection(state: SettingsUiState) {
    val (title, color, body) = when (val r = state.testResult) {
        is ConnectionTestResult.Idle -> Triple(
            "Not tested yet",
            MaterialTheme.colorScheme.onSurfaceVariant,
            "Tap \"Test connection\" below to verify.",
        )
        is ConnectionTestResult.Testing -> Triple(
            "Testing…",
            Warning,
            "Contacting backend…",
        )
        is ConnectionTestResult.Success -> Triple(
            "Connected",
            Success,
            buildString {
                append("Status: ${r.health.status}\n")
                append("Environment: ${r.health.environment}\n")
                append("Uptime: ${"%.1f".format(r.health.uptimeSeconds)} s\n")
                val db = r.health.checks.database
                append("Database: ${if (db.ok) "OK" else "FAIL (${db.error})"}")
            },
        )
        is ConnectionTestResult.Failure -> Triple(
            "Failed",
            Danger,
            r.message,
        )
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    "Connection",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                )
                Spacer(Modifier.width(12.dp))
                when (state.testResult) {
                    is ConnectionTestResult.Testing -> {
                        CircularProgressIndicator(
                            modifier = Modifier.size(16.dp),
                            strokeWidth = 2.dp,
                        )
                    }
                    is ConnectionTestResult.Success -> Icon(
                        Icons.Filled.Check,
                        contentDescription = null,
                        tint = Success,
                        modifier = Modifier.size(18.dp),
                    )
                    is ConnectionTestResult.Failure -> Icon(
                        Icons.Filled.Warning,
                        contentDescription = null,
                        tint = Danger,
                        modifier = Modifier.size(18.dp),
                    )
                    else -> Unit
                }
            }
            Text(title, color = color, style = MaterialTheme.typography.titleSmall)
            if (body.isNotBlank()) {
                Text(
                    body,
                    style = MaterialTheme.typography.bodyMedium,
                    fontFamily = if (state.testResult is ConnectionTestResult.Success)
                        FontFamily.Monospace else FontFamily.Default,
                )
            }
        }
    }
}

// ---------------------------------------------------------------
// Backend URL section
// ---------------------------------------------------------------

@Composable
private fun BackendSection(
    state: SettingsUiState,
    onInputChanged: (String) -> Unit,
    onSave: () -> Unit,
    onTest: () -> Unit,
    onReset: () -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                "Backend URL",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )

            OutlinedTextField(
                value = state.apiBaseUrlInput,
                onValueChange = onInputChanged,
                label = { Text("Base URL") },
                placeholder = { Text("http://192.168.1.50:8000/") },
                singleLine = true,
                isError = state.urlError != null,
                supportingText = state.urlError?.let { { Text(it, color = Danger) } },
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.Uri,
                    imeAction = ImeAction.Done,
                ),
                modifier = Modifier.fillMaxWidth(),
            )

            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Button(
                    onClick = onSave,
                    enabled = state.urlError == null &&
                            state.apiBaseUrlInput != state.savedApiBaseUrl,
                    modifier = Modifier.weight(1f),
                ) {
                    Text("Save")
                }
                Button(
                    onClick = onTest,
                    enabled = state.testResult !is ConnectionTestResult.Testing,
                    modifier = Modifier.weight(1f),
                ) {
                    Icon(
                        Icons.Filled.Refresh,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp),
                    )
                    Spacer(Modifier.width(6.dp))
                    Text("Test connection")
                }
            }

            TextButton(
                onClick = onReset,
                modifier = Modifier.align(Alignment.End),
            ) {
                Text("Reset to defaults")
            }

            Text(
                "Saved: ${state.savedApiBaseUrl}",
                style = MaterialTheme.typography.bodySmall,
                fontFamily = FontFamily.Monospace,
            )
        }
    }
}

// ---------------------------------------------------------------
// Info section
// ---------------------------------------------------------------

@Composable
private fun InfoSection(state: SettingsUiState) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(
                "History",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                "Last success: ${formatMillis(state.lastSuccessAtMillis)}",
                style = MaterialTheme.typography.bodyMedium,
            )
            Text(
                "Last failure: ${formatMillis(state.lastFailureAtMillis)}",
                style = MaterialTheme.typography.bodyMedium,
            )
            Spacer(Modifier.size(8.dp))
            Text(
                "Tip: 10.0.2.2 reaches the host machine from an emulator. " +
                        "From a real device on the same Wi-Fi, use the host's LAN IP " +
                        "(for example 192.168.1.50).",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

private fun formatMillis(ms: Long): String {
    if (ms <= 0L) return "never"
    val fmt = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US)
    return fmt.format(Date(ms))
}
