package com.babylon.site.data

import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*

data class Worker(
    val id: String,
    val name: String,
    val language: String,
    val channel: String,
    val photo_url: String?,
    val phone: String? = null,
)

data class TaskDto(
    val id: String,
    val title: String,
    val description: String,
    val worker_id: String,
    val status: String,
    val before_photo_urls: List<String>,
    val after_photo_urls: List<String>,
    val claude_review: String?,
    val photo_requirement: String? = null,
    val created_at: String?,
)

data class RegisterResponse(val id: String, val name: String)

// Response of POST /tasks/{task_id}/photo - a lightweight status object,
// NOT a full TaskDto (it doesn't include title/description/worker_id/etc).
data class PhotoReviewDto(
    val id: String,
    val url: String,
    val stage: String,
    val verdict: String?,      // "match" | "no_match" | "unclear" | null (no photo_requirement set)
    val explanation: String?,
)

data class PhotoUploadResponse(
    val id: String,
    val status: String,
    val claude_review: String?,
    val photo_reviews: List<PhotoReviewDto> = emptyList(),
)

data class ApkUpdateInfo(
    val version_code: Int,
    val version_name: String,
    val notes: String?,
    val uploaded_at: String?,
    val url: String,
)

interface SiteCommsApi {

    @Multipart
    @POST("workers/register")
    suspend fun registerWorker(
        @Part("name") name: RequestBody,
        @Part("language") language: RequestBody,
        @Part("device_token") deviceToken: RequestBody?,
        @Part photo: MultipartBody.Part?,
    ): Response<RegisterResponse>

    @GET("tasks")
    suspend fun listTasks(): Response<List<TaskDto>>

    @FormUrlEncoded
    @POST("workers/{worker_id}/device_token")
    suspend fun updateDeviceToken(
        @Path("worker_id") workerId: String,
        @Field("device_token") deviceToken: String,
    ): Response<Unit>

    @FormUrlEncoded
    @POST("tasks/{task_id}/reply")
    suspend fun sendReply(
        @Path("task_id") taskId: String,
        @Field("original_text") originalText: String,
        @Field("original_lang") originalLang: String,
        @Field("translated_text") translatedText: String,
        @Field("translated_lang") translatedLang: String,
    ): Response<Unit>

    @Multipart
    @POST("tasks/{task_id}/photo")
    suspend fun uploadTaskPhoto(
        @Path("task_id") taskId: String,
        @Part("stage") stage: RequestBody,
        @Part photos: List<MultipartBody.Part>,
    ): Response<PhotoUploadResponse>

    // Polled periodically to see if a newer APK build has been published.
    // Returns 404 until the server has had at least one build uploaded to it.
    @GET("apk/latest.json")
    suspend fun checkApkUpdate(): Response<ApkUpdateInfo>

    companion object {
        fun create(): SiteCommsApi {
            return Retrofit.Builder()
                .baseUrl(ApiConfig.BASE_URL)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(SiteCommsApi::class.java)
        }
    }
}
