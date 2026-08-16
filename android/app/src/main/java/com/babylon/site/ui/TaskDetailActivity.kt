package com.babylon.site.ui

import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.speech.RecognizerIntent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.babylon.site.data.SiteCommsApi
import com.babylon.site.databinding.ActivityTaskDetailBinding
import com.babylon.site.util.OnDeviceTranslator
import com.babylon.site.util.buildSpeechRecognizerIntent
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File

// The manager's own language - same assumption TaskListActivity makes today.
// (Swap for whatever the manager's actual language is, once that's configurable.)
private const val MANAGER_LANGUAGE = "he"

class TaskDetailActivity : AppCompatActivity() {

    private lateinit var binding: ActivityTaskDetailBinding
    private val scope = MainScope()
    private lateinit var taskId: String
    private var pendingStage: String = "before"
    private var photoUri: Uri? = null
    private var photoFile: File? = null   // real File - uri.path is not a filesystem path for content:// URIs
    private lateinit var workerLang: String
    private var replyTranslator: OnDeviceTranslator? = null

    private val takePicture = registerForActivityResult(ActivityResultContracts.TakePicture()) { success ->
        if (success) {
            photoFile?.let { uploadPhoto(pendingStage, it) }
        } else {
            binding.detailStatus.text = "Photo capture cancelled or failed"
        }
    }

    private val requestCameraPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) launchCamera(pendingStage) else {
            binding.detailStatus.text = "Camera permission is needed to take the $pendingStage photo"
        }
    }

    private val speechRecognizer = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val text = result.data
            ?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
            ?.firstOrNull()
        if (text.isNullOrBlank()) {
            binding.replyStatus.text = "Didn't catch that - tap the mic and try again."
        } else {
            translateAndSendReply(text)
        }
    }

    private val requestMicPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) launchSpeechRecognizer() else {
            binding.replyStatus.text = "Microphone permission is needed to reply by voice."
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityTaskDetailBinding.inflate(layoutInflater)
        setContentView(binding.root)

        taskId = intent.getStringExtra("task_id") ?: return
        binding.detailTitle.text = intent.getStringExtra("task_title")
        binding.detailDescription.text = intent.getStringExtra("task_description")
        binding.detailStatus.text = intent.getStringExtra("task_status")

        workerLang = getSharedPreferences("site_comms", MODE_PRIVATE)
            .getString("language", "en") ?: "en"
        // Reply direction is the reverse of TaskListActivity's translator:
        // worker's language -> manager's language.
        replyTranslator = OnDeviceTranslator(workerLang, MANAGER_LANGUAGE)
        replyTranslator?.ensureModelDownloaded(onReady = {}, onError = {})

        binding.beforePhotoButton.setOnClickListener { capturePhoto("before") }
        binding.afterPhotoButton.setOnClickListener { capturePhoto("after") }
        binding.replyButton.setOnClickListener { onReplyTapped() }
    }

    private fun onReplyTapped() {
        val hasMic = ContextCompat.checkSelfPermission(this, android.Manifest.permission.RECORD_AUDIO) ==
            PackageManager.PERMISSION_GRANTED
        if (hasMic) launchSpeechRecognizer() else requestMicPermission.launch(android.Manifest.permission.RECORD_AUDIO)
    }

    private fun launchSpeechRecognizer() {
        binding.replyStatus.text = "Listening..."
        try {
            speechRecognizer.launch(buildSpeechRecognizerIntent(workerLang))
        } catch (e: Exception) {
            binding.replyStatus.text = "Voice input isn't available on this phone."
        }
    }

    private fun translateAndSendReply(originalText: String) {
        binding.replyStatus.text = "Translating..."
        replyTranslator?.translate(
            originalText,
            onResult = { translated -> sendReply(originalText, translated) },
            onError = {
                // Fall back to sending the untranslated text rather than losing the reply.
                sendReply(originalText, originalText)
            },
        )
    }

    private fun sendReply(originalText: String, translatedText: String) {
        scope.launch(Dispatchers.IO) {
            try {
                val api = SiteCommsApi.create()
                val response = api.sendReply(taskId, originalText, workerLang, translatedText, MANAGER_LANGUAGE)
                launch(Dispatchers.Main) {
                    binding.replyStatus.text =
                        if (response.isSuccessful) "Sent: \"$originalText\""
                        else "Couldn't send reply - check connection."
                }
            } catch (e: Exception) {
                launch(Dispatchers.Main) { binding.replyStatus.text = "Couldn't send reply: ${e.message}" }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        replyTranslator?.close()
    }

    private fun capturePhoto(stage: String) {
        pendingStage = stage
        val hasCamera = ContextCompat.checkSelfPermission(this, android.Manifest.permission.CAMERA) ==
            PackageManager.PERMISSION_GRANTED
        if (hasCamera) launchCamera(stage) else requestCameraPermission.launch(android.Manifest.permission.CAMERA)
    }

    private fun launchCamera(stage: String) {
        val file = File(cacheDir, "task_${taskId}_${stage}_${System.currentTimeMillis()}.jpg")
        photoFile = file
        photoUri = androidx.core.content.FileProvider.getUriForFile(
            this, "$packageName.fileprovider", file
        )
        takePicture.launch(photoUri)
    }

    private fun uploadPhoto(stage: String, file: File) {
        if (!file.exists()) {
            binding.detailStatus.text = "Photo file went missing - try again"
            return
        }
        scope.launch(Dispatchers.IO) {
            try {
                val api = SiteCommsApi.create()
                val body = file.asRequestBody("image/jpeg".toMediaTypeOrNull())
                val part = MultipartBody.Part.createFormData("photos", file.name, body)
                val stagePart = stage.toRequestBody("text/plain".toMediaTypeOrNull())

                val response = api.uploadTaskPhoto(taskId, stagePart, listOf(part))
                launch(Dispatchers.Main) {
                    if (response.isSuccessful) {
                        binding.detailStatus.text = response.body()?.status
                    }
                }
            } catch (e: Exception) {
                launch(Dispatchers.Main) {
                    binding.detailStatus.text = "Photo upload failed: ${e.message} - tap the button to retry"
                }
            }
        }
    }
}
