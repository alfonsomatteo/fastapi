from fastapi import FastAPI, UploadFile, File
import subprocess
import os
import tempfile

app = FastAPI()

# Endpoint di prova per verificare che il server sia attivo
@app.get("/")
async def root():
    return {"greeting": "Hello, World!", "message": "Welcome to FastAPI!"}

# Endpoint che utilizza FFmpeg per processare un file audio
@app.post("/processa-audio/")
async def processa_audio(file: UploadFile = File(...)):
    # Salva il file audio caricato temporaneamente
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
        temp_file.write(await file.read())
        temp_file_path = temp_file.name

    # Definisci il percorso di output
    output_file_path = temp_file_path.replace(".mp3", "_output.mp3")

    # Comando FFmpeg per modificare l'audio (esempio: aumento del volume)
    comando = [
        "ffmpeg",
        "-i", temp_file_path,
        "-af", "volume=1.5",
        output_file_path
    ]

    try:
        subprocess.run(comando, check=True)
        return {"message": "Processamento completato con successo."}
    except subprocess.CalledProcessError as e:
        return {"error": f"Errore durante il processamento: {e}"}
    finally:
        # Rimuovi i file temporanei
        os.remove(temp_file_path)
        if os.path.exists(output_file_path):
            os.remove(output_file_path)
