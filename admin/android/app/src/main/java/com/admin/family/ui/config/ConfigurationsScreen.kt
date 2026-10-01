package com.admin.family.ui.config

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.admin.family.data.config.NamedConfig
import kotlinx.coroutines.launch
import com.admin.family.ui.theme.Danger
import com.admin.family.ui.theme.Success

/**
 * Named-Configurations screen.
 *
 * Layout:
 *   - TopAppBar with hamburger → opens Drawer with saved configs
 *   - Main area shows details of the currently active config
 *   - Bottom button: "Create new configuration"
 *   - Each config in drawer: tap to activate, long-press / edit icon to edit,
 *     delete icon to remove
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConfigurationsScreen(
    configs: List<NamedConfig>,
    activeId: String?,
    onCreate: (name: String, url: String) -> Unit,
    onActivate: (String) -> Unit,
    onDelete: (String) -> Unit,
    onUpdate: (NamedConfig) -> Unit,
    onBack: () -> Unit,
) {
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val scope = rememberCoroutineScope()
    var showCreateDialog by remember { mutableStateOf(false) }
    var editing by remember { mutableStateOf<NamedConfig?>(null) }

    val active = configs.firstOrNull { it.id == activeId }

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet {
                DrawerHeader(count = configs.size)
                Divider()

                if (configs.isEmpty()) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(24.dp),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(
                            "No configurations yet",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                } else {
                    LazyColumn(
                        modifier = Modifier.fillMaxWidth(),
                        contentPadding = PaddingValues(vertical = 8.dp),
                    ) {
                        items(configs, key = { it.id }) { cfg ->
                            DrawerItem(
                                config = cfg,
                                isActive = cfg.id == activeId,
                                onClick = {
                                    onActivate(cfg.id)
                                    scope.launch { drawerState.close() }
                                },
                                onEdit = { editing = cfg },
                                onDelete = { onDelete(cfg.id) },
                            )
                        }
                    }
                }

                Spacer(Modifier.weight(1f))

                HorizontalDivider()
                NavigationDrawerItem(
                    icon = { Icon(Icons.Filled.Add, contentDescription = null) },
                    label = { Text("Create new configuration") },
                    selected = false,
                    onClick = {
                        showCreateDialog = true
                        scope.launch { drawerState.close() }
                    },
                    modifier = Modifier.padding(8.dp),
                )
            }
        },
    ) {
        Scaffold(
            topBar = {
                TopAppBar(
                    title = { Text("Configurations") },
                    navigationIcon = {
                        IconButton(onClick = {
                            scope.launch { drawerState.open() }
                        }) {
                            Icon(Icons.Filled.Menu, contentDescription = "Menu")
                        }
                    },
                    actions = {
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
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                if (active == null) {
                    EmptyState(onCreate = { showCreateDialog = true })
                } else {
                    ActiveConfigCard(
                        config = active,
                        onEdit = { editing = active },
                    )
                    SwipeHintCard()
                }

                Spacer(Modifier.height(8.dp))

                Button(
                    onClick = { showCreateDialog = true },
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier.fillMaxWidth().height(50.dp),
                ) {
                    Icon(Icons.Filled.Add, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("Create new configuration", fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }

    // ─── Create dialog ───
    if (showCreateDialog) {
        ConfigEditDialog(
            title = "New configuration",
            initialName = "",
            initialUrl = active?.backendUrl ?: "http://127.0.0.1:8000/",
            onDismiss = { showCreateDialog = false },
            onSave = { name, url ->
                onCreate(name, url)
                showCreateDialog = false
            },
        )
    }

    // ─── Edit dialog ───
    editing?.let { cfg ->
        ConfigEditDialog(
            title = "Edit configuration",
            initialName = cfg.name,
            initialUrl = cfg.backendUrl,
            onDismiss = { editing = null },
            onSave = { name, url ->
                onUpdate(cfg.copy(name = name, backendUrl = url))
                editing = null
            },
        )
    }
}

// ───────────────────────────────────────────────────────────────
//  Sub-composables
// ───────────────────────────────────────────────────────────────

@Composable
private fun DrawerHeader(count: Int) {
    Column(Modifier.padding(16.dp)) {
        Text(
            "Configurations",
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(4.dp))
        Text(
            "$count saved",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun DrawerItem(
    config: NamedConfig,
    isActive: Boolean,
    onClick: () -> Unit,
    onEdit: () -> Unit,
    onDelete: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (isActive) {
            Icon(
                Icons.Filled.Check,
                contentDescription = "Active",
                tint = Success,
                modifier = Modifier.size(18.dp),
            )
            Spacer(Modifier.width(8.dp))
        } else {
            Spacer(Modifier.size(26.dp))
        }

        Column(Modifier.weight(1f)) {
            Text(
                config.name,
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = if (isActive) FontWeight.Bold else FontWeight.Normal,
            )
            Text(
                config.backendUrl,
                style = MaterialTheme.typography.bodySmall,
                fontFamily = FontFamily.Monospace,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.alpha(0.75f),
            )
        }

        IconButton(onClick = onEdit, modifier = Modifier.size(36.dp)) {
            Icon(
                Icons.Filled.Edit,
                contentDescription = "Edit",
                modifier = Modifier.size(18.dp),
            )
        }
        IconButton(onClick = onDelete, modifier = Modifier.size(36.dp)) {
            Icon(
                Icons.Filled.Delete,
                contentDescription = "Delete",
                tint = Danger,
                modifier = Modifier.size(18.dp),
            )
        }
    }
}

@Composable
private fun ActiveConfigCard(
    config: NamedConfig,
    onEdit: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Column(
            Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    Icons.Filled.Check,
                    contentDescription = null,
                    tint = Success,
                    modifier = Modifier.size(20.dp),
                )
                Spacer(Modifier.width(8.dp))
                Text(
                    "Active configuration",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                )
            }

            Spacer(Modifier.height(4.dp))

            LabeledRow("Name", config.name)
            LabeledRow("Backend URL", config.backendUrl, monospace = true)

            config.controlToken?.takeIf { it.isNotBlank() }?.let {
                LabeledRow("Control token", maskToken(it), monospace = true)
            }
            config.tunnelProvider?.let {
                LabeledRow("Tunnel", it)
            }
            config.tunnelUrl?.let {
                LabeledRow("Tunnel URL", it, monospace = true)
            }

            Spacer(Modifier.height(4.dp))

            OutlinedButton(
                onClick = onEdit,
                shape = RoundedCornerShape(8.dp),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Filled.Edit, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(Modifier.width(6.dp))
                Text("Edit this configuration")
            }
        }
    }
}

@Composable
private fun SwipeHintCard() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
        ),
        shape = RoundedCornerShape(12.dp),
    ) {
        Column(Modifier.padding(14.dp)) {
            Text(
                "Switch configurations",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
            )
            Spacer(Modifier.height(4.dp))
            Text(
                "Open the side menu (☰) and tap a configuration to activate it " +
                        "instantly.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun EmptyState(onCreate: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
    ) {
        Column(
            Modifier.padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                "No configurations yet",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                "Create your first configuration to point the app at a backend.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun LabeledRow(
    label: String,
    value: String,
    monospace: Boolean = false,
) {
    Row(Modifier.fillMaxWidth()) {
        Text(
            "$label: ",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.width(110.dp),
        )
        Text(
            value,
            style = MaterialTheme.typography.bodySmall,
            fontFamily = if (monospace) FontFamily.Monospace else FontFamily.Default,
            modifier = Modifier.weight(1f),
        )
    }
}

// ───────────────────────────────────────────────────────────────
//  Create / Edit dialog
// ───────────────────────────────────────────────────────────────

@Composable
private fun ConfigEditDialog(
    title: String,
    initialName: String,
    initialUrl: String,
    onDismiss: () -> Unit,
    onSave: (name: String, url: String) -> Unit,
) {
    var name by remember { mutableStateOf(initialName) }
    var url by remember { mutableStateOf(initialUrl) }
    var error by remember { mutableStateOf<String?>(null) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it.take(40) },
                    label = { Text("Configuration name") },
                    placeholder = { Text("Home / Work / Trip") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Text,
                        imeAction = ImeAction.Next,
                    ),
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = url,
                    onValueChange = { url = it },
                    label = { Text("Backend URL") },
                    placeholder = { Text("http://192.168.1.50:8000/") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Uri,
                        imeAction = ImeAction.Done,
                    ),
                    modifier = Modifier.fillMaxWidth(),
                )
                if (error != null) {
                    Text(error!!, color = Danger, style = MaterialTheme.typography.bodySmall)
                }
            }
        },
        confirmButton = {
            TextButton(onClick = {
                error = null
                val trimmedName = name.trim()
                val trimmedUrl = url.trim()
                if (trimmedName.isBlank()) {
                    error = "Name cannot be empty"
                    return@TextButton
                }
                if (!trimmedUrl.startsWith("http://") &&
                    !trimmedUrl.startsWith("https://")) {
                    error = "URL must start with http:// or https://"
                    return@TextButton
                }
                onSave(trimmedName, trimmedUrl)
            }) {
                Text("Save")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        },
    )
}

// ───────────────────────────────────────────────────────────────
//  Helpers
// ───────────────────────────────────────────────────────────────

private fun maskToken(t: String): String {
    if (t.length <= 6) return "••••"
    return t.take(3) + "••••" + t.takeLast(3)
}
