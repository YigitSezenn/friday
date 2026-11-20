package com.friday.phone.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.PushPin
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilledIconButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.friday.phone.data.WakeConfig
import com.friday.phone.domain.HistoryItem
import java.text.DateFormat
import java.util.Date

// ---------- Eşleştirme ----------

@Composable
fun PairScreen(state: UiState, onScan: () -> Unit, onConfirm: (String) -> Unit, onCancel: () -> Unit) {
    var code by rememberSaveable { mutableStateOf("") }
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).imePadding().padding(28.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Reactor(Modifier.size(200.dp), busy = state.pendingKey.isNotEmpty())
        Spacer(Modifier.height(18.dp))
        Text("FRIDAY", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.primary)
        Spacer(Modifier.height(12.dp))
        if (state.pendingKey.isEmpty()) {
            Text(
                "Bilgisayarındaki FRIDAY'de Ayarlar › Telefon bölümünü aç ve oradaki QR kodu okut.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(28.dp))
            Button(onClick = onScan, modifier = Modifier.fillMaxWidth().height(56.dp).pressDepth()) {
                Icon(Icons.Filled.QrCodeScanner, contentDescription = null)
                Spacer(Modifier.size(10.dp))
                Text("QR OKUT", style = MaterialTheme.typography.labelLarge)
            }
        } else {
            Text(
                "QR okundu. Bilgisayar ekranında QR'ın yanında yazan 6 haneli kodu gir.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(20.dp))
            OutlinedTextField(
                value = code,
                onValueChange = { code = it.filter(Char::isDigit).take(6) },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                label = { Text("KOD") },
                isError = state.pairError != null,
                supportingText = { state.pairError?.let { Text(it) } },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number, imeAction = ImeAction.Done),
                keyboardActions = KeyboardActions(onDone = { if (code.length == 6) onConfirm(code) }),
            )
            Spacer(Modifier.height(12.dp))
            Button(onClick = { onConfirm(code) }, enabled = code.length == 6, modifier = Modifier.fillMaxWidth().height(56.dp).pressDepth()) {
                Text("ONAYLA", style = MaterialTheme.typography.labelLarge)
            }
            TextButton(onClick = { code = ""; onCancel() }, modifier = Modifier.fillMaxWidth()) {
                Text("VAZGEÇ", style = MaterialTheme.typography.labelLarge)
            }
        }
    }
}

// ---------- Komut ----------

