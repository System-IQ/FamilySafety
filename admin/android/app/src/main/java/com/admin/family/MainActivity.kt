package com.admin.family

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.admin.family.ui.navigation.AppNavigation
import com.admin.family.ui.theme.FamilyAdminTheme

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val app = application as FamilyAdminApp

        setContent {
            FamilyAdminTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    AppNavigation(
                        deviceRepository = app.deviceRepository,
                        settingsRepository = app.settingsRepository,
                        apiClient = app.apiClient,
                    )
                }
            }
        }
    }
}
