package com.friday.phone

import android.Manifest
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.speech.RecognizerIntent
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.core.content.ContextCompat
import com.friday.phone.domain.SITE
import com.friday.phone.ui.FridayApp
import com.friday.phone.ui.FridayTheme
import com.friday.phone.ui.FridayViewModel
import com.friday.phone.ui.PlatformActions
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions

/** Yalnızca telefona özgü işleri (kamera, ses tanıma, açılış bağlantısı) yapar; ekran ve mantık ui/ ile domain/ içinde. */
class MainActivity : ComponentActivity() {
    private val viewModel: FridayViewModel by viewModels()

    private val scan = registerForActivityResult(ScanContract()) { result ->
        val text = result.contents?.trim().orEmpty()
        if (text.isNotEmpty()) viewModel.onLink(text)
    }
    private val cameraPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) openScanner() else viewModel.say("QR okumak için kamera izni gerekli.")
    }
    private val hear = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val said = result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull().orEmpty()
        viewModel.onHeard(said)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        if (savedInstanceState == null) intent?.dataString?.let(viewModel::onLink)
        val actions = PlatformActions(
            scanQr = ::requestScan,
            listen = ::listen,
            openSite = ::openSite,
            versionName = versionName(),
        )
        setContent { FridayTheme { FridayApp(viewModel, actions) } }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        intent.dataString?.let(viewModel::onLink)
    }

    private fun requestScan() {
        val granted = ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
        if (granted) openScanner() else cameraPermission.launch(Manifest.permission.CAMERA)
    }

    private fun openScanner() {
        val options = ScanOptions()
        options.setDesiredBarcodeFormats(ScanOptions.QR_CODE)
        options.setPrompt("Bilgisayardaki QR kodu okut")
        options.setBeepEnabled(false)
        scan.launch(options)
    }

    private fun listen() {
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE, "tr-TR")
            .putExtra(RecognizerIntent.EXTRA_PROMPT, "Bilgisayara söyle")
        try {
            hear.launch(intent)
        } catch (_: ActivityNotFoundException) {
            viewModel.say("Bu telefonda ses tanıma yok.")
        }
    }

    private fun openSite() {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(SITE)))
        } catch (_: ActivityNotFoundException) {
            viewModel.say("Tarayıcı bulunamadı.")
        }
    }

    @Suppress("DEPRECATION")
    private fun versionName(): String =
        runCatching { packageManager.getPackageInfo(packageName, 0).versionName }.getOrNull().orEmpty()
}
