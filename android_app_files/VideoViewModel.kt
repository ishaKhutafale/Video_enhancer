package com.videoenhancer.app.viewmodel

import android.net.Uri
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.videoenhancer.app.network.RetrofitClient
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File

class VideoViewModel : ViewModel() {
    
    private val _uploadStatus = MutableLiveData<String>()
    val uploadStatus: LiveData<String> = _uploadStatus
    
    private val _progress = MutableLiveData<Pair<Int, Int>>()
    val progress: LiveData<Pair<Int, Int>> = _progress
    
    private val _isProcessing = MutableLiveData<Boolean>(false)
    val isProcessing: LiveData<Boolean> = _isProcessing
    
    private val _outputVideoPath = MutableLiveData<String?>()
    val outputVideoPath: LiveData<String?> = _outputVideoPath
    
    private val _inputVideoUrl = MutableLiveData<String?>()
    val inputVideoUrl: LiveData<String?> = _inputVideoUrl
    
    private val _processingStatus = MutableLiveData<String>()
    val processingStatus: LiveData<String> = _processingStatus
    
    fun uploadVideo(videoFile: File) {
        viewModelScope.launch {
            try {
                _isProcessing.value = true
                _uploadStatus.value = "Uploading video..."
                _outputVideoPath.value = null
                
                val requestBody = videoFile.asRequestBody("video/mp4".toMediaTypeOrNull())
                val videoPart = MultipartBody.Part.createFormData("video", videoFile.name, requestBody)
                
                val response = RetrofitClient.api.uploadVideo(videoPart)
                
                if (response.isSuccessful) {
                    val uploadResponse = response.body()
                    _uploadStatus.value = "Video uploaded. Processing..."
                    
                    // Set input video URL for preview
                    uploadResponse?.input_video?.let {
                        _inputVideoUrl.value = "${RetrofitClient.BASE_URL}input/$it"
                    }
                    
                    startProgressPolling()
                } else {
                    _uploadStatus.value = "Upload failed: ${response.code()}"
                    _isProcessing.value = false
                }
            } catch (e: Exception) {
                _uploadStatus.value = "Error: ${e.message}"
                _isProcessing.value = false
            }
        }
    }
    
    private fun startProgressPolling() {
        viewModelScope.launch {
            while (_isProcessing.value == true) {
                try {
                    val response = RetrofitClient.api.getProgress()
                    if (response.isSuccessful) {
                        val progressData = response.body()
                        if (progressData != null) {
                            _progress.value = Pair(progressData.current, progressData.total)
                            _processingStatus.value = progressData.status
                            _uploadStatus.value = progressData.message
                            
                            // Check if processing is completed
                            if (progressData.status == "completed") {
                                // Verify output file exists
                                checkOutputVideo()
                                break
                            } else if (progressData.status == "error") {
                                _uploadStatus.value = "Error: ${progressData.message}"
                                _isProcessing.value = false
                                break
                            }
                        }
                    }
                } catch (e: Exception) {
                    // Continue polling even on error
                }
                delay(1000) // Poll every second
            }
        }
    }
    
    private suspend fun checkOutputVideo() {
        try {
            val response = RetrofitClient.api.checkOutput()
            if (response.isSuccessful) {
                val checkData = response.body()
                if (checkData?.ready == true && checkData.filename != null) {
                    _outputVideoPath.value = checkData.filename
                    _uploadStatus.value = "Processing complete! Ready to download."
                    _isProcessing.value = false
                } else {
                    // Wait a bit more and check again
                    delay(2000)
                    checkOutputVideo()
                }
            }
        } catch (e: Exception) {
            _uploadStatus.value = "Error checking output: ${e.message}"
            _isProcessing.value = false
        }
    }
    
    fun resetState() {
        _uploadStatus.value = ""
        _progress.value = Pair(0, 1)
        _isProcessing.value = false
        _outputVideoPath.value = null
        _inputVideoUrl.value = null
        _processingStatus.value = ""
    }
}
