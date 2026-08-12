package com.babylon.site.ui

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.babylon.site.data.SiteCommsApi
import com.babylon.site.data.TaskDto
import com.babylon.site.databinding.ActivityTaskListBinding
import com.babylon.site.util.OnDeviceTranslator
import com.babylon.site.util.TaskSpeaker
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.launch

class TaskListActivity : AppCompatActivity() {

    private lateinit var binding: ActivityTaskListBinding
    private lateinit var adapter: TaskAdapter
    private lateinit var translator: OnDeviceTranslator
    private lateinit var speaker: TaskSpeaker
    private val scope = MainScope()
    private lateinit var workerLang: String

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityTaskListBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val prefs = getSharedPreferences("site_comms", MODE_PRIVATE)
        val workerId = prefs.getString("worker_id", null)
        workerLang = prefs.getString("language", "en") ?: "en"

        if (workerId == null) {
            startActivity(android.content.Intent(this, RegisterActivity::class.java))
            finish()
            return
        }

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

        binding.swipeRefresh.setOnRefreshListener { loadTasks(workerId) }
        loadTasks(workerId)
    }

    private fun loadTasks(workerId: String) {
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
                    binding.swipeRefresh.isRefreshing = false
                }
            } catch (e: Exception) {
                launch(Dispatchers.Main) { binding.swipeRefresh.isRefreshing = false }
            }
        }
    }

    private fun openTaskDetail(task: TaskDto) {
        val intent = android.content.Intent(this, TaskDetailActivity::class.java)
        intent.putExtra("task_id", task.id)
        intent.putExtra("task_title", task.title)
        intent.putExtra("task_description", task.description)
        intent.putExtra("task_status", task.status)
        startActivity(intent)
    }

    override fun onDestroy() {
        super.onDestroy()
        translator.close()
        speaker.shutdown()
    }
}
