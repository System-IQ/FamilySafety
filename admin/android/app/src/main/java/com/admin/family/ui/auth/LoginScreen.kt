package com.admin.family.ui.auth

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.autofill.ContentType
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.semantics.contentType
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.admin.family.BuildConfig
import com.admin.family.ui.theme.Danger
import com.admin.family.ui.theme.Success

@Composable
fun LoginScreen(
    vm: LoginViewModel,
    onSuccess: () -> Unit,
) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    val focus = LocalFocusManager.current

    LaunchedEffect(ui.phase) {
        if (ui.phase is LoginPhase.Success) onSuccess()
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    colors = listOf(
                        MaterialTheme.colorScheme.background,
                        MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f),
                    ),
                )
            )
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 28.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            // ── Brand ──
            Spacer(Modifier.height(8.dp))
            Box(
                modifier = Modifier
                    .size(60.dp)
                    .background(MaterialTheme.colorScheme.primary, RoundedCornerShape(16.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    "FG",
                    style = MaterialTheme.typography.headlineSmall,
                    color = MaterialTheme.colorScheme.onPrimary,
                    fontWeight = FontWeight.Bold,
                )
            }
            Spacer(Modifier.height(12.dp))
            Text(
                "Family Guard",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
            )
            Text(
                "Admin Console",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.alpha(0.75f),
            )

            Spacer(Modifier.height(22.dp))

            // ── Form ──
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
            ) {
                Column(
                    modifier = Modifier.padding(18.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    Text(
                        text = if (ui.mode == AuthMode.LOGIN) "Welcome back" else "Create account",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = if (ui.mode == AuthMode.LOGIN)
                            "Sign in to access your family console"
                        else
                            "Register as a guardian to get started",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )

                    Spacer(Modifier.height(2.dp))

                    // Display name (register)
                    if (ui.mode == AuthMode.REGISTER) {
                        OutlinedTextField(
                            value = ui.displayName,
                            onValueChange = vm::onDisplayNameChanged,
                            label = { Text("Display name") },
                            leadingIcon = { Icon(Icons.Filled.Person, contentDescription = null) },
                            singleLine = true,
                            enabled = ui.phase !is LoginPhase.Authenticating,
                            modifier = Modifier
                                .fillMaxWidth()
                                .semantics { contentType = ContentType.Name },
                        )
                    }

                    // Email
                    OutlinedTextField(
                        value = ui.email,
                        onValueChange = vm::onEmailChanged,
                        label = { Text("Email") },
                        leadingIcon = { Icon(Icons.Filled.Email, contentDescription = null) },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(
                            keyboardType = KeyboardType.Email,
                            imeAction = ImeAction.Next,
                        ),
                        enabled = ui.phase !is LoginPhase.Authenticating,
                        modifier = Modifier
                            .fillMaxWidth()
                            .semantics { contentType = ContentType.EmailAddress },
                    )

                    // Password
                    OutlinedTextField(
                        value = ui.password,
                        onValueChange = vm::onPasswordChanged,
                        label = { Text("Password (min 12 chars)") },
                        leadingIcon = { Icon(Icons.Filled.Lock, contentDescription = null) },
                        trailingIcon = {
                            IconButton(onClick = vm::togglePasswordVisible) {
                                Icon(
                                    if (ui.passwordVisible) Icons.Filled.Visibility
                                    else Icons.Filled.VisibilityOff,
                                    contentDescription = "Toggle",
                                )
                            }
                        },
                        visualTransformation = if (ui.passwordVisible)
                            VisualTransformation.None
                        else
                            PasswordVisualTransformation(),
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(
                            keyboardType = KeyboardType.Password,
                            imeAction = ImeAction.Done,
                        ),
                        keyboardActions = KeyboardActions(
                            onDone = { focus.clearFocus(); vm.submit() },
                        ),
                        enabled = ui.phase !is LoginPhase.Authenticating,
                        modifier = Modifier
                            .fillMaxWidth()
                            .semantics {
                                contentType = if (ui.mode == AuthMode.REGISTER)
                                    ContentType.NewPassword
                                else
                                    ContentType.Password
                            },
                    )

                    // Error
                    AnimatedVisibility(
                        visible = ui.phase is LoginPhase.Error,
                        enter = fadeIn(tween(150)),
                        exit = fadeOut(tween(100)),
                    ) {
                        val msg = (ui.phase as? LoginPhase.Error)?.message ?: ""
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .background(Danger.copy(alpha = 0.12f), RoundedCornerShape(8.dp))
                                .padding(10.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Icon(
                                Icons.Filled.Error,
                                contentDescription = null,
                                tint = Danger,
                                modifier = Modifier.size(16.dp),
                            )
                            Spacer(Modifier.width(8.dp))
                            Text(
                                msg,
                                color = Danger,
                                style = MaterialTheme.typography.bodySmall,
                            )
                        }
                    }

                    Spacer(Modifier.height(2.dp))

                    // Submit
                    Button(
                        onClick = { focus.clearFocus(); vm.submit() },
                        enabled = ui.canSubmit,
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(48.dp),
                    ) {
                        if (ui.phase is LoginPhase.Authenticating) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(16.dp),
                                strokeWidth = 2.dp,
                                color = MaterialTheme.colorScheme.onPrimary,
                            )
                            Spacer(Modifier.width(10.dp))
                            Text("Please wait…")
                        } else {
                            Text(
                                if (ui.mode == AuthMode.LOGIN) "Sign in" else "Create account",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.SemiBold,
                            )
                        }
                    }

                    // Mode switch
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            if (ui.mode == AuthMode.LOGIN) "No account?" else "Have an account?",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        TextButton(onClick = vm::toggleMode) {
                            Text(
                                if (ui.mode == AuthMode.LOGIN) "Create one" else "Sign in",
                                fontWeight = FontWeight.SemiBold,
                                style = MaterialTheme.typography.bodySmall,
                            )
                        }
                    }
                }
            }

            Spacer(Modifier.height(12.dp))

            // ── Server URL ──
            ServerUrlCard(ui, vm)

            Spacer(Modifier.height(16.dp))

            // ── Footer ──
            Text(
                text = "v${BuildConfig.VERSION_NAME}  ·  Family Safety",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.alpha(0.5f),
            )
            Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable
