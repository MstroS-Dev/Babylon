package com.babylon.site.util

import com.google.mlkit.nl.translate.TranslateLanguage
import com.google.mlkit.nl.translate.Translation
import com.google.mlkit.nl.translate.Translator
import com.google.mlkit.nl.translate.TranslatorOptions
import com.google.mlkit.common.model.DownloadConditions
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/**
 * Wraps ML Kit's on-device translator. Downloads the language pack once
 * (needs wifi/data the first time), then works fully offline after that -
 * important for a construction site with unreliable internet.
 */
class OnDeviceTranslator(sourceLangCode: String, targetLangCode: String) {

    private val translator: Translator

    init {
        val options = TranslatorOptions.Builder()
            .setSourceLanguage(mlKitCode(sourceLangCode))
            .setTargetLanguage(mlKitCode(targetLangCode))
            .build()
        translator = Translation.getClient(options)
    }

    /** Call once (e.g. on first app launch or language change) before translating. */
    fun ensureModelDownloaded(onReady: () -> Unit, onError: (Exception) -> Unit) {
        val conditions = DownloadConditions.Builder().build() // allows any network by default
        translator.downloadModelIfNeeded(conditions)
            .addOnSuccessListener { onReady() }
            .addOnFailureListener { onError(it) }
    }

    suspend fun ensureModelDownloadedSuspend() = suspendCancellableCoroutine<Unit> { cont ->
        val conditions = DownloadConditions.Builder().build()
        translator.downloadModelIfNeeded(conditions)
            .addOnSuccessListener { if (cont.isActive) cont.resume(Unit) }
            .addOnFailureListener { if (cont.isActive) cont.resumeWithException(it) }
    }

    fun translate(text: String, onResult: (String) -> Unit, onError: (Exception) -> Unit) {
        translator.translate(text)
            .addOnSuccessListener { onResult(it) }
            .addOnFailureListener { onError(it) }
    }

    /** Suspending version of translate() - actually waits for the ML Kit
     * result instead of returning before the callback fires. The plain
     * callback version above is easy to misuse in a loop (map/forEach
     * moves on before onResult ever runs, silently leaving the original
     * untranslated text in place) - prefer this one for anything that
     * needs the translated text before proceeding. */
    suspend fun translateSuspend(text: String): String = suspendCancellableCoroutine { cont ->
        translator.translate(text)
            .addOnSuccessListener { if (cont.isActive) cont.resume(it) }
            .addOnFailureListener { if (cont.isActive) cont.resumeWithException(it) }
    }

    fun close() = translator.close()

    private fun mlKitCode(code: String): String = when (code) {
        "he" -> TranslateLanguage.HEBREW
        "hi" -> TranslateLanguage.HINDI
        "zh" -> TranslateLanguage.CHINESE
        "ro" -> TranslateLanguage.ROMANIAN
        "ur" -> TranslateLanguage.URDU
        "ar" -> TranslateLanguage.ARABIC
        "th" -> TranslateLanguage.THAI
        "tl" -> TranslateLanguage.TAGALOG
        "en" -> TranslateLanguage.ENGLISH
        // Falls back to whatever ML Kit itself recognizes for the tag (it
        // supports far more languages than our fixed worker-language list),
        // and only as a last resort assumes English - this now also
        // handles a *detected* source language, not just a worker-picked
        // one, so unrecognized-but-valid codes should resolve properly
        // instead of being silently coerced to English.
        else -> TranslateLanguage.fromLanguageTag(code) ?: TranslateLanguage.ENGLISH
    }
}
