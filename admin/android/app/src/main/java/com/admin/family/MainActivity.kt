package com.admin.family

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.admin.family.data.repository.DeviceRepository
import com.admin.family.ui.controlroom.ControlRoomScreen
import com.admin.family.ui.controlroom.ControlRoomViewModel
import com.admin.family.ui.controlroom.ControlRoomViewModelFactory
import com.admin.family.ui.theme.FamilyAdminTheme

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val repo: DeviceRepository = (application as FamilyAdminApp).deviceRepository

        setContent {
            FamilyAdminTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    val vm: ControlRoomViewModel = viewModel(
                        factory = ControlRoomViewModelFactory(repo),
                    )
                    ControlRoomScreen(vm)
                }
            }
        }
    }
}
