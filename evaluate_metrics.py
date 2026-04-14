import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from skimage.metrics import peak_signal_noise_ratio

# ---------------- PATHS ----------------
HR_DIR = "eval/hr"
SR_DIR = "eval/sr"                 # Your model output
EXISTING_SR_DIR = "eval/existing_sr"  # Existing model output
OUTPUT_DIR = "eval/results"

os.makedirs(OUTPUT_DIR, exist_ok=True)

psnr_ours = []
psnr_existing = []

frames = sorted(os.listdir(HR_DIR))
print(f"[INFO] Total HR frames found: {len(frames)}")

# ---------------- COMPUTE METRICS ----------------
for f in frames:

    hr_path = os.path.join(HR_DIR, f)
    sr_path = os.path.join(SR_DIR, f)
    ex_path = os.path.join(EXISTING_SR_DIR, f)

    if not os.path.exists(sr_path) or not os.path.exists(ex_path):
        continue

    hr = cv2.imread(hr_path)
    sr = cv2.imread(sr_path)
    ex = cv2.imread(ex_path)

    if hr is None or sr is None or ex is None:
        continue

    # Resize outputs to HR resolution
    h, w = hr.shape[:2]
    sr = cv2.resize(sr, (w, h), interpolation=cv2.INTER_CUBIC)
    ex = cv2.resize(ex, (w, h), interpolation=cv2.INTER_CUBIC)

    # Convert to grayscale for metrics
    hr_gray = cv2.cvtColor(hr, cv2.COLOR_BGR2GRAY)
    sr_gray = cv2.cvtColor(sr, cv2.COLOR_BGR2GRAY)
    ex_gray = cv2.cvtColor(ex, cv2.COLOR_BGR2GRAY)

    # Compute PSNR
    psnr_sr = peak_signal_noise_ratio(hr_gray, sr_gray, data_range=255)
    psnr_ex = peak_signal_noise_ratio(hr_gray, ex_gray, data_range=255)

    psnr_ours.append(psnr_sr)
    psnr_existing.append(psnr_ex)

# ---------------- RESULTS ----------------
print("\n========== PSNR RESULTS ==========\n")
print(f"Frames evaluated : {len(psnr_ours)}")

if len(psnr_ours) > 0:
    print(f"Average PSNR (Our Model)     : {np.mean(psnr_ours):.2f} dB")
    print(f"Average PSNR (Existing Model): {np.mean(psnr_existing):.2f} dB")
else:
    print("No frames evaluated. Check filename matching.")

print("\n==================================\n")

# ---------------- RESEARCH STYLE GRAPH ----------------
frames_idx = np.arange(len(psnr_ours))

plt.figure(figsize=(9,4.5))

plt.plot(
    frames_idx,
    psnr_ours,
    linewidth=2.5,
    color="tab:blue",
    label="Proposed Super-Resolution Pipeline"
)

plt.plot(
    frames_idx,
    psnr_existing,
    linewidth=2.5,
    linestyle="--",
    color="tab:orange",
    label="Existing AI Enhancement"
)

plt.xlabel("Frame Index", fontsize=12)
plt.ylabel("PSNR (dB)", fontsize=12)

plt.xticks(fontsize=10)
plt.yticks(fontsize=10)

# Better PSNR scaling
if len(psnr_ours) > 0:
    plt.ylim(min(psnr_existing) - 1, max(psnr_ours) + 1)

# Soft research grid
plt.grid(True, linestyle="--", alpha=0.35)

# Clean axis style
ax = plt.gca()
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Legend position
plt.legend(loc="lower right", frameon=False, fontsize=11)

plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "psnr_comparison_research.png"),
    dpi=400
)

plt.close()

print("[DONE] Research-style PSNR comparison graph saved in eval/results/")
