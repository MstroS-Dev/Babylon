package com.babylon.site.util

import android.content.Context
import android.content.Intent
import android.speech.RecognizerIntent
import android.speech.tts.TextToSpeech
import java.util.Locale

/**
 * Our SUPPORTED_LANGUAGES list stores bare ISO 639-1 codes ("he", "zh", "hi"...).
 * Android's speech recognizer and TTS engine need a full BCP-47 locale tag
 * (region included) to reliably resolve the right language pack - a bare
 * code is not guaranteed to map to anything, and both APIs fail silently
 * by falling back to the device's own default locale rather than erroring,
 * which can make a worker's own language come out transcribed/spoken in
 * a completely different one with no visible failure at all.
 */
private val LOCALE_TAGS = mapOf(
    "en" to "en-US",
    "he" to "he-IL",
    "hi" to "hi-IN",
    "zh" to "zh-CN",
    "ro" to "ro-RO",
    "ur" to "ur-PK",
    "ar" to "ar-SA",
    "th" to "th-TH",
    "tl" to "fil-PH", // Android's speech/TTS locale for Tagalog/Filipino is "fil", not "tl"
)

fun resolveLocaleTag(languageCode: String): String = LOCALE_TAGS[languageCode] ?: languageCode

/** Reads a translated task out loud in the worker's language. */
class TaskSpeaker(context: Context, private val languageCode: String) {
    private var tts: TextToSpeech? = null

    init {
        tts = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.language = Locale.forLanguageTag(resolveLocaleTag(languageCode))
            }
        }
    }

    fun speak(text: String) {
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, null)
    }

    fun shutdown() {
        tts?.stop()
        tts?.shutdown()
    }
}

/** Builds the intent for Android's built-in speech recognizer, for voice replies. */
fun buildSpeechRecognizerIntent(languageCode: String): Intent {
    val localeTag = resolveLocaleTag(languageCode)
    return Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
        putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
        putExtra(RecognizerIntent.EXTRA_LANGUAGE, localeTag)
        putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, localeTag)
    }
}
