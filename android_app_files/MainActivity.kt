package com.videoenhancer.app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.Settings
import android.widget.Button
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.view.isVisible
import androidx.lifecycle.lifecycleScope
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import com.videoenhancer.app.network.RetrofitClient
import com.videoenhancer.app.viewmodel.VideoViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream

class MainActivity : AppCompatActivity() {

    private val viewModel: VideoViewModel by viewModels()
    
    private lateinit var selectVideoButton: Button
    private lateinit var uploadButton: Button
    private lateinit var downloadButton: Button
    private lateinit var progressBar: ProgressBar
    private lateinit var statusText: TextView
    private lateinit var progressText: TextView
    private lateinit var originalPlaceholder: TextView
    private lateinit var enhancedPlaceholder: TextView
    
    private lateinit var originalVideoPlayer: PlayerView
    private lateinit var enhancedVideoPlayer: PlayerView
    
    private var originalPlayer: ExoPlayer? = null
    private var enhancedPlayer: ExoPlayer? = null
    
    private var selectedVideoUri: Uri? = null
    private var selectedVideoFile: File? = null

    private val videoPickerLauncher = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let {
            selectedVideoUri = it
            originalPlaceholder.text = "Loading video..."
            uploadButton.isEnabled = true
            
            // Show original video in player
            setupOriginalVideoPlayer(uri)
            
            // Copy to cache file for upload
            lifecycleScope.launch {
                selectedVideoFile = copyUriToFile(uri)
                originalPlaceholder.isVisible = false
                originalVideoPlayer.isVisible = true
            }
        }
    }

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.values.all { it }
        if (!allGranted) {
            Toast.makeText(this, "Permissions required", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        initViews()
        initPlayers()
        requestPermissions()
        setupObservers()
        setupListeners()
    }

    private fun initViews() {
        selectVideoButton = findViewById(R.id.selectVideoButton)
        uploadButton = findViewById(R.id.uploadButton)
        downloadButton = findViewById(R.id.downloadButton)
        progressBar = findViewById(R.id.progressBar)
        statusText = findViewById(R.id.statusText)
        progressText = findViewById(R.id.progressText)
        originalPlaceholder = findViewById(R.id.originalPlaceholder)
        enhancedPlaceholder = findViewById(R.id.enhancedPlaceholder)
        originalVideoPlayer = findViewById(R.id.originalVideoPlayer)
        enhancedVideoPlayer = findViewById(R.id.enhancedVideoPlayer)
    }

    private fun initPlayers() {
        // Initialize ExoPlayer instances
        originalPlayer = ExoPlayer.Builder(this).build()
        enhancedPlayer = ExoPlayer.Builder(this).build()
        
        originalVideoPlayer.player = originalPlayer
        enhancedVideoPlayer.player = enhancedPlayer
        
        // Set to loop videos
        originalPlayer?.repeatMode = Player.REPEAT_MODE_ALL
        enhancedPlayer?.repeatMode = Player.REPEAT_MODE_ALL
    }

    private fun setupOriginalVideoPlayer(uri: Uri) {
        originalPlayer?.apply {
            setMediaItem(MediaItem.fromUri(uri))
            prepare()
            playWhenReady = false
        }
    }

    private fun setupEnhancedVideoPlayer(url: String) {
        enhancedPlayer?.apply {
            setMediaItem(MediaItem.fromUri(url))
            prepare()
            playWhenReady = false
        }
        
        enhancedPlaceholder.isVisible = false
        enhancedVideoPlayer.isVisible = true
    }

    private fun requestPermissions() {
        val permissions = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            arrayOf(Manifest.permission.READ_MEDIA_VIDEO)
        } else {
            arrayOf(Manifest.permission.READ_EXTERNAL_STORAGE)
        }
        
        val needsPermission = permissions.any {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        
        if (needsPermission) {
            permissionLauncher.launch(permissions)
        }
        
        // For Android 11+ storage access
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            if (!Environment.isExternalStorageManager()) {
                val intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                intent.data = Uri.parse("package:$packageName")
                startActivity(intent)
            }
        }
    }

    private fun setupListeners() {
        selectVideoButton.setOnClickListener {
            videoPickerLauncher.launch("video/*")
        }

        uploadButton.setOnClickListener {
            selectedVideoFile?.let { file ->
                // Reset enhanced video display
                enhancedPlayer?.stop()
                enhancedPlayer?.clearMediaItems()
                enhancedVideoPlayer.isVisible = false
                enhancedPlaceholder.isVisible = true
                enhancedPlaceholder.text = "Processing..."
                
                viewModel.uploadVideo(file)
            } ?: run {
                Toast.makeText(this, "Please select a video first", Toast.LENGTH_SHORT).show()
            }
        }

        downloadButton.setOnClickListener {
            viewModel.outputVideoPath.value?.let { filename ->
                downloadEnhancedVideo(filename)
            }
        }
    }

    private fun setupObservers() {
        viewModel.uploadStatus.observe(this) { status ->
            statusText.text = status
        }

        viewModel.progress.observe(this) { (current, total) ->
            if (total > 1) {
                progressBar.max = total
                progressBar.progress = current
                progressText.text = "Processing: $current / $total frames"
            }
        }

        viewModel.isProcessing.observe(this) { isProcessing ->
            progressBar.isVisible = isProcessing
            selectVideoButton.isEnabled = !isProcessing
            uploadButton.isEnabled = !isProcessing && selectedVideoFile != null
        }

        viewModel.outputVideoPath.observe(this) { filename ->
            if (filename != null) {
                downloadButton.isVisible = true
                
                // Show enhanced video in player
                val enhancedUrl = "${RetrofitClient.BASE_URL}output/$filename"
                setupEnhancedVideoPlayer(enhancedUrl)
                enhancedPlaceholder.text = "Enhancement complete!"
            }
        }
        
        viewModel.inputVideoUrl.observe(this) { url ->
            // Input video URL observer (if needed for additional features)
        }
    }

    private suspend fun copyUriToFile(uri: Uri): File = withContext(Dispatchers.IO) {
        val inputStream = contentResolver.openInputStream(uri)
        val file = File(cacheDir, "input_video_${System.currentTimeMillis()}.mp4")
        
        inputStream?.use { input ->
            FileOutputStream(file).use { output ->
                input.copyTo(output)
            }
        }
        
        file
    }

    private fun downloadEnhancedVideo(filename: String) {
        lifecycleScope.launch {
            try {
                statusText.text = "Downloading enhanced video..."
                downloadButton.isEnabled = false
                
                val response = withContext(Dispatchers.IO) {
                    RetrofitClient.api.downloadVideo(filename)
                }
                
                if (response.isSuccessful) {
                    val body = response.body()
                    body?.let {
                        val downloadsDir = Environment.getExternalStoragePublicDirectory(
                            Environment.DIRECTORY_DOWNLOADS
                        )
                        val outputFile = File(downloadsDir, "enhanced_${System.currentTimeMillis()}.mp4")
                        
                        withContext(Dispatchers.IO) {
                            FileOutputStream(outputFile).use { output ->
                                it.byteStream().copyTo(output)
                            }
                        }
                        
                        statusText.text = "Video saved to Downloads!"
                        Toast.makeText(
                            this@MainActivity,
                            "Saved: ${outputFile.name}",
                            Toast.LENGTH_LONG
                        ).show()
                        
                        downloadButton.isEnabled = true
                    }
                } else {
                    statusText.text = "Download failed: ${response.code()}"
                    downloadButton.isEnabled = true
                    Toast.makeText(
                        this@MainActivity,
                        "Download failed. Please try again.",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            } catch (e: Exception) {
                statusText.text = "Download error: ${e.message}"
                downloadButton.isEnabled = true
                Toast.makeText(
                    this@MainActivity,
                    "Error: ${e.message}",
                    Toast.LENGTH_SHORT
                ).show()
            }
        }
    }

    override fun onStop() {
        super.onStop()
        originalPlayer?.pause()
        enhancedPlayer?.pause()
    }

    override fun onDestroy() {
        super.onDestroy()
        originalPlayer?.release()
        enhancedPlayer?.release()
        originalPlayer = null
        enhancedPlayer = null
    }
}
