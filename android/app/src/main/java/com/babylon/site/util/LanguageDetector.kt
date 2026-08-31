package com.babylon.site.util

import com.google.mlkit.nl.languageid.LanguageIdentification
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

/**
 * Detects what language a piece of text is actually written in, rather
 * than assuming every task was typed in one fixed language. A manager may
 * type tasks in Hebrew, English, or a mix - translating from the wrong
 * assumed source produces garbled or entirely skipped translations even
 * when the destination language is right.
 */
object LanguageDetector {
    private val identifier = LanguageIdentification.getClient()

    /** Returns an ISO 639-1 code (e.g. "en", "he"), or null if the text is
     * too short/ambiguous for ML Kit to make a confident call. Never
     * throws - a detection failure just means "don't know", which callers
     * should treat as "skip translation, show the original text". */
    suspend fun detect(text: String): String? {
        if (text.isBlank()) return null
        return try {
            suspendCancellableCoroutine { cont ->
                identifier.identifyLanguage(text)
                    .addOnSuccessListener { tag ->
                        cont.resume(if (tag == "und") null else tag)
                    }
                    .addOnFailureListener { cont.resume(null) }
            }
        } catch (e: Exception) {
            null
        }
    }
}
