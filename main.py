from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse
import subprocess
import os
import uuid

app = FastAPI()

@app.post("/process-video")
async def process_video(
    file: UploadFile = File(...),
    remove_metadata: bool = Form(False),
    reduce_fps: bool = Form(False),
    crop_start: bool = Form(False),
    speed_audio: bool = Form(False),
):
    input_filename = f"input_{uuid.uuid4()}.mp4"
    output_filename = f"output_{uuid.uuid4()}.mp4"

    with open(input_filename, "wb") as f:
        f.write(await file.read())

    cmd = ["ffmpeg", "-i", input_filename]

    if remove_metadata:
        cmd += ["-map_metadata", "-1"]
    if reduce_fps:
        cmd += ["-r", "15"]
    if crop_start:
        cmd += ["-ss", "5"]
    if speed_audio:
        cmd += ["-filter:a", "atempo=1.1"]

    cmd.append(output_filename)

    subprocess.run(cmd)

    os.remove(input_filename)
    return FileResponse(output_filename, media_type="video/mp4", filename="edited_video.mp4")
