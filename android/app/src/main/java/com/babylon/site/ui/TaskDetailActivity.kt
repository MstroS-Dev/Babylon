package com.babylon.site.ui

import android.content.pm.PackageManager
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.speech.RecognizerIntent
import android.view.View
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.babylon.site.data.PhotoReviewDto
import com.babylon.site.data.SiteCommsApi
import com.babylon.site.databinding.ActivityTaskDetailBinding
import com.babylon.site.util.CountingRequestBody
import com.babylon.site.util.OnDeviceTranslator
import com.babylon.site.util.applyStatusPill
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
    private var photoRequirement: String? = null

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
        applyStatusPill(this, binding.detailStatus, intent.getStringExtra("task_status") ?: "")

        val photoRequirementText = intent.getStringExtra("task_photo_requirement")
        photoRequirement = photoRequirementText
        if (!photoRequirementText.isNullOrBlank()) {
            binding.detailPhotoRequirement.text = "📸 Required photo: $photoRequirementText"
            binding.detailPhotoRequirement.visibility = android.view.View.VISIBLE
        }

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

    private data class StageViews(val container: View, val thumbnail: android.widget.ImageView, val status: android.widget.TextView)

    private fun stageViews(stage: String): StageViews = if (stage == "before") {
        StageViews(binding.beforePhotoProgress, binding.beforePhotoThumbnail, binding.beforePhotoStatus)
    } else {
        StageViews(binding.afterPhotoProgress, binding.afterPhotoThumbnail, binding.afterPhotoStatus)
    }

    private fun uploadPhoto(stage: String, file: File) {
        if (!file.exists()) {
            binding.detailStatus.text = "Photo file went missing - try again"
            return
        }
        val views = stageViews(stage)

        // Stage 1: show the photo immediately and mark it uploading, before
        // any network activity even starts - the worker should never be
        // looking at a black/blank screen wondering if their tap registered.
        views.container.visibility = View.VISIBLE
        views.thumbnail.setImageBitmap(decodeThumbnail(file))
        setStageStatus(views, "📤 Uploading photo…", "#666666")

        scope.launch(Dispatchers.IO) {
            try {
                val api = SiteCommsApi.create()
                val fileBody = file.asRequestBody("image/jpeg".toMediaTypeOrNull())
                val countingBody = CountingRequestBody(fileBody) {
                    // Called once all bytes are actually sent - from here the
                    // wait is the server (and possibly the AI review), not
                    // the upload itself, so say so.
                    runOnUiThread { setStageStatus(views, "🤖 Checking your photo…", "#8A6D00") }
                }
                val part = MultipartBody.Part.createFormData("photos", file.name, countingBody)
                val stagePart = stage.toRequestBody("text/plain".toMediaTypeOrNull())

                val response = api.uploadTaskPhoto(taskId, stagePart, listOf(part))
                launch(Dispatchers.Main) {
                    if (response.isSuccessful) {
                        val responseBody = response.body()
                        binding.detailStatus.text = responseBody?.status
                        applyStatusPill(this@TaskDetailActivity, binding.detailStatus, responseBody?.status ?: "")
                        showPhotoResult(stage, views, responseBody?.photo_reviews?.lastOrNull())
                    } else {
                        setStageStatus(views, "❌ Upload failed - tap the button to retry", "#B71C1C")
                    }
                }
            } catch (e: Exception) {
                launch(Dispatchers.Main) {
                    setStageStatus(views, "❌ Upload failed: ${e.message} - tap the button to retry", "#B71C1C")
                }
            }
        }
    }

    private fun decodeThumbnail(file: File): android.graphics.Bitmap? {
        return try {
            val opts = BitmapFactory.Options().apply { inSampleSize = 4 } // fast, small - it's just a thumbnail
            BitmapFactory.decodeFile(file.absolutePath, opts)
        } catch (e: Exception) {
            null
        }
    }

    private fun setStageStatus(views: StageViews, text: String, colorHex: String) {
        views.status.text = text
        views.status.setTextColor(android.graphics.Color.parseColor(colorHex))
    }

    private fun showPhotoResult(stage: String, views: StageViews, review: PhotoReviewDto?) {
        // No photo_requirement was set on this task, so nothing was reviewed -
        // the upload itself succeeding is the whole story.
        if (review == null || review.verdict == null) {
            setStageStatus(views, "✅ Uploaded", "#1B5E20")
            announceIfReady(stage, blocked = false)
            return
        }
        when (review.verdict) {
            "match" -> {
                setStageStatus(views, "✅ Looks good!", "#1B5E20")
                announceIfReady(stage, blocked = false)
            }
            "no_match" -> {
                setStageStatus(views, "❌ That's not the correct item - please try again.", "#B71C1C")
                announceIfReady(stage, blocked = true)
            }
            else -> {
                setStageStatus(views, "🤔 Not sure yet - a manager will take a look.", "#8A6D00")
                announceIfReady(stage, blocked = false)
            }
        }
    }

    /** Appends the "you're clear to proceed" line once a stage's photo is
     * accepted (or didn't need review at all). Not shown when the photo was
     * rejected - the worker needs to retake it first. */
    private fun announceIfReady(stage: String, blocked: Boolean) {
        if (blocked) return
        val views = stageViews(stage)
        val announcement = if (stage == "before") {
            "\n✅ You can start working on this task now."
        } else {
            "\n✅ Task marked complete - nice work!"
        }
        views.status.append(announcement)
    }
}
