package com.admin.family.ui.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Lock
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
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.admin.family.data.auth.AccessCodeStore
import com.admin.family.ui.theme.Danger

/**
 * First-time setup: create a 6-digit PIN, then confirm it.
 * On success calls onPinReady(pin) — caller stores it via AccessCodeStore.setupPin().
 */
private enum class PinSetupStep { ENTER, CONFIRM }

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PinSetupScreen(
    onPinReady: (pin: String) -> Unit,
    onCancel: (() -> Unit)? = null,
    isReset: Boolean = false,
) {
    var step by remember { mutableStateOf(PinSetupStep.ENTER) }
    var pin by remember { mutableStateOf("") }
    var confirm by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    val focus = LocalFocusManager.current

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
                Text(
                    "FG",
                    style = MaterialTheme.typography.headlineSmall,
                    color = MaterialTheme.colorScheme.onPrimary,
                    fontWeight = FontWeight.Bold,
                )
            }
            Spacer(Modifier.height(14.dp))
            Text("Family Guard", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text(
                if (isReset) "Reset your PIN" else "Set up your PIN",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.alpha(0.75f),
            )

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
                    Text(
                        if (step == PinSetupStep.ENTER) "Choose a 6-digit PIN" else "Confirm your PIN",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        if (step == PinSetupStep.ENTER)
                            "This PIN unlocks the app on this device."
                        else
                            "Enter the same 6 digits again.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )

                    if (step == PinSetupStep.ENTER) {
                        PinField(value = pin, onValueChange = { pin = it.filter { c -> c.isDigit() }.take(6) })
                    } else {
                        PinField(value = confirm, onValueChange = { confirm = it.filter { c -> c.isDigit() }.take(6) })
                    }

                    if (error != null) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .background(Danger.copy(alpha = 0.12f), RoundedCornerShape(8.dp))
                                .padding(10.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(error!!, color = Danger, style = MaterialTheme.typography.bodySmall)
                        }
                    }

                    Spacer(Modifier.height(4.dp))

                    Button(
                        onClick = {
                            focus.clearFocus()
                            error = null
                            if (step == PinSetupStep.ENTER) {
                                if (pin.length != AccessCodeStore.PIN_LENGTH) {
                                    error = "PIN must be exactly ${AccessCodeStore.PIN_LENGTH} digits"
                                } else {
                                    step = PinSetupStep.CONFIRM
                                }
                            } else {
                                if (confirm != pin) {
                                    error = "PINs do not match"
                                    confirm = ""
                                } else {
                                    onPinReady(pin)
                                }
                            }
                        },
                        enabled = if (step == PinSetupStep.ENTER)
                            pin.length == AccessCodeStore.PIN_LENGTH
                        else
                            confirm.length == AccessCodeStore.PIN_LENGTH,
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth().height(48.dp),
                    ) {
                        Icon(Icons.Filled.CheckCircle, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text(
                            if (step == PinSetupStep.ENTER) "Continue" else "Save PIN",
                            fontWeight = FontWeight.SemiBold,
                        )
                    }

                    if (step == PinSetupStep.CONFIRM) {
                        TextButton(
                            onClick = {
                                step = PinSetupStep.ENTER
                                confirm = ""
                                error = null
                            },
                            modifier = Modifier.align(Alignment.End),
                        ) {
                            Text("Back")
                        }
                    }

                    if (onCancel != null && step == PinSetupStep.ENTER) {
                        TextButton(
                            onClick = onCancel,
                            modifier = Modifier.align(Alignment.End),
                        ) {
                            Text("Cancel")
                        }
                    }

                    Text(
                        "The PIN is stored only on this device.",
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PinField(
    value: String,
    onValueChange: (String) -> Unit,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text("PIN") },
        placeholder = { Text("••••••", textAlign = TextAlign.Center) },
        leadingIcon = { Icon(Icons.Filled.Lock, contentDescription = null) },
        visualTransformation = PasswordVisualTransformation(),
        singleLine = true,
        keyboardOptions = KeyboardOptions(
            keyboardType = KeyboardType.NumberPassword,
            imeAction = ImeAction.Done,
        ),
        modifier = Modifier.fillMaxWidth(),
    )
}


