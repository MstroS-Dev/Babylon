package com.babylon.site.ui

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.babylon.site.data.ApkUpdateInfo
import com.babylon.site.data.SiteCommsApi
import com.babylon.site.data.TaskDto
import com.babylon.site.databinding.ActivityTaskListBinding
import com.babylon.site.util.AppUpdater
import com.babylon.site.util.OnDeviceTranslator
import com.babylon.site.util.TaskSpeaker
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class TaskListActivity : AppCompatActivity() {

    private lateinit var binding: ActivityTaskListBinding
    private lateinit var adapter: TaskAdapter
    private lateinit var translator: OnDeviceTranslator
    private lateinit var speaker: TaskSpeaker
    private val scope = MainScope()
    private lateinit var workerLang: String
    private lateinit var workerId: String
    private var pollingJob: Job? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityTaskListBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val prefs = getSharedPreferences("site_comms", MODE_PRIVATE)
        val storedWorkerId = prefs.getString("worker_id", null)
        workerLang = prefs.getString("language", "en") ?: "en"

        if (storedWorkerId == null) {
            startActivity(android.content.Intent(this, RegisterActivity::class.java))
            finish()
            return
        }
        workerId = storedWorkerId

        // Manager writes tasks in Hebrew/English - assume 'he' as source for now.
        // (Swap for whatever the manager's actual language is.)
        translator = OnDeviceTranslator("he", workerLang)
        translator.ensureModelDownloaded(onReady = {}, onError = {})
        speaker = TaskSpeaker(this, workerLang)

        adapter = TaskAdapter(
            onSpeak = { text -> speaker.speak(text) },
            onOpen = { task -> openTaskDetail(task) },
        )
        binding.taskRecycler.layoutManager = LinearLayoutManager(this)
        binding.taskRecycler.adapter = adapter

        binding.swipeRefresh.setOnRefreshListener { loadTasks(showSpinner = true) }
        loadTasks(showSpinner = true)
        registerDeviceTokenIfAvailable(workerId)
        checkForAppUpdate()
    }

    /**
     * Polls the task list every 30s while this screen is actually visible,
     * silently (no spinner, no visible refresh) unless the user pulls to
     * refresh themselves. Started in onResume/stopped in onPause rather
     * than tied to onCreate/onDestroy: that's what makes this naturally
     * stop the moment a worker opens a task's detail screen (this activity
     * is paused underneath it) - nothing pulls them out of what they're
     * looking at, and polling picks back up the moment they return here.
     */
    private fun startPolling() {
        pollingJob?.cancel()
        pollingJob = scope.launch(Dispatchers.IO) {
            while (isActive) {
                delay(30_000)
                if (isActive) loadTasks(showSpinner = false)
            }
        }
    }

    override fun onResume() {
        super.onResume()
        startPolling()
    }

    override fun onPause() {
        super.onPause()
        pollingJob?.cancel()
    }

    /**
     * Silently checks the server for a newer APK build. If one exists, shows
     * a persistent Snackbar with an "Update" action - tapping it downloads
     * the new APK and opens the system installer (which still needs one
     * final tap from the user; Android doesn't allow silent self-install
     * outside Google Play or enterprise device management).
     */
    private fun checkForAppUpdate() {
        scope.launch(Dispatchers.IO) {
            val update = AppUpdater.checkForUpdate() ?: return@launch
            launch(Dispatchers.Main) { promptUpdate(update) }
        }
    }

    private fun promptUpdate(update: ApkUpdateInfo) {
        Snackbar.make(
            binding.root,
            "A new update is available (v${update.version_name})",
            Snackbar.LENGTH_INDEFINITE,
        ).setAction("Update") {
            if (AppUpdater.canInstall(this)) {
                Toast.makeText(this, "Downloading update…", Toast.LENGTH_SHORT).show()
                AppUpdater.downloadAndInstall(this, update)
            } else {
                Toast.makeText(
                    this,
                    "Allow this app to install updates, then tap Update again",
                    Toast.LENGTH_LONG,
                ).show()
                AppUpdater.requestInstallPermission(this)
            }
        }.show()
    }

    /**
     * Sends the FCM token to the server so it can push new-task notifications.
     * No-ops until Firebase is wired into the app (see push.py on the server
     * for setup steps) - FirebaseMessaging.getInstance() isn't on the
     * classpath yet, so this is the drop-in point for that call once it is.
     */
    private fun registerDeviceTokenIfAvailable(workerId: String) {
        // TODO: once google-services.json is added and the Firebase Messaging
        // dependency is uncommented in build.gradle.kts, replace this with:
        //
        // FirebaseMessaging.getInstance().token.addOnSuccessListener { token ->
        //     scope.launch(Dispatchers.IO) {
        //         runCatching { SiteCommsApi.create().updateDeviceToken(workerId, token) }
        //     }
        // }
    }

    private fun loadTasks(showSpinner: Boolean) {
        scope.launch(Dispatchers.IO) {
            try {
                val api = SiteCommsApi.create()
                val response = api.listTasks()
                val myTasks = response.body()?.filter { it.worker_id == workerId } ?: emptyList()

                // Translate each task's title/description on-device for display
                val translated = myTasks.map { task ->
                    var translatedText = task.description
                    translator.translate(
                        task.description,
                        onResult = { translatedText = it },
                        onError = {},
                    )
                    task to translatedText
                }

                launch(Dispatchers.Main) {
                    adapter.submitList(myTasks)
                    if (showSpinner) binding.swipeRefresh.isRefreshing = false
                }
            } catch (e: Exception) {
                launch(Dispatchers.Main) { if (showSpinner) binding.swipeRefresh.isRefreshing = false }
            }
        }
    }

    private fun openTaskDetail(task: TaskDto) {
        val intent = android.content.Intent(this, TaskDetailActivity::class.java)
        intent.putExtra("task_id", task.id)
        intent.putExtra("task_title", task.title)
        intent.putExtra("task_description", task.description)
        intent.putExtra("task_status", task.status)
        intent.putExtra("task_photo_requirement", task.photo_requirement)
        startActivity(intent)
    }

    override fun onDestroy() {
        super.onDestroy()
        translator.close()
        speaker.shutdown()
    }
}
