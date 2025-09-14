from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

# Permitir conexiones desde cualquier origen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# URL del modelo de Hugging Face
HF_API_URL = "https://api-inference.huggingface.co/models/openai/whisper-small"
HF_TOKEN = "TU_HUGGINGFACE_TOKEN_AQUI"

headers = {"Authorization": f"Bearer {HF_TOKEN}"}

@app.post("/process_audio/")
async def process_audio(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    response = requests.post(HF_API_URL, headers=headers, data=audio_bytes)
    try:
        return response.json()
    except:
        return {"error": "Error al procesar el audio", "status_code": response.status_code}
