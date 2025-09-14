import os
import requests
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

app = FastAPI()

# URL del modelo Whisper en Hugging Face
HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/openai/whisper-small"
# La API Key se toma de las variables de entorno
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")

headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

@app.post("/process_audio/")
async def process_audio(file: UploadFile = File(...)):
    try:
        audio_bytes = await file.read()
        response = requests.post(
            HUGGINGFACE_API_URL,
            headers=headers,
            files={"file": ("audio.wav", audio_bytes, "audio/wav")}
        )
        if response.status_code != 200:
            return JSONResponse(
                status_code=response.status_code,
                content={"error": "Error al procesar el audio", "details": response.text}
            )
        return response.json()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Excepción interna del servidor", "details": str(e)}
        )

@app.get("/")
def root():
    return {"message": "El servicio está activo. Usa /process_audio/ para subir audio."}
