package com.babylon.site.util

import android.app.DownloadManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.Settings
import androidx.core.content.FileProvider
import com.babylon.site.BuildConfig
import com.babylon.site.data.ApiConfig
import com.babylon.site.data.ApkUpdateInfo
import com.babylon.site.data.SiteCommsApi

/**
 * Checks the server for a newer APK build, downloads it, and hands it off
 * to the system package installer. Android does not allow a normal
 * sideloaded app to silently replace itself - the final "Install" tap is
 * always the user's, even here. What this class automates is everything
 * up to that point: noticing a new build exists, fetching it, and opening
 * the installer screen for it.
 */
object AppUpdater {

    /** Hits /apk/latest.json and returns update info only if it's newer than
     * what's currently installed. Network I/O - call from a background
     * thread/coroutine. Returns null (never throws) if the server has no
     * build published yet, is unreachable, or we're already up to date -
     * an update check should never be able to crash or block the app. */
    suspend fun checkForUpdate(): ApkUpdateInfo? {
        return try {
            val response = SiteCommsApi.create().checkApkUpdate()
            val info = if (response.isSuccessful) response.body() else null
            if (info != null && info.version_code > BuildConfig.VERSION_CODE) info else null
        } catch (e: Exception) {
            null
        }
    }

    /** True if this app is currently allowed to prompt the install screen
     * for a downloaded APK. Only relevant on API 26+ (below that, it's
     * governed by a device-wide "unknown sources" toggle we can't query or
     * request programmatically - the install screen itself will surface a
     * warning with a settings shortcut on those older devices instead). */
    fun canInstall(context: Context): Boolean {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.O ||
            context.packageManager.canRequestPackageInstalls()
    }

    /** Sends the user to the system settings screen where they can allow
     * this app to install unknown apps. Call canInstall() again once they
     * return (e.g. in onResume) before retrying the download. */
    fun requestInstallPermission(context: Context) {
        val intent = Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES)
            .setData(Uri.parse("package:${context.packageName}"))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(intent)
    }

    private const val UPDATE_FILE_NAME = "update.apk"

    /** Downloads the APK via the system DownloadManager (handles retries and
     * shows progress in the notification shade), then opens the installer
     * once it lands. Registers a short-lived receiver for the download
     * completion broadcast - safe to call this multiple times; a stale
     * receiver from a previous call is unregistered first. */
    fun downloadAndInstall(context: Context, info: ApkUpdateInfo) {
        val downloadUrl = if (info.url.startsWith("http")) {
            info.url
        } else {
            ApiConfig.BASE_URL.trimEnd('/') + info.url
        }

        val downloadManager = context.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
        val request = DownloadManager.Request(Uri.parse(downloadUrl))
            .setTitle("Almegorim comms update")
            .setDescription("Downloading version ${info.version_name}")
            .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
            .setDestinationInExternalFilesDir(context, Environment.DIRECTORY_DOWNLOADS, UPDATE_FILE_NAME)
        val downloadId = downloadManager.enqueue(request)

        val receiver = object : BroadcastReceiver() {
            override fun onReceive(ctx: Context, intent: Intent) {
                val finishedId = intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1)
                if (finishedId != downloadId) return
                try {
                    ctx.applicationContext.unregisterReceiver(this)
                } catch (e: IllegalArgumentException) {
                    // Already unregistered - fine, nothing to clean up.
                }
                openInstaller(ctx, downloadManager, downloadId)
            }
        }

        val filter = IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            context.applicationContext.registerReceiver(receiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            context.applicationContext.registerReceiver(receiver, filter)
        }
    }

    private fun openInstaller(context: Context, downloadManager: DownloadManager, downloadId: Long) {
        val status = downloadManager.query(DownloadManager.Query().setFilterById(downloadId))?.use { cursor ->
            if (cursor.moveToFirst()) {
                cursor.getInt(cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS))
            } else null
        }
        if (status != DownloadManager.STATUS_SUCCESSFUL) return // failed/cancelled download - nothing to install

        val file = java.io.File(
            context.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS),
            UPDATE_FILE_NAME,
        )
        val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
        val installIntent = Intent(Intent.ACTION_VIEW)
            .setDataAndType(uri, "application/vnd.android.package-archive")
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(installIntent)
    }
}
