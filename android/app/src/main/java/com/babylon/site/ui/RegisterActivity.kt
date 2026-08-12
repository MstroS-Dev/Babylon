package com.babylon.site.ui

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.MediaStore
import android.widget.ArrayAdapter
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.babylon.site.data.SUPPORTED_LANGUAGES
import com.babylon.site.data.SiteCommsApi
import com.babylon.site.databinding.ActivityRegisterBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.MainScope
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File

class RegisterActivity : AppCompatActivity() {

    private lateinit var binding: ActivityRegisterBinding
    private var photoUri: Uri? = null
    private val scope = MainScope()

    private val takePicture = registerForActivityResult(ActivityResultContracts.TakePicture()) { success ->
        if (success) binding.photoPreview.setImageURI(photoUri)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityRegisterBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val langLabels = SUPPORTED_LANGUAGES.map { it.label }
        binding.languageSpinner.adapter = ArrayAdapter(
            this, android.R.layout.simple_spinner_dropdown_item, langLabels
        )

        binding.takePhotoButton.setOnClickListener {
            val photoFile = File(cacheDir, "profile_${System.currentTimeMillis()}.jpg")
            photoUri = androidx.core.content.FileProvider.getUriForFile(
                this, "$packageName.fileprovider", photoFile
            )
            takePicture.launch(photoUri)
        }

        binding.registerButton.setOnClickListener {
            val name = binding.nameInput.text.toString().trim()
            val langIndex = binding.languageSpinner.selectedItemPosition
            if (name.isEmpty()) {
                binding.nameInput.error = "Enter your name"
                return@setOnClickListener
            }
            val langCode = SUPPORTED_LANGUAGES[langIndex].code
            registerWorker(name, langCode)
        }
    }

    private fun registerWorker(name: String, langCode: String) {
        scope.launch(Dispatchers.IO) {
            try {
                val api = SiteCommsApi.create()
                val namePart = name.toRequestBody("text/plain".toMediaTypeOrNull())
                val langPart = langCode.toRequestBody("text/plain".toMediaTypeOrNull())

                val photoPart = photoUri?.let { uri ->
                    val file = File(uri.path ?: return@let null)
                    val body = file.asRequestBody("image/jpeg".toMediaTypeOrNull())
                    MultipartBody.Part.createFormData("photo", file.name, body)
                }

                val response = api.registerWorker(namePart, langPart, null, photoPart)
                launch(Dispatchers.Main) {
                    if (response.isSuccessful) {
                        val workerId = response.body()?.id
                        getSharedPreferences("site_comms", MODE_PRIVATE).edit()
                            .putString("worker_id", workerId)
                            .putString("language", langCode)
                            .apply()
                        startActivity(Intent(this@RegisterActivity, TaskListActivity::class.java))
                        finish()
                    } else {
                        binding.nameInput.error = "Registration failed - check server connection"
                    }
                }
            } catch (e: Exception) {
                launch(Dispatchers.Main) {
                    binding.nameInput.error = "Couldn't reach server: ${e.message}"
                }
            }
        }
    }
}
