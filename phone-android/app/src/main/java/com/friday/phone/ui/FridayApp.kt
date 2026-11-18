package com.friday.phone.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.consumeWindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.PowerSettingsNew
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector

/** Telefonun yapabildiği, ekranların bilmesi gerekmeyen işler: kamera, ses tanıma, tarayıcı. */
data class PlatformActions(
    val scanQr: () -> Unit,
    val listen: () -> Unit,
    val openSite: () -> Unit,
    val toggleLanMic: () -> Unit,
    val versionName: String,
)

private enum class Tab(val label: String, val icon: ImageVector) {
    COMMAND("KOMUT", Icons.AutoMirrored.Filled.Send),
    WAKE("UYANDIR", Icons.Filled.PowerSettingsNew),
    SETTINGS("AYARLAR", Icons.Filled.Settings),
}

@Composable
fun FridayApp(vm: FridayViewModel, actions: PlatformActions) {
    val state by vm.state.collectAsState()
    val snackbar = remember { SnackbarHostState() }
    var tab by rememberSaveable { mutableStateOf(Tab.COMMAND) }

    LaunchedEffect(state.message) {
        val text = state.message
        if (text != null) {
            snackbar.showSnackbar(text)
            vm.consumeMessage()
        }
    }

    val showMain = state.paired && state.pendingKey.isEmpty()
    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        snackbarHost = { SnackbarHost(snackbar) },
        bottomBar = {
            if (showMain) {
                NavigationBar(containerColor = MaterialTheme.colorScheme.surface) {
                    Tab.values().forEach { item ->
                        NavigationBarItem(
                            selected = tab == item,
                            onClick = { tab = item },
                            icon = { Icon(item.icon, contentDescription = item.label) },
                            label = { Text(item.label, style = MaterialTheme.typography.labelMedium) },
                        )
                    }
                }
            }
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding).consumeWindowInsets(padding)) {
            if (!showMain) {
                PairScreen(state, onScan = actions.scanQr, onConfirm = vm::confirmCode, onCancel = vm::cancelPairing)
            } else {
                when (tab) {
                    Tab.COMMAND -> CommandScreen(
                        state,
                        onSend = vm::send,
                        onListen = actions.listen,
                        onToggleLanMic = actions.toggleLanMic,
                    )
                    Tab.WAKE -> WakeScreen(state, onWake = vm::wake)
                    Tab.SETTINGS -> SettingsScreen(state, actions, onForget = vm::forgetPairing, onForgetLan = vm::forgetLan)
                }
            }
        }
    }
}
