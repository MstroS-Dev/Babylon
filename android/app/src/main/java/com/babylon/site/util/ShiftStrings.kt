package com.babylon.site.util

/**
 * A handful of fixed UI-chrome strings (connection status, check-in/out
 * button labels) translated per supported language. These are static app
 * chrome, not dynamic task content, so a small hardcoded table is simpler
 * and more reliable than routing them through the on-device ML Kit
 * translator (which needs a model download and is meant for arbitrary
 * task text, not fixed button labels).
 */
data class ShiftStrings(
    val connected: String,
    val offline: String,
    val checkIn: String,
    val checkOut: String,
    val checkedIn: String,
    val checkedOut: String,
    val noTasksYet: String,
)

private val SHIFT_STRINGS = mapOf(
    "en" to ShiftStrings("Connected", "Offline", "Check In", "Check Out", "You're checked in", "You're checked out", "No tasks yet"),
    "he" to ShiftStrings("מחובר", "לא מחובר", "כניסה למשמרת", "יציאה ממשמרת", "נכנסת למשמרת", "יצאת מהמשמרת", "אין משימות כרגע"),
    "hi" to ShiftStrings("जुड़ा हुआ", "ऑफ़लाइन", "चेक इन", "चेक आउट", "आप चेक इन हैं", "आप चेक आउट हैं", "अभी कोई काम नहीं है"),
    "zh" to ShiftStrings("已连接", "离线", "签到", "签退", "您已签到", "您已签退", "暂无任务"),
    "ro" to ShiftStrings("Conectat", "Deconectat", "Pontaj sosire", "Pontaj plecare", "Ai pontat sosirea", "Ai pontat plecarea", "Nicio sarcină momentan"),
    "ur" to ShiftStrings("منسلک", "آف لائن", "چیک ان", "چیک آؤٹ", "آپ چیک ان ہیں", "آپ چیک آؤٹ ہیں", "ابھی کوئی کام نہیں"),
    "ar" to ShiftStrings("متصل", "غير متصل", "تسجيل الدخول", "تسجيل الخروج", "تم تسجيل دخولك", "تم تسجيل خروجك", "لا توجد مهام حاليًا"),
    "th" to ShiftStrings("เชื่อมต่อแล้ว", "ออฟไลน์", "เข้างาน", "ออกงาน", "คุณเข้างานแล้ว", "คุณออกงานแล้ว", "ยังไม่มีงานตอนนี้"),
    "tl" to ShiftStrings("Konektado", "Offline", "Mag-check in", "Mag-check out", "Naka-check in ka na", "Naka-check out ka na", "Wala pang gawain"),
)

fun shiftStrings(languageCode: String): ShiftStrings = SHIFT_STRINGS[languageCode] ?: SHIFT_STRINGS.getValue("en")
