from fastapi import FastAPI, File, UploadFile
import openai
import io

app = FastAPI()

@app.post("/process_audio/")
async def process_audio(file: UploadFile = File(...)):
    try:
        audio_bytes = await file.read()

        # Mandar el audio a OpenAI (Whisper para transcripción + GPT respuesta)
        transcript = openai.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=io.BytesIO(audio_bytes)
        )

        respuesta = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": transcript.text}]
        )

        return {"texto": transcript.text, "respuesta": respuesta.choices[0].message["content"]}

    except Exception as e:
        return {"error": str(e)}
