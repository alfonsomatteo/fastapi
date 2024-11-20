from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse
import subprocess
import os
import tempfile
import logging
from typing import Optional
import whisper
import openai

# Configurazione log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Middleware per limitare la dimensione dei file caricati
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    max_body_size = 50 * 1024 * 1024  # 50 MB
    if int(request.headers.get("content-length", 0)) > max_body_size:
        raise HTTPException(status_code=413, detail="File troppo grande")
    return await call_next(request)

# Funzioni utilitarie
def convert_to_mp3(input_path: str) -> str:
    """Converte un file audio in formato MP3 per assicurare compatibilità."""
    output_path = tempfile.mktemp(suffix=".mp3")
    convert_command = f"ffmpeg -y -i {input_path} -acodec libmp3lame -ar 48000 -ac 2 {output_path}"
    subprocess.run(convert_command, shell=True, check=True)
    return output_path

def create_silence(duration_ms: int) -> str:
    """Genera un file audio di silenzio della durata specificata in millisecondi."""
    output_path = tempfile.mktemp(suffix=".mp3")
    silence_command = f"ffmpeg -y -f lavfi -i anullsrc=r=48000:cl=stereo -t {duration_ms / 1000} {output_path}"
    subprocess.run(silence_command, shell=True, check=True)
    return output_path

def get_audio_duration(file_path: str) -> float:
    """Ritorna la durata dell'audio in secondi."""
    command = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {file_path}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return float(result.stdout.strip())

@app.get("/")
async def root():
    return {"greeting": "Hello, World!", "message": "Welcome to FastAPI!"}

@app.post("/monta-podcast/")
async def monta_podcast(
    background_tasks: BackgroundTasks,
    stacchetto: UploadFile = File(...),
    background_music: UploadFile = File(...),
    traccia_vocale1: Optional[UploadFile] = File(None),
    traccia_vocale2: Optional[UploadFile] = File(None),
    traccia_vocale3: Optional[UploadFile] = File(None),
    traccia_vocale4: Optional[UploadFile] = File(None),
    traccia_vocale5: Optional[UploadFile] = File(None),
    traccia_vocale6: Optional[UploadFile] = File(None),
    traccia_vocale7: Optional[UploadFile] = File(None),
    traccia_vocale8: Optional[UploadFile] = File(None),
    traccia_vocale9: Optional[UploadFile] = File(None),
    traccia_vocale10: Optional[UploadFile] = File(None),
):
    # Funzionalità di montaggio podcast, non modificata rispetto alla versione precedente
    ...

@app.post("/video-extraction/")
async def video_extraction(video: UploadFile = File(...)):
    temp_files = []
    try:
        # Salva il video caricato
        video_path = tempfile.mktemp(suffix=".mp4")
        with open(video_path, "wb") as f:
            f.write(await video.read())
        temp_files.append(video_path)

        # Estrai l'audio dal video
        audio_path = tempfile.mktemp(suffix=".mp3")
        extract_audio_command = f"ffmpeg -y -i {video_path} -q:a 0 -map a {audio_path}"
        subprocess.run(extract_audio_command, shell=True, check=True)
        temp_files.append(audio_path)

        # Trascrivi l'audio con Whisper
        model = whisper.load_model("base")
        transcription = model.transcribe(audio_path)
        text = transcription["text"]
        logger.info("Trascrizione completata.")

        # Genera una sintesi del testo con OpenAI
        openai.api_key = "il_tuo_openai_api_key"  # Assicurati di sostituire questa riga
        summary_response = openai.Completion.create(
            model="text-davinci-003",
            prompt=f"Riepiloga il seguente testo in modo conciso: {text}",
            max_tokens=300,
            temperature=0.5
        )
        summary = summary_response.choices[0].text.strip()
        logger.info("Sintesi completata.")

        # Rimuovi file temporanei
        for path in temp_files:
            os.remove(path)

        return {"transcription": text, "summary": summary}

    except subprocess.CalledProcessError as e:
        logger.error(f"Errore durante l'esecuzione di FFmpeg: {e}")
        raise HTTPException(status_code=500, detail="Errore durante l'elaborazione del file video.")
    except Exception as e:
        logger.error(f"Errore: {e}")
        raise HTTPException(status_code=500, detail="Errore interno al server.")


