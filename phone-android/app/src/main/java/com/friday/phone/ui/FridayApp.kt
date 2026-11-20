package com.friday.phone.ui

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.animation.core.tween
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
                AnimatedContent(
                    targetState = tab,
                    transitionSpec = {
                        val dir = if (targetState.ordinal > initialState.ordinal) 1 else -1
                        (slideInHorizontally(tween(360)) { it / 4 * dir } + fadeIn(tween(300)) + scaleIn(tween(360), initialScale = 0.92f)) togetherWith
                            (slideOutHorizontally(tween(260)) { -it / 4 * dir } + fadeOut(tween(200)) + scaleOut(tween(260), targetScale = 0.92f))
                    },
                    label = "tab",
                ) { current ->
                    when (current) {
                        Tab.COMMAND -> CommandScreen(
                            state,
                            onSend = vm::send,
                            onListen = actions.listen,
                            onToggleLanMic = actions.toggleLanMic,
                            history = HistoryActions(
                                onDelete = vm::deleteCommand,
                                onEdit = vm::editCommand,
                                onPin = vm::togglePin,
                                onClear = vm::clearHistory,
                            ),
                        )
                        Tab.WAKE -> WakeScreen(state, onWake = vm::wake)
                        Tab.SETTINGS -> SettingsScreen(state, actions, onForget = vm::forgetPairing, onForgetLan = vm::forgetLan)
                    }
                }
            }
        }
    }
}
