package com.friday.phone.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.input.ImeAction
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
    ) {
        Text("FRIDAY", style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary)
        Spacer(Modifier.height(12.dp))
        if (state.pendingKey.isEmpty()) {
            Text(
                "Bilgisayarındaki FRIDAY'de Ayarlar › Telefon bölümünü aç ve oradaki QR kodu okut.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(28.dp))
            Button(onClick = onScan, modifier = Modifier.fillMaxWidth().height(56.dp)) {
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
            Button(onClick = { onConfirm(code) }, enabled = code.length == 6, modifier = Modifier.fillMaxWidth().height(56.dp)) {
                Text("ONAYLA", style = MaterialTheme.typography.labelLarge)
            }
            TextButton(onClick = { code = ""; onCancel() }, modifier = Modifier.fillMaxWidth()) {
                Text("VAZGEÇ", style = MaterialTheme.typography.labelLarge)
            }
        }
    }
}

// ---------- Komut ----------

@Composable
fun CommandScreen(state: UiState, onSend: (String) -> Unit, onListen: () -> Unit, onToggleLanMic: () -> Unit) {
    var text by rememberSaveable { mutableStateOf("") }
    val haptics = LocalHapticFeedback.current
    val submit = {
        if (text.isNotBlank() && !state.sending) {
            haptics.performHapticFeedback(HapticFeedbackType.TextHandleMove)
            onSend(text)
            text = ""
        }
    }
    Column(Modifier.fillMaxSize()) {
        StatusHeader(state.pairingCode)
        if (state.lanHost.isNotEmpty()) {
            OutlinedButton(
                onClick = onToggleLanMic,
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
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
                items(state.history, key = { it.text }) { item -> HistoryRow(item) { onSend(item.text) } }
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
                maxLines = 3,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { submit() }),
            )
            IconButton(onClick = onListen) { Icon(Icons.Filled.Mic, contentDescription = "Konuş") }
            FilledIconButton(onClick = { submit() }, enabled = text.isNotBlank() && !state.sending) {
                if (state.sending) {
                    CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                } else {
                    Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Gönder")
                }
            }
        }
    }
}

@Composable
private fun StatusHeader(code: String) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("FRIDAY", style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary)
        Spacer(Modifier.weight(1f))
        StatusDot(MaterialTheme.colorScheme.primary)
        Spacer(Modifier.size(8.dp))
        Text("EŞLEŞTİ · $code", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun StatusDot(color: Color) {
    Spacer(Modifier.size(8.dp).background(color, CircleShape))
}

@Composable
private fun HistoryRow(item: HistoryItem, onResend: () -> Unit) {
    val time = remember(item.time) { DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(Date(item.time)) }
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onResend),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
    ) {
        Column(Modifier.padding(14.dp)) {
            Text(item.text, color = MaterialTheme.colorScheme.onSurface)
            Spacer(Modifier.height(4.dp))
            Text(
                (if (item.delivered) "İLETİLDİ" else "İLETİLEMEDİ") + " · $time · tekrar göndermek için dokun",
                style = MaterialTheme.typography.labelMedium,
                color = if (item.delivered) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
            )
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
            modifier = Modifier.fillMaxWidth().height(56.dp),
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
        OutlinedButton(onClick = actions.scanQr, modifier = Modifier.fillMaxWidth()) {
            Text("YENİDEN EŞLEŞTİR", style = MaterialTheme.typography.labelLarge)
        }
        OutlinedButton(onClick = { confirm = true }, modifier = Modifier.fillMaxWidth()) {
            Text("EŞLEŞMEYİ SİL", style = MaterialTheme.typography.labelLarge)
        }
        HorizontalDivider(color = MaterialTheme.colorScheme.outline)
        Text("YEREL BAĞLANTI", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        if (state.lanHost.isEmpty()) {
            Text("Aynı Wi-Fi'de telefon mikrofonu için bilgisayardaki telefon QR'ını okut.")
        } else {
            Text("Kayıtlı: ${state.lanHost}")
            OutlinedButton(onClick = onForgetLan, modifier = Modifier.fillMaxWidth()) {
                Text("YEREL BAĞLANTIYI SİL", style = MaterialTheme.typography.labelLarge)
            }
        }
        HorizontalDivider(color = MaterialTheme.colorScheme.outline)
        OutlinedButton(onClick = actions.openSite, modifier = Modifier.fillMaxWidth()) {
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
