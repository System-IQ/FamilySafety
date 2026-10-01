package com.admin.family.ui.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Fingerprint
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

/**
 * Lightweight screen shown while the biometric prompt is active.
 * Provides context and a fallback button ("Use access code").
 */
@Composable
fun BiometricGateScreen(
    onFallbackToCode: () -> Unit,
    onRetry: () -> Unit,
    biometricAvailable: Boolean = true,
    message: String? = null,
) {
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
                .padding(32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Box(
                modifier = Modifier
                    .size(96.dp)
                    .background(
                        MaterialTheme.colorScheme.primary.copy(alpha = 0.12f),
                        RoundedCornerShape(50),
                    ),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    Icons.Filled.Fingerprint,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(56.dp),
                )
            }

            Spacer(Modifier.height(24.dp))
            Text(
                "Locked",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(6.dp))
            Text(
                message ?: if (biometricAvailable)
                    "Place your finger on the sensor or look at the camera."
                else
                    "Biometric not available. Enter your access code.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            Spacer(Modifier.height(32.dp))

            if (biometricAvailable) {
                Button(
                    onClick = onRetry,
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier.fillMaxWidth().height(48.dp),
                ) {
                    Icon(Icons.Filled.Fingerprint, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("Try again", fontWeight = FontWeight.SemiBold)
                }
                Spacer(Modifier.height(10.dp))
            }

            OutlinedButton(
                onClick = onFallbackToCode,
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.fillMaxWidth().height(48.dp),
            ) {
                Text("Use access code")
            }
        }
    }
}
