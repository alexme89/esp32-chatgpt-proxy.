# app.py
from flask import Flask, request, jsonify, send_file
import os
import tempfile
import whisper
from gtts import gTTS
import subprocess
import random

app = Flask(__name__)

# Cargar modelo Whisper al inicio
print("🤖 Cargando modelo Whisper...")
try:
    # Usar modelo más pequeño para Render gratuito
    model = whisper.load_model("base")
    print("✅ Modelo Whisper cargado exitosamente")
except Exception as e:
    print(f"❌ Error cargando modelo: {e}")
    model = None

@app.route('/')
def home():
    return {
        "status": "ESP32 ChatGPT Proxy funcionando", 
        "model": "whisper-base",
        "version": "2.0"
    }

@app.route('/health')
def health():
    return {"status": "healthy", "model_loaded": model is not None}

@app.route('/process_audio/', methods=['POST'])
def process_audio():
    temp_files = []  # Para limpiar archivos temporales
    
    try:
        # Verificar autenticación
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Token de autorización requerido"}), 401
        
        # Verificar archivo
        if 'file' not in request.files:
            return jsonify({"error": "No se encontró archivo de audio"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "Nombre de archivo vacío"}), 400
        
        # Verificar modelo
        if model is None:
            return jsonify({"error": "Modelo Whisper no disponible"}), 503
        
        print(f"📁 Procesando: {file.filename}")
        
        # Guardar archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_input:
            file.save(temp_input.name)
            temp_files.append(temp_input.name)
            input_path = temp_input.name
        
        print(f"📊 Archivo guardado: {os.path.getsize(input_path)} bytes")
        
        # Transcribir con Whisper
        print("🎤 Transcribiendo...")
        result = model.transcribe(input_path, language="es")
        transcription = result["text"].strip()
        
        print(f"📝 Transcripción: '{transcription}'")
        
        if not transcription:
            return jsonify({"error": "No se detectó audio o está vacío"}), 400
        
        # Generar respuesta
        response_text = generate_response(transcription)
        print(f"🤖 Respuesta: '{response_text}'")
        
        # Convertir respuesta a audio
        audio_path = text_to_speech(response_text)
        temp_files.append(audio_path)
        
        # Verificar que el audio se generó
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            return jsonify({"error": "Error generando audio de respuesta"}), 500
        
        print(f"🔊 Audio generado: {os.path.getsize(audio_path)} bytes")
        
        # Enviar respuesta
        return send_file(
            audio_path,
            as_attachment=True,
            download_name="response.wav",
            mimetype="audio/wav"
        )
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({
            "error": "Error procesando audio", 
            "details": str(e)
        }), 500
        
    finally:
        # Limpiar archivos temporales
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass

def generate_response(text):
    """Genera respuesta simulada (puedes conectar OpenAI aquí)"""
    responses = [
        f"Hola, escuché que dijiste: {text}. ¿Cómo puedo ayudarte?",
        f"Gracias por tu mensaje: {text}. ¿En qué más puedo asistirte?",
        f"Recibí tu audio: {text}. ¿Tienes alguna pregunta específica?",
        f"Perfecto, dijiste: {text}. ¿Necesitas más información?",
        f"Entendido: {text}. ¿Hay algo más que quieras saber?"
    ]
    
    return random.choice(responses)

def text_to_speech(text, max_length=200):
    """Convierte texto a audio WAV"""
    try:
        # Limitar longitud para evitar archivos muy grandes
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        print(f"🗣️ Generando TTS para: '{text[:50]}...'")
        
        # Crear archivo temporal para MP3
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_mp3:
            mp3_path = temp_mp3.name
        
        # Crear archivo temporal para WAV
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_wav:
            wav_path = temp_wav.name
        
        # Generar audio con gTTS
        tts = gTTS(text=text, lang='es', slow=False)
        tts.save(mp3_path)
        
        # Convertir MP3 a WAV usando ffmpeg (disponible en Render)
        subprocess.run([
            'ffmpeg', '-y', '-i', mp3_path, 
            '-ar', '8000',  # 8kHz para ESP32
            '-ac', '1',     # Mono
            '-acodec', 'pcm_s16le',  # 16-bit PCM
            wav_path
        ], check=True, capture_output=True)
        
        # Limpiar MP3
        if os.path.exists(mp3_path):
            os.unlink(mp3_path)
        
        if os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
            return wav_path
        else:
            raise Exception("No se pudo generar archivo WAV")
            
    except subprocess.CalledProcessError as e:
        print(f"Error en ffmpeg: {e}")
        return create_silence_wav()
    except Exception as e:
        print(f"Error en TTS: {e}")
        return create_silence_wav()

def create_silence_wav():
    """Crea un archivo WAV de silencio como fallback"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            # Crear 1 segundo de silencio
            subprocess.run([
                'ffmpeg', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=8000:cl=mono', 
                '-t', '1', '-acodec', 'pcm_s16le', temp_file.name
            ], check=True, capture_output=True)
            
            return temp_file.name
    except:
        # Si todo falla, crear archivo vacío
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            temp_file.write(b'')
            return temp_file.name

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
