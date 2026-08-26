package com.shoots.app.data

import android.content.ContentResolver
import android.net.Uri
import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import kotlinx.serialization.json.Json
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.RequestBody
import okhttp3.logging.HttpLoggingInterceptor
import okio.BufferedSink
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.HTTP
import retrofit2.http.Header
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query
import java.io.FileNotFoundException
import java.util.concurrent.TimeUnit

interface ShootsApi {
    @POST("auth/android/session")
    suspend fun createAndroidSession(@Body body: AndroidSessionRequest): AndroidSessionResponse

    @DELETE("api/devices/current")
    suspend fun revokeCurrentDevice(): Response<Unit>

    @PUT("api/devices/current/notifications")
    suspend fun setNotificationTarget(@Body body: NotificationTargetRequest): Response<Unit>

    @POST("api/capture-sessions")
    suspend fun reserveCaptureSession(@Body body: CaptureSessionReserveRequest): CaptureSessionDto

    @PUT("api/capture-sessions/{id}/manifest")
    suspend fun commitCaptureManifest(
        @Path("id") id: String,
        @Body body: CaptureManifestRequest,
    ): CaptureSessionDto

    @POST("api/capture-sessions/{id}/cancel")
    suspend fun cancelCaptureSession(@Path("id") id: String): CaptureSessionDto

    @GET("api/capture-sessions/{id}")
    suspend fun captureSession(@Path("id") id: String): CaptureSessionDto

    @Multipart
    @POST("api/ingress/shots")
    suspend fun uploadShot(
        @Part file: MultipartBody.Part,
        @Part("source_id") sourceId: RequestBody,
        @Part("capture_session_id") captureSessionId: RequestBody?,
    ): ImportResponse

    @GET("api/mobile/snapshot")
    suspend fun mobileSnapshot(@Header("If-None-Match") etag: String?): Response<MobileSnapshotDto>

    @GET("api/shots")
    suspend fun shots(
        @Query("limit") limit: Int,
        @Query("cursor") cursor: String? = null,
    ): Response<List<ShotViewDto>>

    @GET("api/shots/{id}")
    suspend fun shot(@Path("id") id: String): ShotViewDto

    @PUT("api/shots/{id}/keeper")
    suspend fun setKeeper(@Path("id") id: String, @Body body: KeeperRequest): ShotDto

    @POST("api/drive/authorization-code")
    suspend fun connectDrive(@Body body: DriveAuthorizationRequest): DriveConnectResponse

    @DELETE("api/drive")
    suspend fun disconnectDrive(): Response<Unit>

    @HTTP(method = "DELETE", path = "api/account", hasBody = true)
    suspend fun deleteAccount(@Body body: AndroidSessionRequest): DeletionResponse
}

class ContentUriRequestBody(
    private val resolver: ContentResolver,
    private val uri: Uri,
    private val mimeType: String,
    private val length: Long,
) : RequestBody() {
    override fun contentType() = mimeType.toMediaTypeOrNull()

    override fun contentLength(): Long = length

    override fun writeTo(sink: BufferedSink) {
        val input = resolver.openInputStream(uri) ?: throw FileNotFoundException(uri.toString())
        input.use { source ->
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            while (true) {
                val count = source.read(buffer)
                if (count < 0) break
                sink.write(buffer, 0, count)
            }
        }
    }
}

class ApiFactory(
    serviceOrigin: String,
    sessionStore: SessionStore,
    val json: Json,
    debug: Boolean,
) {
    private val authInterceptor = Interceptor { chain ->
        val token = sessionStore.token()
        val request = if (token.isBlank()) chain.request() else {
            chain.request().newBuilder().header("Authorization", "Bearer $token").build()
        }
        chain.proceed(request)
    }

    val okHttp: OkHttpClient = OkHttpClient.Builder()
        .addInterceptor(authInterceptor)
        .apply {
            if (debug) {
                addInterceptor(
                    HttpLoggingInterceptor().apply {
                        redactHeader("Authorization")
                        level = HttpLoggingInterceptor.Level.BASIC
                    }
                )
            }
        }
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(120, TimeUnit.SECONDS)
        .build()

    val api: ShootsApi = Retrofit.Builder()
        .baseUrl(normalizeOrigin(serviceOrigin))
        .client(okHttp)
        .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
        .build()
        .create(ShootsApi::class.java)

    private fun normalizeOrigin(origin: String): String {
        val usable = origin.takeIf { it.startsWith("https://") || it.startsWith("http://") }
            ?: "https://unconfigured.invalid"
        return usable.trimEnd('/') + "/"
    }
}
