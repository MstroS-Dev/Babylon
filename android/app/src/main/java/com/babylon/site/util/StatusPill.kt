package com.babylon.site.util

import android.content.Context
import androidx.core.content.ContextCompat
import com.babylon.site.R

/** Text color res, background color res for a task status pill. Shared
 * between the task list cards and the task detail screen so a given
 * status always reads the same color everywhere it shows up. */
fun statusPillColors(status: String): Pair<Int, Int> = when (status) {
    "done" -> R.color.status_success to R.color.status_success_bg
    "in_progress" -> R.color.status_warning to R.color.status_warning_bg
    else -> R.color.status_neutral to R.color.status_neutral_bg // "assigned" and anything else
}

fun applyStatusPill(context: Context, textView: android.widget.TextView, status: String) {
    val (textColorRes, bgColorRes) = statusPillColors(status)
    textView.setTextColor(ContextCompat.getColor(context, textColorRes))
    textView.backgroundTintList = ContextCompat.getColorStateList(context, bgColorRes)
}
