package com.babylon.site.data

object ApiConfig {
    // Change this to your server's address once it's deployed
    const val BASE_URL = "http://YOUR_SERVER_IP:8000/"
}

data class LanguageOption(val code: String, val label: String)

val SUPPORTED_LANGUAGES = listOf(
    LanguageOption("en", "English"),
    LanguageOption("he", "Hebrew"),
    LanguageOption("hi", "Hindi"),
    LanguageOption("zh", "Chinese"),
    LanguageOption("ro", "Romanian"),
    LanguageOption("ur", "Urdu"),
    LanguageOption("ar", "Arabic"),
    LanguageOption("th", "Thai"),
    LanguageOption("tl", "Tagalog"),
)