/** Kayıtlı komut işlemleri: tekrar gönder, düzenle, sabitle, sil, temizle. */
data class HistoryActions(
    val onDelete: (String) -> Unit,
    val onEdit: (String, String) -> Unit,
    val onPin: (String) -> Unit,
    val onClear: () -> Unit,
)

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun CommandScreen(
    state: UiState,
    onSend: (String) -> Unit,
    onListen: () -> Unit,
    onToggleLanMic: () -> Unit,
    history: HistoryActions,
) {
    var text by rememberSaveable { mutableStateOf("") }
    var editing by remember { mutableStateOf<HistoryItem?>(null) }
    var confirmClear by remember { mutableStateOf(false) }
    val haptics = LocalHapticFeedback.current
    val submit = {
        if (text.isNotBlank() && !state.sending) {
            haptics.performHapticFeedback(HapticFeedbackType.TextHandleMove)
            onSend(text)
            text = ""
        }
    }
    Column(Modifier.fillMaxSize()) {
        StatusHeader(state.pairingCode, busy = state.sending)
        if (state.lanHost.isNotEmpty()) {
            OutlinedButton(
                onClick = onToggleLanMic,
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp).pressDepth(),
            ) {
                Text(
                    if (state.lanMic) "TELEFON MİKROFONU: AÇIK · KAPAT" else "TELEFON MİKROFONUNU AÇ (${state.lanHost})",
                    style = MaterialTheme.typography.labelLarge,
                )
            }
        }
        LazyColumn(
            modifier = Modifier.weight(1f).fillMaxWidth(),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            if (state.history.isEmpty()) {
                item {
                    Text(
                        "Henüz komut yok. Aşağıya yaz ya da mikrofona basıp söyle; komut bilgisayardaki FRIDAY'e gider.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(vertical = 24.dp),
                    )
                }
            } else {
                item(key = "__header") {
                    Row(Modifier.fillMaxWidth().padding(top = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                        Text("KAYITLI KOMUTLAR", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Spacer(Modifier.weight(1f))
                        if (state.history.any { !it.pinned }) {
                            TextButton(onClick = { confirmClear = true }) { Text("TEMİZLE", style = MaterialTheme.typography.labelMedium) }
                        }
                    }
                }
                items(state.history, key = { it.text }) { item ->
                    HistoryRow(
                        item,
                        modifier = Modifier.animateItemPlacement(),
                        onResend = { onSend(item.text) },
                        onEdit = { editing = item },
                        onPin = { history.onPin(item.text) },
                        onDelete = { history.onDelete(item.text) },
                    )
                }
            }
        }
        Row(
            modifier = Modifier.fillMaxWidth().imePadding().padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            OutlinedTextField(
                value = text,
                onValueChange = { text = it },
                modifier = Modifier.weight(1f),
                placeholder = { Text("Bilgisayara yaz…") },
                shape = MaterialTheme.shapes.large,
                maxLines = 3,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { submit() }),
            )
            IconButton(onClick = onListen) { Icon(Icons.Filled.Mic, contentDescription = "Konuş") }
            val sendPulse = rememberInfiniteTransition(label = "send")
            val sendScale by sendPulse.animateFloat(1f, 1.08f, infiniteRepeatable(tween(600), RepeatMode.Reverse), label = "s")
            FilledIconButton(
                onClick = { submit() },
                enabled = text.isNotBlank() && !state.sending,
                modifier = Modifier.scale(if (state.sending) sendScale else 1f).pressDepth(),
            ) {
                if (state.sending) {
                    CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                } else {
                    Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Gönder")
                }
            }
        }
    }
    CommandDialogs(
        editing = editing,
        onEditDone = { value ->
            val current = editing
            editing = null
            if (current != null && value != null) history.onEdit(current.text, value)
        },
        confirmClear = confirmClear,
        onClearDone = { yes -> confirmClear = false; if (yes) history.onClear() },
    )
}

@Composable
private fun CommandDialogs(
    editing: HistoryItem?,
    onEditDone: (String?) -> Unit,
    confirmClear: Boolean,
    onClearDone: (Boolean) -> Unit,
) {
    if (editing != null) {
        var value by remember(editing.text) { mutableStateOf(editing.text) }
        AlertDialog(
            onDismissRequest = { onEditDone(null) },
            title = { Text("Komutu düzenle") },
            text = {
                OutlinedTextField(
                    value = value,
                    onValueChange = { value = it },
                    modifier = Modifier.fillMaxWidth(),
                    maxLines = 4,
                )
            },
            confirmButton = { TextButton(onClick = { onEditDone(value) }, enabled = value.isNotBlank()) { Text("KAYDET") } },
            dismissButton = { TextButton(onClick = { onEditDone(null) }) { Text("VAZGEÇ") } },
        )
    }
    if (confirmClear) {
        AlertDialog(
            onDismissRequest = { onClearDone(false) },
            title = { Text("Geçmiş temizlensin mi?") },
            text = { Text("Sabitlenmiş komutlar kalır, diğerleri silinir.") },
            confirmButton = { TextButton(onClick = { onClearDone(true) }) { Text("TEMİZLE") } },
            dismissButton = { TextButton(onClick = { onClearDone(false) }) { Text("VAZGEÇ") } },
        )
    }
}

