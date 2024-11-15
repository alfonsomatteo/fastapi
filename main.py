from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import subprocess
import os
import tempfile

app = FastAPI()

@app.get("/")
async def root():
    return {"greeting": "Hello, World!", "message": "Welcome to FastAPI!"}

@app.post("/monta-podcast/")
async def monta_podcast(
    background_tasks: BackgroundTasks,
    stacchetto: UploadFile = File(...),
    background_music: UploadFile = File(...),
    tracce_vocali: list[UploadFile] = File(...)
):
    # Percorsi temporanei per i file caricati
    temp_files = []

    try:
        # Salva lo stacchetto in un file temporaneo
        stacchetto_path = tempfile.mktemp(suffix=".mp3")
        with open(stacchetto_path, "wb") as f:
            f.write(await stacchetto.read())
        temp_files.append(stacchetto_path)

        # Salva la musica di sottofondo in un file temporaneo
        background_music_path = tempfile.mktemp(suffix=".mp3")
        with open(background_music_path, "wb") as f:
            f.write(await background_music.read())
        temp_files.append(background_music_path)

        # Salva le tracce vocali in file temporanei
        tracce_paths = []
        for traccia in tracce_vocali:
            traccia_path = tempfile.mktemp(suffix=".mp3")
            with open(traccia_path, "wb") as f:
                f.write(await traccia.read())
            tracce_paths.append(traccia_path)
            temp_files.append(traccia_path)

        # Concatenazione dello stacchetto e delle tracce vocali
        concatenated_audio_path = tempfile.mktemp(suffix=".mp3")
        concat_list_path = tempfile.mktemp(suffix=".txt")
        temp_files.append(concat_list_path)
        
        # Creiamo un file di testo per la concatenazione
        with open(concat_list_path, "w") as f:
            f.write(f"file '{stacchetto_path}'\n")
            for traccia_path in tracce_paths:
                f.write(f"file '{traccia_path}'\n")

        # Comando per concatenare i file usando un file di lista
        concat_command = (
            f"ffmpeg -y -f concat -safe 0 -i {concat_list_path} -c copy {concatenated_audio_path}"
        )
        subprocess.run(concat_command, shell=True, check=True)
        temp_files.append(concatenated_audio_path)

        # Percorso per il file finale del podcast
        output_podcast_path = tempfile.mktemp(suffix=".mp3")

        # Comando per aggiungere la musica di sottofondo al file concatenato
        final_command = (
            f"ffmpeg -y -i {concatenated_audio_path} -i {background_music_path} "
            f"-filter_complex \"[1]volume=0.2[audio];[0][audio]amix=inputs=2:duration=longest\" "
            f"{output_podcast_path}"
        )

        # Esegui il comando FFmpeg e cattura l'output
        result = subprocess.run(final_command, shell=True, check=True, text=True, capture_output=True)
        print("FFmpeg output:", result.stdout)
        print("FFmpeg error (if any):", result.stderr)

        # Controlla se il file è stato effettivamente creato
        if not os.path.exists(output_podcast_path):
            print("Errore: Il file di output non esiste.")
            raise HTTPException(status_code=500, detail="Errore nella generazione del file audio finale.")

        print("File generato con successo:", output_podcast_path)
        
        # Pianifica la rimozione del file di output dopo l'invio della risposta
        background_tasks.add_task(os.remove, output_podcast_path)

        # Pianifica la rimozione dei file temporanei di input
        for path in temp_files:
            background_tasks.add_task(os.remove, path)

        # Restituisci il file audio finale come risposta
        return FileResponse(output_podcast_path, media_type='audio/mpeg', filename="podcast_finale.mp3")

    except subprocess.CalledProcessError as e:
        print("Errore durante il comando FFmpeg:", e.stderr)
        raise HTTPException(status_code=500, detail=f"Errore durante il montaggio: {e}")
    except Exception as e:
        print("Errore:", str(e))
        raise
