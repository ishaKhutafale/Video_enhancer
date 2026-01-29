let progressInterval = null;

function upload() {
    const fileInput = document.getElementById("videoInput");
    const inputVideo = document.getElementById("inputVideo");
    const outputVideo = document.getElementById("outputVideo");
    const bar = document.getElementById("bar");
    const enhanceBtn = document.getElementById("enhanceBtn");

    const file = fileInput.files[0];
    if (!file) {
        alert("Please select a video first!");
        return;
    }

    // Disable button during processing
    enhanceBtn.disabled = true;

    // ---------------- RESET UI ----------------
    bar.style.width = "0%";

    // Reset enhanced video
    outputVideo.pause();
    outputVideo.removeAttribute("src");
    outputVideo.style.display = "none";
    outputVideo.controls = true;
    outputVideo.load();

    // Show input preview immediately
    inputVideo.src = URL.createObjectURL(file);
    inputVideo.load();

    // ---------------- UPLOAD VIDEO ----------------
    const form = new FormData();
    form.append("video", file);

    fetch("/upload", {
        method: "POST",
        body: form
    })
        .then(res => res.json())
        .then(data => {
            console.log("Upload started:", data);
            pollProgress(); // Start polling progress
        })
        .catch(err => {
            console.error("Upload failed", err);
            enhanceBtn.disabled = false;
        });
}


// ---------------- PROGRESS POLLING ----------------

function pollProgress() {
    const bar = document.getElementById("bar");
    const enhanceBtn = document.getElementById("enhanceBtn");

    // Clear old interval if running
    if (progressInterval) {
        clearInterval(progressInterval);
    }

    progressInterval = setInterval(() => {

        fetch("/progress")
            .then(res => res.json())
            .then(data => {

                if (!data.total || data.total === 0) return;

                const percent = Math.floor((data.current / data.total) * 100);

                // Update progress bar
                bar.style.width = percent + "%";

                console.log("Progress:", percent + "%");

                // If completed
                if (data.status === "completed") {
                    clearInterval(progressInterval);
                    progressInterval = null;

                    console.log("Enhancement completed!");

                    // Wait until output file is fully ready
                    waitForOutputReady();

                    enhanceBtn.disabled = false;
                }

                // If error
                if (data.status === "error") {
                    clearInterval(progressInterval);
                    progressInterval = null;

                    alert("Enhancement Error: " + data.message);
                    enhanceBtn.disabled = false;
                }
            })

            .catch(err => {
                console.error("Progress polling error", err);
                clearInterval(progressInterval);
                enhanceBtn.disabled = false;
            });

    }, 1000);
}


// ---------------- WAIT UNTIL OUTPUT IS READY ----------------

function waitForOutputReady() {
    const outputVideo = document.getElementById("outputVideo");

    console.log("Checking output file...");

    let checkInterval = setInterval(() => {

        fetch("/check_output")
            .then(res => res.json())
            .then(data => {

                if (data.ready) {
                    clearInterval(checkInterval);

                    console.log("Output is ready!");

                    // ✅ Force reload enhanced video (cache-busted)
                    outputVideo.src =
                        "/output/enhanced_output.mp4?t=" + new Date().getTime();

                    outputVideo.load();

                    // ✅ Show enhanced video panel
                    outputVideo.style.display = "block";

                    console.log("Enhanced video loaded successfully!");
                }
            })

            .catch(err => {
                console.error("Output check error:", err);
            });

    }, 1000);
}

