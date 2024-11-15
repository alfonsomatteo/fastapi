from fastapi import FastAPI, UploadFile, File, HTTPException
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
    stacchetto: UploadFile = File(...),
    background_music: UploadFile = File(...),
    tracce_vocali: list[UploadFile] = File(...)
):
    # Percorsi temporanei per i file caricati
    temp_files = []

    # Salva lo stacchetto in un file temporaneo
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
        temp_file.write(await stacchetto.read())
        stacchetto_path = temp_file.name
        temp_files.append(stacchetto_path)

    # Salva la musica di sottofondo in un file temporaneo
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
        temp_file.write(await background_music.read())
        background_music_path = temp_file.name
        temp_files.append(background_music_path)

    # Salva le tracce vocali in file temporanei
    tracce_paths = []
    for idx, traccia in enumerate(tracce_vocali):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            temp_file.write(await traccia.read())
            tracce_paths.append(temp_file.name)
            temp_files.append(temp_file.name)

    # Percorso per il file finale del podcast
    output_podcast_path = tempfile.mktemp(suffix=".mp3")
    temp_files.append(output_podcast_path)

    # Comando FFmpeg per combinare i file audio
    inputs = " ".join([f"-i {path}" for path in [stacchetto_path] + tracce_paths + [background_music_path]])
    filter_complex = f"[0:a] [1:a] amerge=inputs=2 [bg];"
    for i in range(len(tracce_paths)):
        filter_complex += f"[{i+2}:a][bg]amix=inputs=2:duration=longest[bg];"
    final_map = f"-map [bg] {output_podcast_path}"

    comando = f"ffmpeg {inputs} -filter_complex \"{filter_complex}\" {final_map}"

    # Esegui il comando FFmpeg e cattura l'output
    try:
        result = subprocess.run(comando, shell=True, check=True, text=True, capture_output=True)
        print("FFmpeg output:", result.stdout)  # Log dell'output di FFmpeg
        print("FFmpeg error (if any):", result.stderr)

        # Controlla se il file è stato effettivamente creato
        if not os.path.exists(output_podcast_path):
            print("Errore: Il file di output non esiste.")
            raise HTTPException(status_code=500, detail="Errore nella generazione del file audio finale.")

        print("File generato con successo:", output_podcast_path)
        
        # Restituisci il file audio finale come risposta
        return FileResponse(output_podcast_path, media_type='audio/mpeg', filename="podcast_finale.mp3")
    except subprocess.CalledProcessError as e:
        print("Errore durante il comando FFmpeg:", e.stderr)
        raise HTTPException(status_code=500, detail=f"Errore durante il montaggio: {e}")
    finally:
        # Rimuovi tutti i file temporanei
        for path in temp_files:
            if os.path.exists(path):
                os.remove(path)
