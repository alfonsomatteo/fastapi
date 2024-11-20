from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import openai
import subprocess
import os
import tempfile
from typing import Optional

app = FastAPI()

# Configura la chiave API di OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.get("/")
async def root():
    return {"message": "Benvenuto nel servizio API per montaggio podcast e trascrizione video"}

def convert_to_mp3(input_path: str) -> str:
    """Converte un file audio in formato MP3."""
    output_path = tempfile.mktemp(suffix=".mp3")
    convert_command = f"ffmpeg -y -i {input_path} -acodec libmp3lame -ar 48000 -ac 2 {output_path}"
    subprocess.run(convert_command, shell=True, check=True)
    return output_path

def get_audio_duration(file_path: str) -> float:
    """Ottiene la durata di un file audio."""
    command = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {file_path}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return float(result.stdout.strip())

@app.post("/transcribe-video/")
async def transcribe_video(video: UploadFile = File(...)):
    """Estrae l'audio da un video, lo trascrive e ne fornisce una sintesi."""
    temp_files = []

    try:
        # Salva il file video in modo temporaneo
        video_path = tempfile.mktemp(suffix=".mp4")
        with open(video_path, "wb") as f:
            f.write(await video.read())
        temp_files.append(video_path)

        # Estrai l'audio dal video
        audio_path = tempfile.mktemp(suffix=".mp3")
        extract_command = f"ffmpeg -y -i {video_path} -vn -acodec libmp3lame {audio_path}"
        subprocess.run(extract_command, shell=True, check=True)
        temp_files.append(audio_path)

        # Utilizza Whisper per trascrivere l'audio
        import whisper
        model = whisper.load_model("small")
        result = model.transcribe(audio_path, language="it")

        # Genera una sintesi del testo trascritto con OpenAI
        transcription = result['text']
        chat_response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Sei un assistente utile."},
                {"role": "user", "content": f"Riassumi il seguente testo: {transcription}"}
            ]
        )

        summary = chat_response['choices'][0]['message']['content']

        # Pulizia dei file temporanei
        for file in temp_files:
            os.remove(file)

        return {"transcription": transcription, "summary": summary}

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Errore durante l'elaborazione del video: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    """Monta un podcast con stacchetto, musica di sottofondo e tracce vocali."""
    temp_files = []
    tracce_paths = []

    try:
        # Salva e converte lo stacchetto
        stacchetto_path = tempfile.mktemp(suffix=".mp3")
        with open(stacchetto_path, "wb") as f:
            f.write(await stacchetto.read())
        stacchetto_path = convert_to_mp3(stacchetto_path)
        temp_files.append(stacchetto_path)

        # Salva e converte la musica di sottofondo
        background_music_path = tempfile.mktemp(suffix=".mp3")
        with open(background_music_path, "wb") as f:
            f.write(await background_music.read())
        background_music_path = convert_to_mp3(background_music_path)
        temp_files.append(background_music_path)

        # Lista delle tracce vocali
        tracce_vocali = [
            traccia_vocale1, traccia_vocale2, traccia_vocale3, traccia_vocale4,
            traccia_vocale5, traccia_vocale6, traccia_vocale7, traccia_vocale8,
            traccia_vocale9, traccia_vocale10
        ]

        # Salva e converte ogni traccia vocale fornita
        for traccia in tracce_vocali:
            if traccia:
                traccia_path = tempfile.mktemp(suffix=".mp3")
                with open(traccia_path, "wb") as f:
                    f.write(await traccia.read())
                traccia_path = convert_to_mp3(traccia_path)
                tracce_paths.append(traccia_path)
                temp_files.append(traccia_path)

        # Concatenazione delle tracce vocali
        concatenated_audio_path = tempfile.mktemp(suffix=".mp3")
        concat_list_path = tempfile.mktemp(suffix=".txt")
        with open(concat_list_path, "w") as f:
            f.write(f"file '{stacchetto_path}'\n")
            for traccia_path in tracce_paths:
                f.write(f"file '{traccia_path}'\n")
            f.write(f"file '{background_music_path}'\n")

        concat_command = f"ffmpeg -y -f concat -safe 0 -i {concat_list_path} -c copy {concatenated_audio_path}"
        subprocess.run(concat_command, shell=True, check=True)
        temp_files.append(concatenated_audio_path)

        # Ritorna il file audio generato
        output_podcast_path = tempfile.mktemp(suffix=".mp3")
        final_command = f"ffmpeg -y -i {concatenated_audio_path} -i {background_music_path} -filter_complex \"amix=inputs=2\" {output_podcast_path}"
        subprocess.run(final_command, shell=True, check=True)

        background_tasks.add_task(os.remove, output_podcast_path)
        for path in temp_files:
            background_tasks.add_task(os.remove, path)

        return FileResponse(output_podcast_path, media_type="audio/mpeg", filename="podcast_finale.mp3")

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Errore durante il montaggio: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
