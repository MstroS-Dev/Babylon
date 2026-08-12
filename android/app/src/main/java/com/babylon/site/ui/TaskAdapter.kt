package com.babylon.site.ui

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.babylon.site.data.TaskDto
import com.babylon.site.databinding.ItemTaskBinding

class TaskAdapter(
    private val onSpeak: (String) -> Unit,
    private val onOpen: (TaskDto) -> Unit,
) : RecyclerView.Adapter<TaskAdapter.ViewHolder>() {

    private var tasks: List<TaskDto> = emptyList()

    fun submitList(newTasks: List<TaskDto>) {
        tasks = newTasks
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemTaskBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(tasks[position])
    }

    override fun getItemCount() = tasks.size

    inner class ViewHolder(private val binding: ItemTaskBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(task: TaskDto) {
            binding.taskTitle.text = task.title
            binding.taskDescription.text = task.description
            binding.taskStatus.text = task.status.replace("_", " ")
            binding.speakButton.setOnClickListener { onSpeak("${task.title}. ${task.description}") }
            binding.root.setOnClickListener { onOpen(task) }
        }
    }
}
