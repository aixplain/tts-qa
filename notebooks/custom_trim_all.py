import os
import sys


sys.path.append("../")

import psycopg2
from dotenv import load_dotenv
from tqdm import tqdm

# Assuming custom_vad_function is a function you have that takes a filename and returns new start and end trim times
from src.utils.audio import CustomVAD, trim_audio


my_custom_vad = CustomVAD(pyannote_model_path="pyannote/segmentation", silero_model_path="snakers4/silero-vad")

# Load environment variables
load_dotenv("../vars.env")

# Database credentials
db_host = os.getenv("POSTGRES_HOST")
db_name = os.getenv("POSTGRES_DB")
db_user = os.getenv("POSTGRES_USER")
db_password = os.getenv("POSTGRES_PWD")

# Establish a database connection
conn = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_password)
cur = conn.cursor()

# Retrieve all datasets
cur.execute("SELECT id, name FROM dataset;")
datasets = cur.fetchall()


# for each of the folder under /data/tts-qa/tts-data/ go one level down an generate trimmed2 folder
folders = os.listdir("/data/tts-qa/tts-data/")

for folder in folders:
    if os.path.isdir("/data/tts-qa/tts-data/" + folder):
        if not os.path.exists("/data/tts-qa/tts-data/" + folder + "/trimmed2"):
            os.mkdir("/data/tts-qa/tts-data/" + folder + "/trimmed2")

from src.utils.db_utils import convert_to_88k, convert_to_mono, convert_to_s16le, evaluate_audio, normalize_audio


# Process each dataset
for dataset_id, dataset_name in datasets:
    if dataset_name == "English(Melynda)":
        my_custom_vad.set_padding(0.075)
    else:
        continue
    if dataset_name in ["English (Alyssa)"]:
        continue
    if dataset_name == "German(Dorothee)":
        my_custom_vad.set_energy_threshold(3_000_000)

    print(f"Processing dataset: {dataset_name}")

    # Retrieve all samples that are selected for delivery from the current dataset
    cur.execute(
        """
        SELECT id, filename, local_path, local_trimmed_path
        FROM sample
        WHERE dataset_id = %s;
    """,
        (dataset_id,),
    )
    samples = cur.fetchall()

    # Loop over each sample
    for id, filename, local_path, local_trimmed_path in tqdm(samples):
        # Define the new trimmed path  from '/data/tts-qa/tts-data/French(Dorsaf) Deliverable 7/trimmed/FR00054280.wav'
        trimmed2_path = local_trimmed_path.replace("trimmed", "trimmed2")

        # if os.path.exists(trimmed2_path):
        #     continue

        # Run custom VAD to get new trim times
        response = my_custom_vad.process_file(local_path)

        trim_start, trim_end = tuple(response["custom_segment"])

        # round 2
        trim_start = round(trim_start, 2)
        trim_end = round(trim_end, 2)

        # Trim the audio
        trim_audio(local_path, trim_start, trim_end, trimmed2_path)
        duration = float(trim_end - trim_start)

        if dataset_name == "German(Dorothee)":
            meta = evaluate_audio(trimmed2_path)

            if meta["is_88khz"] == False:
                convert_to_88k(trimmed2_path, trimmed2_path)

            if meta["is_mono"] == False:
                convert_to_mono(trimmed2_path, trimmed2_path)

            if meta["peak_volume_db"] < -6 or meta["peak_volume_db"] > -3:
                normalize_audio(trimmed2_path, trimmed2_path)

            if meta["isPCM"] == False:
                convert_to_s16le(trimmed2_path, trimmed2_path)

        try:
            # Update the database with the new trim times (if necessary)
            cur.execute(
                """
                UPDATE sample
                SET trim_custom_start = %s, trim_custom_end = %s, local_custom_trimmed_path = %s, custom_trimmed_audio_duration = %s
                WHERE id = %s;
            """,
                (trim_start, trim_end, trimmed2_path, duration, id),
            )
            conn.commit()
        except Exception as e:
            print(f"Error updating database: {e}")
            os.remove(trimmed2_path)
            conn.rollback()


# Close the database connection
cur.close()
conn.close()
