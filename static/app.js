let progressInterval = null;

function upload() {
    const fileInput = document.getElementById("videoInput");
    const inputVideo = document.getElementById("inputVideo");
    const outputVideo = document.getElementById("outputVideo");
    const bar = document.getElementById("bar");
    const enhanceBtn = document.getElementById("enhanceBtn");

    const file = fileInput.files[0];
    if (!file) return;

    // Reset UI
    bar.style.width = "0%";
    outputVideo.pause();
    outputVideo.removeAttribute("src");
    outputVideo.style.display = "none";
    outputVideo.load();

    // Show input preview
    inputVideo.src = URL.createObjectURL(file);

    // Upload video
    const form = new FormData();
    form.append("video", file);

    fetch("/upload", { method: "POST", body: form })
        .catch(err => {
            console.error("Upload failed", err);
            enhanceBtn.disabled = false;
        });

    // Start polling
    pollProgress();
}

function pollProgress() {
    const bar = document.getElementById("bar");
    const outputVideo = document.getElementById("outputVideo");
    const enhanceBtn = document.getElementById("enhanceBtn");

    if (progressInterval) {
        clearInterval(progressInterval);
    }

    progressInterval = setInterval(() => {
        fetch("/progress")
            .then(res => res.json())
            .then(data => {
                if (!data.total || data.total === 0) return;
                const percent = Math.floor((data.current / data.total) * 100);
                bar.style.width = percent + "%";

                if (percent >= 100) {
                    clearInterval(progressInterval);
                    progressInterval = null;

                    // Load fresh output (cache-busted)
                    outputVideo.src = "/output/enhanced_output.mp4?t=" + Date.now();
                    outputVideo.style.display = "block";
                    outputVideo.load();
                    enhanceBtn.disabled = false;
                }
            })
            .catch(err => {
                console.error("Progress error", err);
                clearInterval(progressInterval);
                enhanceBtn.disabled = false;
            });
    }, 1000);
}

