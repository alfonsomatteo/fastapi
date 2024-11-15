from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import subprocess
import os
import tempfile

app = FastAPI()

@app.post("/process-podcast/")
async def process_podcast(stacchetto: UploadFile = File(...), background_music: UploadFile = File(...), tracce_vocali: list[UploadFile] = File(...)):
    temp_files = []
    
    try:
        # Salva tutti i file caricati temporaneamente
        stacchetto_path = save_temp_file(stacchetto, temp_files)
        background_music_path = save_temp_file(background_music, temp_files)
        tracce_vocali_paths = [save_temp_file(traccia, temp_files) for traccia in tracce_vocali]

        # Combina le tracce vocali in un unico file con piccole pause tra le tracce
        combined_voci_path = os.path.join("/tmp", next(tempfile._get_candidate_names()) + ".mp3")
        create_combined_voci_file(tracce_vocali_paths, combined_voci_path)

        # Applica la dissolvenza alla fine del sottofondo
        final_output_path = os.path.join("/tmp", next(tempfile._get_candidate_names()) + ".mp3")
        apply_background_with_fadeout(stacchetto_path, background_music_path, combined_voci_path, final_output_path)

        # Restituisce il file audio finale come risposta scaricabile
        return FileResponse(final_output_path, filename="podcast_finale.mp3", media_type="audio/mpeg")

    except Exception as e:
        return {"detail": f"Errore durante il montaggio: {e}"}
    finally:
        # Pulisce i file temporanei
        for file in temp_files:
            os.remove(file)

def save_temp_file(upload_file, temp_files):
    temp_path = os.path.join("/tmp", next(tempfile._get_candidate_names()) + ".mp3")
    with open(temp_path, "wb") as f:
        f.write(upload_file.file.read())
    temp_files.append(temp_path)
    return temp_path

def create_combined_voci_file(tracce_vocali_paths, output_path):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        concat_file_list = "\n".join([f"file '{path}'\nfile 'silent.mp3'" for path in tracce_vocali_paths])
        f.write(concat_file_list.encode())
        f.flush()
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f.name,
            "-c", "copy", output_path
        ], check=True)

def apply_background_with_fadeout(stacchetto_path, background_music_path, combined_voci_path, output_path):
    subprocess.run([
        "ffmpeg", "-y", "-i", combined_voci_path, "-i", background_music_path,
        "-filter_complex",
        "[1]afade=t=out:st=90:d=5[bg];[0][bg]amix=inputs=2:duration=longest:dropout_transition=3",
        "-c:a", "libmp3lame", output_path
    ], check=True)

