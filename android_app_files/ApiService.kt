package com.videoenhancer.app.network

import okhttp3.MultipartBody
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.*

interface ApiService {
    @Multipart
    @POST("upload")
    suspend fun uploadVideo(
        @Part video: MultipartBody.Part
    ): Response<UploadResponse>
    
    @GET("progress")
    suspend fun getProgress(): Response<ProgressResponse>
    
    @GET("check_output")
    suspend fun checkOutput(): Response<OutputCheckResponse>
    
    @GET("output/{filename}")
    @Streaming
    suspend fun downloadVideo(
        @Path("filename") filename: String
    ): Response<ResponseBody>
}

data class UploadResponse(
    val status: String,
    val input_video: String?
)

data class ProgressResponse(
    val current: Int,
    val total: Int,
    val status: String,
    val message: String
)

data class OutputCheckResponse(
    val exists: Boolean,
    val ready: Boolean,
    val filename: String?
)
