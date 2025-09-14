from fastapi import FastAPI, UploadFile
from fastapi.responses import StreamingResponse
import openai, io

app = FastAPI()

@app.post("/process_audio/")
async def process_audio(file: UploadFile):
    audio_bytes = await file.read()

    # 1. Transcripción con Whisper
    transcript = openai.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=("audio.wav", io.BytesIO(audio_bytes), "audio/wav")
    )
    text = transcript.text

    # 2. Respuesta de ChatGPT
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":"Eres un asistente tipo Jarvis."},
                  {"role":"user","content": text}]
    )
    reply = response.choices[0].message.content

    # 3. TTS con OpenAI
    speech = openai.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=reply
    )

    # 4. Regresar audio WAV
    return StreamingResponse(io.BytesIO(speech.read()), media_type="audio/wav")