@Composable
private fun StatusHeader(code: String, busy: Boolean) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(start = 12.dp, end = 20.dp, top = 8.dp, bottom = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Reactor(Modifier.size(64.dp).floating().tilt3d(), busy = busy)
        Spacer(Modifier.size(10.dp))
        Column {
            Text("FRIDAY", style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary)
            Row(verticalAlignment = Alignment.CenterVertically) {
                StatusDot(if (busy) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.primary)
                Spacer(Modifier.size(6.dp))
                Text(
                    if (busy) "GÖNDERİLİYOR…" else "EŞLEŞTİ · $code",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun StatusDot(color: Color) {
    val pulse = rememberInfiniteTransition(label = "dot")
    val a by pulse.animateFloat(0.35f, 1f, infiniteRepeatable(tween(900), RepeatMode.Reverse), label = "a")
    Spacer(Modifier.size(8.dp).alpha(a).background(color, CircleShape))
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun HistoryRow(
    item: HistoryItem,
    modifier: Modifier = Modifier,
    onResend: () -> Unit,
    onEdit: () -> Unit,
    onPin: () -> Unit,
    onDelete: () -> Unit,
) {
    val time = remember(item.time) { DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(Date(item.time)) }
    var menu by remember { mutableStateOf(false) }
    var shown by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { shown = true }
    val haptics = LocalHapticFeedback.current
    AnimatedVisibility(
        visible = shown,
        modifier = modifier,
        enter = fadeIn(tween(260)) + slideInVertically(tween(320)) { it / 3 },
    ) {
        Card(
            modifier = Modifier.fillMaxWidth().tilt3d().combinedClickable(
                onClick = onResend,
                onLongClick = { haptics.performHapticFeedback(HapticFeedbackType.LongPress); menu = true },
            ),
            shape = MaterialTheme.shapes.medium,
            colors = CardDefaults.cardColors(
                containerColor = if (item.pinned) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.45f) else MaterialTheme.colorScheme.surface,
            ),
            border = BorderStroke(1.dp, if (item.pinned) MaterialTheme.colorScheme.primary.copy(alpha = 0.5f) else MaterialTheme.colorScheme.outlineVariant),
        ) {
            Row(Modifier.padding(start = 14.dp, top = 10.dp, bottom = 10.dp, end = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        if (item.pinned) {
                            Icon(Icons.Filled.PushPin, contentDescription = "Sabitlendi", tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(14.dp))
                            Spacer(Modifier.size(6.dp))
                        }
                        Text(item.text, color = MaterialTheme.colorScheme.onSurface, maxLines = 3, overflow = TextOverflow.Ellipsis)
                    }
                    Spacer(Modifier.height(4.dp))
                    Text(
                        (if (item.delivered) "İLETİLDİ" else "İLETİLEMEDİ") + " · $time",
                        style = MaterialTheme.typography.labelMedium,
                        color = if (item.delivered) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                    )
                }
                Box {
                    IconButton(onClick = { menu = true }) { Icon(Icons.Filled.MoreVert, contentDescription = "Komut seçenekleri") }
                    DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                        DropdownMenuItem(
                            text = { Text("Tekrar gönder") },
                            leadingIcon = { Icon(Icons.AutoMirrored.Filled.Send, null) },
                            onClick = { menu = false; onResend() },
                        )
                        DropdownMenuItem(
                            text = { Text("Düzenle") },
                            leadingIcon = { Icon(Icons.Filled.Edit, null) },
                            onClick = { menu = false; onEdit() },
                        )
                        DropdownMenuItem(
                            text = { Text(if (item.pinned) "Sabitlemeyi kaldır" else "Sabitle") },
                            leadingIcon = { Icon(Icons.Filled.PushPin, null) },
                            onClick = { menu = false; onPin() },
                        )
                        DropdownMenuItem(
                            text = { Text("Sil", color = MaterialTheme.colorScheme.error) },
                            leadingIcon = { Icon(Icons.Filled.Delete, null, tint = MaterialTheme.colorScheme.error) },
                            onClick = { menu = false; onDelete() },
                        )
                    }
                }
            }
        }
    }
}

// ---------- Uyandırma ----------

@Composable
fun WakeScreen(state: UiState, onWake: (WakeConfig) -> Unit) {
    var mac by rememberSaveable(state.wake) { mutableStateOf(state.wake.mac) }
    var ip by rememberSaveable(state.wake) { mutableStateOf(state.wake.ip) }
    var port by rememberSaveable(state.wake) { mutableStateOf(state.wake.port) }
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).imePadding().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text("BİLGİSAYARIMI UYANDIR", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
        Text(
            "Telefon ve bilgisayar aynı Wi-Fi ağında olmalı; bilgisayarda Wake-on-LAN açık olmalı. Bilgiler cihazında saklanır.",
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        OutlinedTextField(
            value = mac,
            onValueChange = { mac = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text("MAC ADRESİ") },
            placeholder = { Text("AA:BB:CC:DD:EE:FF") },
        )
        OutlinedTextField(
            value = ip,
            onValueChange = { ip = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text("IP ADRESİ") },
            placeholder = { Text("192.168.1.20") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
        )
        OutlinedTextField(
            value = port,
            onValueChange = { port = it.filter(Char::isDigit).take(5) },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text("PORT") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
        )
        Button(
            onClick = { onWake(WakeConfig(mac, ip, port)) },
            enabled = !state.waking,
            modifier = Modifier.fillMaxWidth().height(56.dp).pressDepth(),
        ) {
            if (state.waking) {
                CircularProgressIndicator(modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
            } else {
                Text("UYANDIRMA PAKETİ GÖNDER", style = MaterialTheme.typography.labelLarge)
            }
        }
    }
}

// ---------- Ayarlar ----------

@Composable
fun SettingsScreen(state: UiState, actions: PlatformActions, onForget: () -> Unit, onForgetLan: () -> Unit) {
    var confirm by remember { mutableStateOf(false) }
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text("AYARLAR", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
        Text("EŞLEŞME", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text("Bilgisayarla eşleşti · kod ${state.pairingCode}")
        OutlinedButton(onClick = actions.scanQr, modifier = Modifier.fillMaxWidth().pressDepth()) {
            Text("YENİDEN EŞLEŞTİR", style = MaterialTheme.typography.labelLarge)
        }
        OutlinedButton(onClick = { confirm = true }, modifier = Modifier.fillMaxWidth().pressDepth()) {
            Text("EŞLEŞMEYİ SİL", style = MaterialTheme.typography.labelLarge)
        }
        HorizontalDivider(color = MaterialTheme.colorScheme.outline)
        Text("YEREL BAĞLANTI", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        if (state.lanHost.isEmpty()) {
            Text("Aynı Wi-Fi'de telefon mikrofonu için bilgisayardaki telefon QR'ını okut.")
        } else {
            Text("Kayıtlı: ${state.lanHost}")
            OutlinedButton(onClick = onForgetLan, modifier = Modifier.fillMaxWidth().pressDepth()) {
                Text("YEREL BAĞLANTIYI SİL", style = MaterialTheme.typography.labelLarge)
            }
        }
        HorizontalDivider(color = MaterialTheme.colorScheme.outline)
        OutlinedButton(onClick = actions.openSite, modifier = Modifier.fillMaxWidth().pressDepth()) {
            Text("SİTEYİ AÇ", style = MaterialTheme.typography.labelLarge)
        }
        Text(
            "FRIDAY ${actions.versionName}",
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
    if (confirm) {
        AlertDialog(
            onDismissRequest = { confirm = false },
            title = { Text("Eşleşme silinsin mi?") },
            text = { Text("Komut göndermek için QR kodu yeniden okutman gerekir.") },
            confirmButton = { TextButton(onClick = { confirm = false; onForget() }) { Text("SİL") } },
            dismissButton = { TextButton(onClick = { confirm = false }) { Text("VAZGEÇ") } },
        )
    }
}
