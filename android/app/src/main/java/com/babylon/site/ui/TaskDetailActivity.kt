package com.babylon.site.ui

import android.net.Uri
import android.os.Bundle
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.babylon.site.data.SiteCommsApi
import com.babylon.site.databinding.ActivityTaskDetailBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File

class TaskDetailActivity : AppCompatActivity() {

    private lateinit var binding: ActivityTaskDetailBinding
    private val scope = MainScope()
    private lateinit var taskId: String
    private var pendingStage: String = "before"
    private var photoUri: Uri? = null

    private val takePicture = registerForActivityResult(ActivityResultContracts.TakePicture()) { success ->
        if (success) photoUri?.let { uploadPhoto(pendingStage, it) }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityTaskDetailBinding.inflate(layoutInflater)
        setContentView(binding.root)

        taskId = intent.getStringExtra("task_id") ?: return
        binding.detailTitle.text = intent.getStringExtra("task_title")
        binding.detailDescription.text = intent.getStringExtra("task_description")
        binding.detailStatus.text = intent.getStringExtra("task_status")

        binding.beforePhotoButton.setOnClickListener { capturePhoto("before") }
        binding.afterPhotoButton.setOnClickListener { capturePhoto("after") }
    }

    private fun capturePhoto(stage: String) {
        pendingStage = stage
        val photoFile = File(cacheDir, "task_${taskId}_${stage}_${System.currentTimeMillis()}.jpg")
        photoUri = androidx.core.content.FileProvider.getUriForFile(
            this, "$packageName.fileprovider", photoFile
        )
        takePicture.launch(photoUri)
    }

    private fun uploadPhoto(stage: String, uri: Uri) {
        scope.launch(Dispatchers.IO) {
            try {
                val api = SiteCommsApi.create()
                val file = File(uri.path ?: return@launch)
                val body = file.asRequestBody("image/jpeg".toMediaTypeOrNull())
                val part = MultipartBody.Part.createFormData("photos", file.name, body)
                val stagePart = stage.toRequestBody("text/plain".toMediaTypeOrNull())

                val response = api.uploadTaskPhoto(taskId, stagePart, listOf(part))
                launch(Dispatchers.Main) {
                    if (response.isSuccessful) {
                        binding.detailStatus.text = response.body()?.status
                    }
                }
            } catch (_: Exception) {
                // TODO: surface upload failure + retry to the worker
            }
        }
    }
}
