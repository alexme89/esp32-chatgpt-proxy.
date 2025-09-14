# proxy.py - Versión simple sin ML
from flask import Flask, request, jsonify, send_file
import os
import tempfile
from gtts import gTTS
import subprocess
import random
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return {
        "status": "ESP32 ChatGPT Proxy funcionando", 
        "version": "3.0 - Simple",
        "features": ["TTS", "Echo responses"]
    }

@app.route('/health')
def health():
    return {"status": "healthy"}

@app.route('/process_audio/', methods=['POST'])
def process_audio():
    temp_files = []
    
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
        
        print(f"📁 Procesando: {file.filename}")
        
        # Guardar archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_input:
            file.save(temp_input.name)
            temp_files.append(temp_input.name)
            input_path = temp_input.name
        
        print(f"📊 Archivo recibido: {os.path.getsize(input_path)} bytes")
        
        # Por ahora, generar respuesta basada en el tamaño del archivo o tiempo
        file_size = os.path.getsize(input_path)
        
        # Estimar duración aproximada (muy rough)
        estimated_duration = file_size / 16000  # Aproximación para 8kHz mono
        
        # Generar respuesta basada en duración
        if estimated_duration < 1:
            transcription = "Hola"
        elif estimated_duration < 3:
            transcription = "¿Cómo estás?"
        elif estimated_duration < 5:
            transcription = "¿En qué puedo ayudarte hoy?"
        else:
            transcription = "Mensaje recibido correctamente"
        
        print(f"📝 Simulando transcripción: '{transcription}'")
        
        # Generar respuesta
        response_text = generate_response(transcription, file_size)
        print(f"🤖 Respuesta: '{response_text}'")
        
        # Convertir respuesta a audio
        audio_path = text_to_speech(response_text)
        temp_files.append(audio_path)
        
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

def generate_response(transcription, file_size):
    """Genera respuesta basada en la 'transcripción' simulada"""
    
    responses = {
        "Hola": [
            "¡Hola! ¿Cómo estás? Recibí tu saludo perfectamente.",
            "¡Hola! Es un gusto escucharte. ¿En qué puedo ayudarte?",
            "¡Saludos! Tu audio se recibió correctamente."
        ],
        "¿Cómo estás?": [
            "¡Muy bien, gracias por preguntar! ¿Y tú cómo estás?",
            "Todo perfecto por aquí. ¿Cómo te encuentras tú?",
            "Funcionando al 100%. ¿Qué tal tu día?"
        ],
        "¿En qué puedo ayudarte hoy?": [
            "Perfecto, estoy aquí para lo que necesites. ¿Tienes alguna pregunta?",
            "Excelente pregunta. Puedo ayudarte con información o conversación.",
            "Genial, soy tu asistente de voz. ¿Qué te interesa saber?"
        ],
        "Mensaje recibido correctamente": [
            f"Recibí tu mensaje de {file_size} bytes. ¿Hay algo específico en lo que pueda ayudarte?",
            "Tu audio llegó perfectamente. ¿Qué más te gustaría saber?",
            f"Mensaje procesado exitosamente. Duración estimada: {file_size/8000:.1f} segundos."
        ]
    }
    
    # Si no encuentra la transcripción exacta, usar respuesta genérica
    if transcription not in responses:
        generic_responses = [
            f"Recibí tu audio de {file_size} bytes. ¿Puedes repetir tu pregunta?",
            "Tu mensaje llegó bien, pero no estoy seguro de qué dijiste. ¿Podrías hablar más claro?",
            "Audio procesado. ¿En qué puedo ayudarte específicamente?"
        ]
        return random.choice(generic_responses)
    
    return random.choice(responses[transcription])

def text_to_speech(text, max_length=200):
    """Convierte texto a audio WAV"""
    try:
        # Limitar longitud
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        print(f"🗣️ Generando TTS: '{text[:50]}...'")
        
        # Archivos temporales
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_mp3:
            mp3_path = temp_mp3.name
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_wav:
            wav_path = temp_wav.name
        
        # Generar con gTTS
        tts = gTTS(text=text, lang='es', slow=False)
        tts.save(mp3_path)
        
        # Verificar que se creó el MP3
        if not os.path.exists(mp3_path) or os.path.getsize(mp3_path) == 0:
            raise Exception("No se pudo generar MP3")
        
        # Convertir a WAV con ffmpeg
        result = subprocess.run([
            'ffmpeg', '-y', '-i', mp3_path, 
            '-ar', '8000',  # 8kHz para ESP32
            '-ac', '1',     # Mono
            '-acodec', 'pcm_s16le',  # 16-bit PCM
            wav_path
        ], capture_output=True, text=True)
        
        # Verificar que ffmpeg funcionó
        if result.returncode != 0:
            print(f"Error ffmpeg: {result.stderr}")
            raise Exception("Error en conversión ffmpeg")
        
        # Limpiar MP3
        if os.path.exists(mp3_path):
            os.unlink(mp3_path)
        
        # Verificar WAV final
        if os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
            return wav_path
        else:
            raise Exception("Archivo WAV vacío o no existe")
            
    except Exception as e:
        print(f"Error en TTS: {e}")
        return create_silence_wav()

def create_silence_wav():
    """Crea un archivo WAV de silencio como fallback"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            # Crear 1 segundo de silencio con ffmpeg
            result = subprocess.run([
                'ffmpeg', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=8000:cl=mono', 
                '-t', '1', '-acodec', 'pcm_s16le', temp_file.name
            ], capture_output=True)
            
            if result.returncode == 0 and os.path.getsize(temp_file.name) > 0:
                return temp_file.name
            else:
                raise Exception("No se pudo crear silencio con ffmpeg")
                
    except Exception as e:
        print(f"Error creando silencio: {e}")
        # Crear WAV header mínimo manualmente
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                # Header WAV básico para 1 segundo de silencio a 8kHz mono
                header = bytearray([
                    0x52, 0x49, 0x46, 0x46,  # RIFF
                    0x24, 0x3E, 0x00, 0x00,  # ChunkSize
                    0x57, 0x41, 0x56, 0x45,  # WAVE
                    0x66, 0x6D, 0x74, 0x20,  # fmt 
                    0x10, 0x00, 0x00, 0x00,  # Subchunk1Size
                    0x01, 0x00,              # AudioFormat
                    0x01, 0x00,              # NumChannels
                    0x40, 0x1F, 0x00, 0x00,  # SampleRate (8000)
                    0x80, 0x3E, 0x00, 0x00,  # ByteRate
                    0x02, 0x00,              # BlockAlign
                    0x10, 0x00,              # BitsPerSample
                    0x64, 0x61, 0x74, 0x61,  # data
                    0x00, 0x3E, 0x00, 0x00   # Subchunk2Size
                ])
                
                temp_file.write(header)
                # Escribir silencio (8000 muestras de 16-bit = 16000 bytes de ceros)
                silence = bytes(16000)
                temp_file.write(silence)
                
                return temp_file.name
        except:
            return None

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
