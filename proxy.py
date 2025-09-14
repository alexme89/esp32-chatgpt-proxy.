import os
import requests
from fastapi import FastAPI, File, UploadFile

app = FastAPI()

HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/openai/whisper-small"
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")

headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

@app.post("/process_audio/")
async def process_audio(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    response = requests.post(HUGGINGFACE_API_URL, headers=headers, files={"file": audio_bytes})
    if response.status_code != 200:
        return {"error": "Error al procesar el audio", "status_code": response.status_code}
    return response.json()
