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
import com.babylon.site.util.LanguageDetector
import com.babylon.site.util.OnDeviceTranslator
import com.babylon.site.util.TaskSpeaker
import com.babylon.site.util.shiftStrings
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
    // Keyed by detected source language, so we don't rebuild a translator
    // (and re-trigger a model download) for every single task - most tasks
    // from the same manager will detect as the same source language.
    private val translators = mutableMapOf<String, OnDeviceTranslator>()
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
        setupShiftBar()
    }

    /**
     * Sets up the always-visible top status bar: connection state text plus
     * a Check In / Check Out button (the visible one reflects the worker's
     * current state, fetched from the server on launch). This bar is what
     * keeps the screen from ever looking blank/dead when there are simply
     * no tasks right now - there's always something here.
     */
    private fun setupShiftBar() {
        val strings = shiftStrings(workerLang)
        binding.checkInButton.text = strings.checkIn
        binding.checkOutButton.text = strings.checkOut

        binding.checkInButton.setOnClickListener { setCheckedIn(true) }
        binding.checkOutButton.setOnClickListener { setCheckedIn(false) }

        scope.launch(Dispatchers.IO) {
            try {
                val workers = SiteCommsApi.create().listWorkers().body() ?: emptyList()
                val me = workers.find { it.id == workerId }
                launch(Dispatchers.Main) { applyCheckedInState(me?.checked_in ?: false) }
            } catch (e: Exception) {
                // Leave both buttons hidden rather than guessing - next
                // successful poll/resume will pick the real state up.
            }
        }
    }

    private fun setCheckedIn(checkedIn: Boolean) {
        val strings = shiftStrings(workerLang)
        scope.launch(Dispatchers.IO) {
            try {
                val api = SiteCommsApi.create()
                val response = if (checkedIn) api.checkIn(workerId) else api.checkOut(workerId)
                launch(Dispatchers.Main) {
                    if (response.isSuccessful) {
                        applyCheckedInState(checkedIn)
                        Toast.makeText(
                            this@TaskListActivity,
                            if (checkedIn) strings.checkedIn else strings.checkedOut,
                            Toast.LENGTH_SHORT,
                        ).show()
                    } else {
                        Toast.makeText(this@TaskListActivity, "Couldn't update - try again", Toast.LENGTH_SHORT).show()
                    }
                }
            } catch (e: Exception) {
                launch(Dispatchers.Main) {
                    Toast.makeText(this@TaskListActivity, "Couldn't update: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun applyCheckedInState(checkedIn: Boolean) {
        binding.checkInButton.visibility = if (checkedIn) android.view.View.GONE else android.view.View.VISIBLE
        binding.checkOutButton.visibility = if (checkedIn) android.view.View.VISIBLE else android.view.View.GONE
    }

    private fun setConnectionStatus(connected: Boolean) {
        val strings = shiftStrings(workerLang)
        binding.connectionStatus.text = if (connected) "🟢 ${strings.connected}" else "🔴 ${strings.offline}"
        val color = android.graphics.Color.parseColor(
            if (connected) "#0F766E" else "#6B7280"
        )
        // The bar's background is a rounded-corner shape drawable, not a
        // flat color - tinting it (rather than replacing the background
        // outright) keeps the rounded corners intact.
        val mutableBackground = binding.statusBar.background.mutate()
        androidx.core.graphics.drawable.DrawableCompat.setTint(mutableBackground, color)
        binding.statusBar.background = mutableBackground
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
                val displayTasks = myTasks.map { translateForDisplay(it) }

                launch(Dispatchers.Main) {
                    adapter.submitList(displayTasks)
                    binding.emptyStateText.text = shiftStrings(workerLang).noTasksYet
                    binding.emptyStateText.visibility = if (displayTasks.isEmpty()) android.view.View.VISIBLE else android.view.View.GONE
                    setConnectionStatus(connected = true)
                    if (showSpinner) binding.swipeRefresh.isRefreshing = false
                }
            } catch (e: Exception) {
                launch(Dispatchers.Main) {
                    setConnectionStatus(connected = false)
                    if (showSpinner) binding.swipeRefresh.isRefreshing = false
                }
            }
        }
    }

    /**
     * Detects the actual language a task was typed in (rather than
     * assuming a fixed one - a manager may type in Hebrew, English, or a
     * mix) and translates its title/description into the worker's chosen
     * language. If detection is inconclusive, or the task is already in
     * the worker's language, or translation fails for any reason, falls
     * back to the original text - a worker seeing untranslated text is a
     * much smaller problem than a crash or a garbled mistranslation.
     */
    private suspend fun translateForDisplay(task: TaskDto): TaskDto {
        val sourceLang = LanguageDetector.detect("${task.title}. ${task.description}") ?: return task
        if (sourceLang == workerLang) return task // already in the worker's language

        return try {
            val translator = translators.getOrPut(sourceLang) { OnDeviceTranslator(sourceLang, workerLang) }
            // Safe to call every time, not just on first creation - ML Kit
            // resolves immediately once the model's already on-device, so
            // this only actually downloads anything the first time a given
            // source language shows up.
            translator.ensureModelDownloadedSuspend()
            task.copy(
                title = translator.translateSuspend(task.title),
                description = translator.translateSuspend(task.description),
            )
        } catch (e: Exception) {
            task // translation failed (e.g. model download failed) - show the original rather than crash
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
        translators.values.forEach { it.close() }
        speaker.shutdown()
    }
}