private fun ServerUrlCard(ui: LoginUiState, vm: LoginViewModel) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f),
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(8.dp)
                        .background(Success, RoundedCornerShape(50)),
                )
                Spacer(Modifier.width(8.dp))
                Text(
                    "Server",
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Spacer(Modifier.weight(1f))
                if (!ui.editingServerUrl) {
                    IconButton(
                        onClick = vm::startEditingServerUrl,
                        modifier = Modifier.size(28.dp),
                    ) {
                        Icon(
                            Icons.Filled.Edit,
                            contentDescription = "Edit",
                            modifier = Modifier.size(14.dp),
                        )
                    }
                }
            }

            if (!ui.editingServerUrl) {
                Text(
                    text = ui.serverUrl,
                    style = MaterialTheme.typography.bodySmall,
                    fontFamily = FontFamily.Monospace,
                    color = MaterialTheme.colorScheme.onSurface,
                )
            } else {
                OutlinedTextField(
                    value = ui.serverUrlDraft,
                    onValueChange = vm::onServerUrlDraftChanged,
                    singleLine = true,
                    label = { Text("Base URL") },
                    placeholder = { Text("http://127.0.0.1:8000/") },
                    isError = ui.serverUrlError != null,
                    supportingText = ui.serverUrlError?.let {
                        { Text(it, color = Danger) }
                    },
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Uri,
                        imeAction = ImeAction.Done,
                    ),
                    modifier = Modifier.fillMaxWidth(),
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(
                        onClick = vm::cancelEditingServerUrl,
                        modifier = Modifier.weight(1f),
                    ) {
                        Icon(Icons.Filled.Close, contentDescription = null, modifier = Modifier.size(14.dp))
                        Spacer(Modifier.width(6.dp))
                        Text("Cancel", style = MaterialTheme.typography.bodySmall)
                    }
                    Button(
                        onClick = vm::saveServerUrl,
                        modifier = Modifier.weight(1f),
                    ) {
                        Icon(Icons.Filled.Check, contentDescription = null, modifier = Modifier.size(14.dp))
                        Spacer(Modifier.width(6.dp))
                        Text("Save", style = MaterialTheme.typography.bodySmall)
                    }
                }
                TextButton(
                    onClick = vm::resetServerUrl,
                    modifier = Modifier.align(Alignment.End),
                ) {
                    Text("Reset to default", style = MaterialTheme.typography.labelSmall)
                }
            }

            Text(
                text = "On the same phone use 127.0.0.1. " +
                        "From other devices use Tailscale IP or Funnel URL.",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.alpha(0.7f),
            )
        }
    }
}
