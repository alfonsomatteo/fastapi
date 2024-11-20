from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import subprocess
import os
import tempfile
import openai
from typing import Optional

# Imposta la chiave API di OpenAI dalle variabili d'ambiente
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

@app.get("/")
async def root():
    return {"greeting": "Hello, World!", "message": "Welcome to FastAPI!"}

# Funzione per convertire audio in MP3
def convert_to_mp3(input_path: str) -> str:
    output_path = tempfile.mktemp(suffix=".mp3")
    convert_command = f"ffmpeg -y -i {input_path} -acodec libmp3lame -ar 48000 -ac 2 {output_path}"
    subprocess.run(convert_command, shell=True, check=True)
    return output_path

# Funzione per creare silenzio
def create_silence(duration_ms: int) -> str:
    output_path = tempfile.mktemp(suffix=".mp3")
    silence_command = f"ffmpeg -y -f lavfi -i anullsrc=r=48000:cl=stereo -t {duration_ms / 1000} {output_path}"
    subprocess.run(silence_command, shell=True, check=True)
    return output_path

# Funzione per calcolare la durata di un file audio
def get_audio_duration(file_path: str) -> float:
    command = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {file_path}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return float(result.stdout.strip())

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
    temp_files = []
    tracce_paths = []

    try:
        # Salva e converte lo stacchetto in MP3
        stacchetto_path = tempfile.mktemp(suffix=".mp3")
        with open(stacchetto_path, "wb") as f:
            f.write(await stacchetto.read())
        stacchetto_path = convert_to_mp3(stacchetto_path)
        temp_files.append(stacchetto_path)

        # Salva e converte la musica di sottofondo in MP3
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

        # Salva e converte ogni traccia vocale fornita in MP3
        for traccia in tracce_vocali:
            if traccia is not None:
                traccia_path = tempfile.mktemp(suffix=".mp3")
                with open(traccia_path, "wb") as f:
                    f.write(await traccia.read())
                traccia_path = convert_to_mp3(traccia_path)
                tracce_paths.append(traccia_path)
                temp_files.append(traccia_path)

        # Genera un file di silenzio breve (500ms) tra le tracce vocali
        silence_path = create_silence(500)
        temp_files.append(silence_path)

        # Concatenazione delle tracce vocali con lo stacchetto e i silenzi
        concatenated_audio_path = tempfile.mktemp(suffix=".mp3")
        concat_list_path = tempfile.mktemp(suffix=".txt")
        temp_files.append(concat_list_path)

        # Creiamo un file di testo per la concatenazione
        with open(concat_list_path, "w") as f:
            f.write(f"file '{stacchetto_path}'\n")
            for idx, traccia_path in enumerate(tracce_paths):
                f.write(f"file '{traccia_path}'\n")
                if idx < len(tracce_paths) - 1:  # Aggiunge silenzio solo tra le tracce vocali
                    f.write(f"file '{silence_path}'\n")

        # Comando per concatenare i file usando un file di lista
        concat_command = f"ffmpeg -y -f concat -safe 0 -i {concat_list_path} -c copy {concatenated_audio_path}"
        subprocess.run(concat_command, shell=True, check=True)
        temp_files.append(concatenated_audio_path)

        # Calcola la durata totale delle tracce vocali concatenate
        durata_voci = get_audio_duration(concatenated_audio_path) + 1.5  # Aggiungi 1.5 secondi per la dissolvenza finale

        # Percorso per il file finale del podcast
        output_podcast_path = tempfile.mktemp(suffix=".mp3")

        # Comando per gestire il loop della musica di sottofondo e dissolvenza
        final_command = (
            f"ffmpeg -y -stream_loop -1 -i {background_music_path} -i {concatenated_audio_path} "
            f"-filter_complex \"[0]volume=0.1,afade=t=in:st=0:d=2,afade=t=out:st={durata_voci - 1.5}:d=1.5[bg];"
            f"[1][bg]amix=inputs=2:duration=shortest\" -t {durata_voci} {output_podcast_path}"
        )
        subprocess.run(final_command, shell=True, check=True)

        # Pianifica la rimozione del file di output dopo l'invio della risposta
        background_tasks.add_task(os.remove, output_podcast_path)

        # Pianifica la rimozione dei file temporanei di input
        for path in temp_files:
            background_tasks.add_task(os.remove, path)

        return FileResponse(output_podcast_path, media_type='audio/mpeg', filename="podcast_finale.mp3")

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Errore durante il montaggio: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/video-transcription-summary/")
async def video_transcription_summary(video: UploadFile = File(...)):
    temp_files = []
    try:
        # Salva il video
        video_path = tempfile.mktemp(suffix=".mp4")
        with open(video_path, "wb") as f:
            f.write(await video.read())
        temp_files.append(video_path)

        # Estrai l'audio dal video
        audio_path = tempfile.mktemp(suffix=".mp3")
        extract_audio_command = f"ffmpeg -y -i {video_path} -q:a 0 -map a {audio_path}"
        subprocess.run(extract_audio_command, shell=True, check=True)
        temp_files.append(audio_path)

        # Usa Whisper per la trascrizione
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        transcription = result["text"]

        # Usa OpenAI per generare una sintesi
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Sei un assistente che riassume trascrizioni video in modo chiaro ed esaustivo."},
                {"role": "user", "content": transcription}
            ],
            max_tokens=500,
            temperature=0.7
        )
        summary = response["choices"][0]["message"]["content"].strip()

        # Pianifica la rimozione dei file temporanei
        for path in temp_files:
            os.remove(path)

        # Restituisci il risultato
        return {"transcription": transcription, "summary": summary}

    except Exception as e:
        for path in temp_files:
            if os.path.exists(path):
                os.remove(path)
        raise HTTPException(status_code=500, detail=str(e))
