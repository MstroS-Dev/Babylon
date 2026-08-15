package com.babylon.site.ui

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.widget.ArrayAdapter
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
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
    private var photoFile: File? = null   // keep the real File alongside the content Uri -
                                           // uri.path is NOT a filesystem path for FileProvider URIs.
    private val scope = MainScope()

    private val takePicture = registerForActivityResult(ActivityResultContracts.TakePicture()) { success ->
        if (success) {
            binding.photoPreview.setImageURI(photoUri)
        } else {
            android.widget.Toast.makeText(this, "Photo capture cancelled or failed", android.widget.Toast.LENGTH_SHORT).show()
        }
    }

    private val requestCameraPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) launchCamera() else {
            android.widget.Toast.makeText(this, "Camera permission is needed to take your profile photo", android.widget.Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityRegisterBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val langLabels = SUPPORTED_LANGUAGES.map { it.label }
        binding.languageSpinner.adapter = ArrayAdapter(
            this, android.R.layout.simple_spinner_dropdown_item, langLabels
        )

        binding.takePhotoButton.setOnClickListener { onTakePhotoTapped() }

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

    private fun onTakePhotoTapped() {
        val hasCamera = ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) ==
            PackageManager.PERMISSION_GRANTED
        if (hasCamera) launchCamera() else requestCameraPermission.launch(Manifest.permission.CAMERA)
    }

    private fun launchCamera() {
        val file = File(cacheDir, "profile_${System.currentTimeMillis()}.jpg")
        photoFile = file
        photoUri = androidx.core.content.FileProvider.getUriForFile(
            this, "$packageName.fileprovider", file
        )
        takePicture.launch(photoUri)
    }

    private fun registerWorker(name: String, langCode: String) {
        binding.registerButton.isEnabled = false
        scope.launch(Dispatchers.IO) {
            try {
                val api = SiteCommsApi.create()
                val namePart = name.toRequestBody("text/plain".toMediaTypeOrNull())
                val langPart = langCode.toRequestBody("text/plain".toMediaTypeOrNull())

                // Use the File we already have, never Uri.path (not a real path for
                // FileProvider content:// URIs - this was silently producing a bogus,
                // unreadable file and crashing the upload).
                val photoPart = photoFile?.takeIf { it.exists() }?.let { file ->
                    val body = file.asRequestBody("image/jpeg".toMediaTypeOrNull())
                    MultipartBody.Part.createFormData("photo", file.name, body)
                }

                val response = api.registerWorker(namePart, langPart, null, photoPart)
                launch(Dispatchers.Main) {
                    binding.registerButton.isEnabled = true
                    if (response.isSuccessful) {
                        val workerId = response.body()?.id
                        if (workerId == null) {
                            binding.nameInput.error = "Server didn't return a worker id - try again"
                            return@launch
                        }
                        getSharedPreferences("site_comms", MODE_PRIVATE).edit()
                            .putString("worker_id", workerId)
                            .putString("language", langCode)
                            .apply()
                        startActivity(Intent(this@RegisterActivity, TaskListActivity::class.java))
                        finish()
                    } else {
                        binding.nameInput.error = "Registration failed (${response.code()}) - check server connection"
                    }
                }
            } catch (e: Exception) {
                launch(Dispatchers.Main) {
                    binding.registerButton.isEnabled = true
                    binding.nameInput.error = "Couldn't reach server: ${e.message}"
                }
            }
        }
    }
}
