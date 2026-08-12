package com.babylon.site.util

import com.google.mlkit.nl.translate.TranslateLanguage
import com.google.mlkit.nl.translate.Translation
import com.google.mlkit.nl.translate.Translator
import com.google.mlkit.nl.translate.TranslatorOptions
import com.google.mlkit.common.model.DownloadConditions

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

    fun translate(text: String, onResult: (String) -> Unit, onError: (Exception) -> Unit) {
        translator.translate(text)
            .addOnSuccessListener { onResult(it) }
            .addOnFailureListener { onError(it) }
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
        else -> TranslateLanguage.ENGLISH
    }
}
