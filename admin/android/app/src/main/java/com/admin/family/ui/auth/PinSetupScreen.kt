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
 * First-time setup (or PIN reset): enter a 6-digit PIN and confirm it on the same page.
 * On success calls onPinReady(pin) — the caller stores it via AccessCodeStore.setupPin().
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PinSetupScreen(
    onPinReady: (pin: String) -> Unit,
    onCancel: (() -> Unit)? = null,
    isReset: Boolean = false,
) {
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
                        "Choose a 6-digit PIN",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        "Enter the PIN twice to confirm. It unlocks the app on this device.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )

                    PinField(
                        value = pin,
                        onValueChange = { pin = it.filter { c -> c.isDigit() }.take(AccessCodeStore.PIN_LENGTH) },
                        label = "PIN",
                        imeAction = ImeAction.Next,
                    )
                    PinField(
                        value = confirm,
                        onValueChange = { confirm = it.filter { c -> c.isDigit() }.take(AccessCodeStore.PIN_LENGTH) },
                        label = "Confirm PIN",
                        imeAction = ImeAction.Done,
                    )

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
                            when {
                                pin.length != AccessCodeStore.PIN_LENGTH ->
                                    error = "PIN must be exactly ${AccessCodeStore.PIN_LENGTH} digits"
                                confirm.length != AccessCodeStore.PIN_LENGTH ->
                                    error = "Please confirm your PIN"
                                pin != confirm -> {
                                    error = "PINs do not match"
                                    confirm = ""
                                }
                                else -> onPinReady(pin)
                            }
                        },
                        enabled = pin.length == AccessCodeStore.PIN_LENGTH &&
                                confirm.length == AccessCodeStore.PIN_LENGTH,
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth().height(48.dp),
                    ) {
                        Icon(Icons.Filled.CheckCircle, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text(
                            if (isReset) "Save New PIN" else "Save PIN",
                            fontWeight = FontWeight.SemiBold,
                        )
                    }

                    if (onCancel != null) {
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
    label: String = "PIN",
    imeAction: ImeAction = ImeAction.Done,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        placeholder = { Text("••••••", textAlign = TextAlign.Center) },
        leadingIcon = { Icon(Icons.Filled.Lock, contentDescription = null) },
        visualTransformation = PasswordVisualTransformation(),
        singleLine = true,
        keyboardOptions = KeyboardOptions(
            keyboardType = KeyboardType.NumberPassword,
            imeAction = imeAction,
        ),
        modifier = Modifier.fillMaxWidth(),
    )
}
