package com.babylon.site.ui

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.appcompat.app.AppCompatActivity
import com.babylon.site.R

/**
 * Launcher screen: shows the logo + app name briefly, then routes to
 * TaskListActivity if this device already registered as a worker, or
 * RegisterActivity if not. This is also what fixes the "registration
 * doesn't stick" bug - previously RegisterActivity itself was the
 * launcher and always showed a blank form on every app open, even
 * after a successful registration, because it never checked
 * SharedPreferences for an existing worker_id.
 */
class SplashActivity : AppCompatActivity() {

    private val splashDelayMs = 900L

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_splash)

        Handler(Looper.getMainLooper()).postDelayed({ routeNext() }, splashDelayMs)
    }

    private fun routeNext() {
        val prefs = getSharedPreferences("site_comms", MODE_PRIVATE)
        val workerId = prefs.getString("worker_id", null)

        val next = if (workerId != null) TaskListActivity::class.java else RegisterActivity::class.java
        startActivity(Intent(this, next))
        finish()
    }
}
