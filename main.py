import os
import random
import uuid
import subprocess
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow Netlify frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-netlify-site.netlify.app"],  # change to your Netlify domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/process-video")
async def process_video(
    file: UploadFile = File(...),
    mesh_overlay: bool = Form(False),
    remove_metadata: bool = Form(False),
    reduce_fps: bool = Form(False),
    crop_start: bool = Form(False),
    speed_audio: bool = Form(False),
    apply_color: bool = Form(False)
):
    input_filename = f"input_{uuid.uuid4()}.mp4"
    output_filename = f"output_{uuid.uuid4()}.mp4"

    with open(input_filename, "wb") as f:
        f.write(await file.read())

    filters = []
    start_crop = []
    duration_crop = []
    fps_cmd = []
    atempo_value = None

    try:
        # Get total video duration
        duration_output = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", input_filename
        ])
        total_duration = float(duration_output.decode().strip())

        # Speed audio (and video) by 5–10%
        if speed_audio:
            atempo_value = round(random.uniform(1.05, 1.10), 2)
            filters.append(f"setpts={round(1/atempo_value, 3)}*PTS")

        # Crop start/end/both by same percent (if crop enabled)
        if crop_start:
            if atempo_value:
                crop_percent = 1 - (1 / atempo_value)
            else:
                crop_percent = random.uniform(0.1, 0.3)

            crop_seconds = total_duration * crop_percent
            crop_type = random.choice(["start", "end", "both"])

            if crop_type == "start":
                start_crop = ["-ss", str(round(crop_seconds, 2))]
                duration_crop = ["-t", str(round(total_duration - crop_seconds, 2))]
            elif crop_type == "end":
                start_crop = ["-ss", "0"]
                duration_crop = ["-t", str(round(total_duration - crop_seconds, 2))]
            else:
                cut_each_side = crop_seconds / 2
                start_crop = ["-ss", str(round(cut_each_side, 2))]
                duration_crop = ["-t", str(round(total_duration - crop_seconds, 2))]

    except Exception as e:
        print("Failed to get duration:", e)

    # Color correction
    if apply_color:
        gamma = round(random.uniform(0.95, 1.05), 2)
        saturation = round(random.uniform(0.95, 1.1), 2)
        contrast = round(random.uniform(0.95, 1.1), 2)
        filters.append(f"eq=gamma={gamma}:saturation={saturation}:contrast={contrast}")

    # Transparent mesh overlay
    overlay_cmd = []
    if mesh_overlay:
        mesh_file = random.choice([f"overlays/mesh{i}.png" for i in range(1, 6)])
        overlay_cmd = ["-i", mesh_file, "-filter_complex", "[0:v][1:v] overlay=0:0"]

    # Reduce FPS by 10–15%
    if reduce_fps:
        try:
            fps_output = subprocess.check_output([
                "ffprobe", "-v", "0", "-of", "csv=p=0",
                "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                input_filename
            ])
            num, denom = map(int, fps_output.decode().strip().split("/"))
            original_fps = num / denom
            new_fps = max(1, round(original_fps * random.uniform(0.85, 0.9)))
            fps_cmd = ["-r", str(new_fps)]
        except Exception as e:
            print("Failed to get original FPS:", e)

    vf_filters = ",".join(filters) if filters else None

    # Build ffmpeg command
    cmd = ["ffmpeg", "-y"] + start_crop + ["-i", input_filename]
    if overlay_cmd:
        cmd += overlay_cmd
    elif vf_filters:
        cmd += ["-vf", vf_filters]

    if speed_audio and atempo_value:
        cmd += ["-filter:a", f"atempo={atempo_value}"]

    if remove_metadata:
        cmd += ["-map_metadata", "-1"]

    cmd += duration_crop + fps_cmd + ["-c:a", "copy", output_filename]

    subprocess.run(cmd)
    os.remove(input_filename)

    return FileResponse(output_filename, media_type="video/mp4", filename="edited_video.mp4")
