package com.admin.family.ui.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Fingerprint
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import com.admin.family.biometric.BiometricAvailability
import com.admin.family.data.auth.AccessCodeStore
import com.admin.family.ui.theme.Danger

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AccessCodeScreen(
    onUnlock: (code: String, enableBiometric: Boolean) -> Unit,
    biometricAvailability: BiometricAvailability = BiometricAvailability.UNKNOWN,
    initialCode: String = "",
    errorMessage: String? = null,
) {
    var code by remember { mutableStateOf(initialCode) }
    var visible by remember { mutableStateOf(false) }
    var enableBiometric by remember {
        mutableStateOf(biometricAvailability == BiometricAvailability.AVAILABLE)
    }
    val focus = LocalFocusManager.current
    val canSubmit = code.trim().length >= AccessCodeStore.MIN_LENGTH

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    listOf(
                        MaterialTheme.colorScheme.background,
                        MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f),
                    )
                )
            )
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Spacer(Modifier.height(24.dp))

            Box(
                modifier = Modifier
                    .size(64.dp)
                    .background(MaterialTheme.colorScheme.primary, RoundedCornerShape(18.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Text("FG",
                    style = MaterialTheme.typography.headlineSmall,
                    color = MaterialTheme.colorScheme.onPrimary,
                    fontWeight = FontWeight.Bold)
            }
            Spacer(Modifier.height(14.dp))
            Text("Family Guard",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold)
            Text("Admin Console",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.alpha(0.75f))

            Spacer(Modifier.height(28.dp))

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
            ) {
                Column(
                    modifier = Modifier.padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Text("Enter access code",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold)
                    Text(
                        "Paste the code you received. No email or password.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )

                    OutlinedTextField(
                        value = code,
                        onValueChange = { code = it },
                        label = { Text("Access code") },
                        leadingIcon = { Icon(Icons.Filled.Lock, contentDescription = null) },
                        trailingIcon = {
                            IconButton(onClick = { visible = !visible }) {
                                Icon(
                                    if (visible) Icons.Filled.Visibility
                                    else Icons.Filled.VisibilityOff,
                                    contentDescription = "Toggle",
                                )
                            }
                        },
                        visualTransformation = if (visible)
                            VisualTransformation.None
                        else
                            PasswordVisualTransformation(),
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(
                            keyboardType = KeyboardType.Password,
                            imeAction = ImeAction.Done,
                        ),
                        modifier = Modifier.fillMaxWidth(),
                    )

                    // Biometric toggle (only when hardware is available)
                    if (biometricAvailability == BiometricAvailability.AVAILABLE) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Icon(Icons.Filled.Fingerprint, contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary)
                            Spacer(Modifier.width(10.dp))
                            Column(Modifier.weight(1f)) {
                                Text("Unlock with biometric",
                                    style = MaterialTheme.typography.bodyMedium,
                                    fontWeight = FontWeight.SemiBold)
                                Text("Use fingerprint or face next time",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            Switch(
                                checked = enableBiometric,
                                onCheckedChange = { enableBiometric = it },
                            )
                        }
                    } else if (biometricAvailability == BiometricAvailability.NOT_ENROLLED) {
                        Text(
                            "Biometric hardware available but no fingerprint enrolled. " +
                                    "Set it up in system settings to enable quick unlock.",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }

                    if (errorMessage != null) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .background(Danger.copy(alpha = 0.12f), RoundedCornerShape(8.dp))
                                .padding(10.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(errorMessage, color = Danger,
                                style = MaterialTheme.typography.bodySmall)
                        }
                    }

                    Spacer(Modifier.height(4.dp))

                    Button(
                        onClick = { focus.clearFocus(); onUnlock(code.trim(), enableBiometric) },
                        enabled = canSubmit,
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth().height(48.dp),
                    ) {
                        Text("Unlock", fontWeight = FontWeight.SemiBold)
                    }

                    Text(
                        "Code is ${AccessCodeStore.MIN_LENGTH}+ characters. " +
                                "Stored only on this device.",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.alpha(0.7f),
                    )
                }
            }

            Spacer(Modifier.height(20.dp))
            Text(
                "v${com.admin.family.BuildConfig.VERSION_NAME}  ·  Family Safety",
                style = MaterialTheme.typography.labelSmall,
                fontFamily = FontFamily.Monospace,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.alpha(0.5f),
            )
        }
    }
}
