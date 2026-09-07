package com.babylon.site.data

object ApiConfig {
    const val BASE_URL = "https://site-comms.16.170.108.223.sslip.io/"
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
