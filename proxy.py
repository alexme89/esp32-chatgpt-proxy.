# app.py para Render
from flask import Flask, request, jsonify, send_file
import os
import tempfile
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import torch
import torchaudio
import librosa
import numpy as np
from gtts import gTTS
import requests

app = Flask(__name__)

# Configuración
HUGGING_FACE_TOKEN = os.environ.get('HUGGING_FACE_TOKEN')  # Tu token desde variables de entorno
MODEL_NAME = "openai/whisper-base"  # ✅ Modelo correcto que existe

# Cargar modelo al inicio (mejor rendimiento)
print(f"Cargando modelo {MODEL_NAME}...")
try:
    processor = WhisperProcessor.from_pretrained(MODEL_NAME, use_auth_token=HUGGING_FACE_TOKEN)
    model = WhisperForConditionalGeneration.from_pretrained(MODEL_NAME, use_auth_token=HUGGING_FACE_TOKEN)
    print("✅ Modelo cargado exitosamente")
except Exception as e:
    print(f"❌ Error cargando modelo: {e}")
    processor = None
    model = None

@app.route('/')
def home():
    return {"status": "ESP32 ChatGPT Proxy funcionando", "model": MODEL_NAME}

@app.route('/process_audio/', methods=['POST'])
def process_audio():
    try:
        # Verificar autenticación
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Token de autorización requerido"}), 401
        
        # Verificar que se recibió un archivo
        if 'file' not in request.files:
            return jsonify({"error": "No se encontró archivo de audio"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "Nombre de archivo vacío"}), 400
        
        print(f"📁 Procesando archivo: {file.filename}")
        print(f"📊 Tamaño: {len(file.read())} bytes")
        file.seek(0)  # Resetear puntero después de leer
        
        # Verificar que el modelo esté cargado
        if processor is None or model is None:
            return jsonify({"error": "Modelo no disponible"}), 503
        
        # Guardar archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Procesar audio con Whisper
            print("🎤 Transcribiendo audio...")
            audio, sample_rate = librosa.load(temp_path, sr=16000)
            
            # Convertir a formato que espera Whisper
            inputs = processor(audio, sampling_rate=16000, return_tensors="pt")
            
            # Generar transcripción
            with torch.no_grad():
                predicted_ids = model.generate(inputs["input_features"])
            
            # Decodificar transcripción
            transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
            print(f"📝 Transcripción: {transcription}")
            
            if not transcription.strip():
                return jsonify({"error": "No se pudo transcribir el audio"}), 400
            
            # Generar respuesta con ChatGPT (simulada por ahora)
            response_text = generate_chatgpt_response(transcription)
            print(f"🤖 Respuesta: {response_text}")
            
            # Convertir respuesta a audio
            print("🔊 Generando audio de respuesta...")
            audio_response_path = text_to_speech(response_text)
            
            # Enviar archivo de audio como respuesta
            return send_file(
                audio_response_path,
                as_attachment=True,
                download_name="response.wav",
                mimetype="audio/wav"
            )
            
        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    except Exception as e:
        print(f"❌ Error procesando audio: {e}")
        return jsonify({"error": "Error al procesar el audio", "details": str(e)}), 500

def generate_chatgpt_response(text):
    """
    Genera respuesta usando OpenAI ChatGPT
    Por ahora simulada - puedes agregar llamada real a OpenAI API
    """
    try:
        # Simulación - reemplazar con llamada real a OpenAI
        responses = [
            f"Entendí que dijiste: {text}. ¿En qué puedo ayudarte?",
            f"Gracias por tu mensaje: {text}. ¿Tienes alguna pregunta?",
            f"Escuché: {text}. ¿Necesitas más información sobre algo específico?"
        ]
        
        import random
        return random.choice(responses)
        
        # TODO: Reemplazar con código real de OpenAI:
        # openai.api_key = os.environ.get('OPENAI_API_KEY')
        # response = openai.ChatCompletion.create(...)
        
    except Exception as e:
        print(f"Error generando respuesta: {e}")
        return "Lo siento, no pude procesar tu solicitud en este momento."

def text_to_speech(text):
    """Convierte texto a audio usando gTTS"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            # Usar gTTS para generar audio
            tts = gTTS(text=text, lang='es', slow=False)
            
            # Guardar como MP3 temporal
            mp3_path = temp_file.name.replace('.wav', '.mp3')
            tts.save(mp3_path)
            
            # Convertir MP3 a WAV usando librosa
            audio, sr = librosa.load(mp3_path, sr=8000)  # 8kHz para ESP32
            
            # Guardar como WAV
            import soundfile as sf
            sf.write(temp_file.name, audio, sr)
            
            # Limpiar MP3 temporal
            if os.path.exists(mp3_path):
                os.unlink(mp3_path)
                
            return temp_file.name
            
    except Exception as e:
        print(f"Error en text_to_speech: {e}")
        # Crear archivo de silencio como fallback
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            silence = np.zeros(8000)  # 1 segundo de silencio a 8kHz
            import soundfile as sf
            sf.write(temp_file.name, silence, 8000)
            return temp_file.name

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
