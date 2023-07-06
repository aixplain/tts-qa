import json
import os
import pickle
import re
import shutil
import tempfile
import traceback
from glob import glob
from typing import Tuple

import editdistance
import numpy as np
import pandas as pd
import whisper_timestamped as whisperts
from celery import Task
from pyannote.audio import Model
from pyannote.audio.pipelines import VoiceActivityDetection
from pydub import AudioSegment
from tqdm import tqdm

from src.logger import root_logger
from src.utils.audio import trim_audio
from src.utils.whisper_model import WhisperASR


app_logger = root_logger.getChild("alignment_utils")


def edit_distance(s1, s2):
    return editdistance.eval(s1, s2)


def format_int(i):
    return str(i).zfill(8)


padding = 0.25


def align_wavs_whisper(
    job: Task, wavs_path: str, csv_path: str, language: str, start_id_regex: str, end_id_regex: str, assigned_only: bool = True
) -> Tuple[str, str]:
    whisper_model = whisperts.load_model("large-v2", device="cuda")
    app_logger.info(f"wav_path: {wavs_path}")
    filenames = glob(os.path.join(wavs_path, "*.wav"))
    app_logger.info(f"Found {len(filenames)} wav files")

    temp_dir = tempfile.mkdtemp()

    # create a wavs dir in temp dir
    output_wavs_dir = os.path.join(temp_dir, "wavs")
    # no error if exists
    os.mkdir(output_wavs_dir)
    try:
        dfs = []
        for filename in filenames:
            app_logger.info(f"Processing {filename}")
            segments_path = filename + ".vad-segments.json"
            if os.path.exists(segments_path):
                app_logger.info(f"Detected segments file {filename}")
                vad_segments = json.load(open(segments_path))
            else:
                app_logger.info(f"Generating segments file {filename}")
                audio = whisperts.load_audio(filename)
                results = whisperts.transcribe(whisper_model, audio, vad=True, detect_disfluencies=False, language=language)
                vad_segments = results["segments"]

                app_logger.info(f"Saving segments for {filename}")
                with open(segments_path, "w") as f:
                    json.dump(vad_segments, f)
                app_logger.info(f"Saved segments for {filename} to {segments_path}")

            data = AudioSegment.from_file(filename)

            start_loc = int(re.search(start_id_regex, filename).group(1))
            end_loc = int(re.search(end_id_regex, filename).group(1))

            app_logger.info(f"start_loc: {start_loc}, end_loc: {end_loc}")

            sentences = {}
            inverseSentences = {}
            df_sentences = pd.read_csv(csv_path)
            id_int = df_sentences["unique_identifier"].apply(lambda x: int(x[2:]))
            df_sentences["id_int"] = id_int
            df_sentences.set_index("id_int", inplace=True)
            # include only ids in between start_loc and end_loc
            df_sentences = df_sentences.loc[start_loc:end_loc]

            app_logger.info(f"There are {len(df_sentences)} sentences in this range")
            for index, row in df_sentences.iterrows():
                sentenceNum = int(index)
                sentence = row["text"]
                sentences[sentenceNum] = sentence
                if sentence not in inverseSentences:
                    inverseSentences[sentence] = sentenceNum
                else:
                    tmp = sentence
                    while tmp in inverseSentences:
                        tmp += " _"
                    inverseSentences[tmp] = sentenceNum
            sentenceNumber = -1
            segments = {}
            segments_path = os.path.join(temp_dir, filename + ".segments.json")
            if os.path.exists(segments_path):
                app_logger.info(f"Detected segments for {filename}  at {segments_path}- loading from file")
                segments = json.load(open(segments_path))
            else:
                app_logger.info(f"Running ASR for {filename}")
                for segment in tqdm(vad_segments):
                    start = segment["start"]
                    end = segment["end"]
                    text = segment["text"]

                    start = max(0, start - padding)
                    end = min(end + padding, len(data) / 1000)
                    seg = {}
                    seg["SegmentStart"] = start
                    seg["SegmentEnd"] = end
                    seg["asr"] = text
                    outputAudio = AudioSegment.empty()
                    outputAudio += data[seg["SegmentStart"] * 1000 : seg["SegmentEnd"] * 1000]
                    # save audio to a tmp file
                    temp_file = os.path.join(temp_dir, "tmp.wav")
                    outputAudio.export(temp_file, format="wav")
                    segments[start] = seg
                # save segments
                print(f"Saving segments for {filename}")
                with open(segments_path, "w") as fout:
                    json.dump(segments, fout, indent=4)
                print(f"Saved segments for {filename}")
            print(f"Matching segments to sentences for {filename}")
            segments_list = [v for k, v in segments.items()]
            sentences_list = [v for k, v in sentences.items()]
            distances_matrix = np.ones((len(segments_list), len(sentences_list))) * 1000
            for ik in range(len(segments_list)):
                for jk, sentence in enumerate(sentences_list):
                    try:
                        distances_matrix[ik, jk] = edit_distance(segments_list[ik]["asr"], sentence) / min(len(segments_list[ik]["asr"]), len(sentence))
                    except:
                        distances_matrix[ik, jk] = np.inf

            # get the best match for each segment
            best_matches = np.argmin(distances_matrix, axis=1)
            # # make a dataframe
            columns = ["status", "filename", "sentenceNumber", "sentence", "asr", "start", "end", "ed_dist", "len_dif"]
            df = pd.DataFrame(columns=columns)
            best_matched_sentences = [sentences_list[k] for k in best_matches]

            # print the results
            for ik in range(len(segments_list)):
                asr = segments_list[ik]["asr"]
                sentence = best_matched_sentences[ik]
                ed_dist = distances_matrix[ik, best_matches[ik]]
                try:
                    len_dif = abs(len(asr) - len(sentence)) / min(len(asr), len(sentence))
                except:
                    len_dif = np.inf
                start = segments_list[ik]["SegmentStart"]
                end = segments_list[ik]["SegmentEnd"]
                sentenceNumber = inverseSentences[sentence]
                if ed_dist < 0.25 and len_dif < 0.15:
                    status = "assigned"
                else:
                    status = "not_assigned"

                row = {
                    "status": status,
                    "filename": filename,
                    "sentenceNumber": sentenceNumber,
                    "sentence": sentence,
                    "asr": asr,
                    "start": start,
                    "end": end,
                    "ed_dist": ed_dist,
                    "len_dif": len_dif,
                }
                df = df.append(row, ignore_index=True)
            # if there is inf  drop it
            df = df.replace([np.inf, -np.inf], np.nan)
            df.dropna(inplace=True)

            app_logger.info(f"Assigned {len(df[df.status=='assigned'])} segments")
            app_logger.info(f"Not assigned {len(df[df.status=='not_assigned'])} segments")

            # if there are multiple rows with same sentenceNumber take the last one and drop the rest
            df = df.sort_values(by=["sentenceNumber"])
            df = df.drop_duplicates(subset=["sentenceNumber"], keep="last")

            app_logger.info(f"Status counts for {filename}:")
            app_logger.info(df.status.value_counts())
            # df.to_csv(filename + ".csv", index=False)

            # create "assigned" and "not_assigned" folders
            os.makedirs(os.path.join(output_wavs_dir, "assigned"), exist_ok=True)
            os.makedirs(os.path.join(output_wavs_dir, "not_assigned"), exist_ok=True)

            # for each row in the dataframe if the status is assigned, create a wav file with the start and end times of the segment
            # if not assigned, create a wav file with the start and end times of the segment
            app_logger.info(f"Trimming audio for {filename}, it will be saved in {output_wavs_dir}")
            # columns should be following: local_path,file_name,unique_identifier,text,sentence_length,sentence_type
            columns = ["status", "local_path", "file_name", "unique_identifier", "text", "sentence_length", "sentence_type"]
            df_final = pd.DataFrame(columns=columns)
            for index, row in tqdm(df.iterrows(), total=len(df)):
                start = row["start"]
                end = row["end"]
                asr = row["asr"]
                sentence = row["sentence"]
                status = row["status"]
                file_path = row["filename"]
                filename = df_sentences.loc[row["sentenceNumber"]]["file_name"]
                # filename = f"{language.upper()}" + format_int(row["sentenceNumber"]) + ".wav"
                if status == "assigned":
                    wav_path = os.path.join(output_wavs_dir, "assigned", filename)
                else:
                    wav_path = os.path.join(output_wavs_dir, "not_assigned", filename)

                outpath = trim_audio(file_path, start, end, wav_path)
                # create a row for the csv file
                myrow = {
                    "status": status,
                    "local_path": outpath,
                    "file_name": filename,
                    "unique_identifier": df_sentences.loc[row["sentenceNumber"]]["unique_identifier"],
                    "text": df_sentences.loc[row["sentenceNumber"]]["text"],
                    "sentence_length": df_sentences.loc[row["sentenceNumber"]]["sentence_length"],
                    "sentence_type": df_sentences.loc[row["sentenceNumber"]]["sentence_type"],
                }
                df_final = df_final.append(myrow, ignore_index=True)
            dfs.append(df_final)

        df_final = pd.concat(dfs)
        # keep only assigned sentences
        if assigned_only:
            # only use assigned sentences
            df_final = df_final[df_final.status == "assigned"]

        # drop duplicates
        df_final = df_final.drop_duplicates(subset=["unique_identifier"], keep="first")

        # save the csv file
        csv_path = os.path.join(output_wavs_dir, "final.csv")

        df_final.to_csv(csv_path, index=False)
        app_logger.info(f"Saved the csv file in {csv_path}")
        del whisper_model
        return output_wavs_dir, csv_path

    except Exception as e:
        app_logger.error(f"Error in aligning {filename}: {e}")
        app_logger.error(traceback.format_exc())
        shutil.rmtree(output_wavs_dir)
        del whisper_model
        return None


modelPyannote = Model.from_pretrained("pyannote/segmentation", use_auth_token="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")

pipeline = VoiceActivityDetection(segmentation=modelPyannote)
HYPER_PARAMETERS = {
    # onset/offset activation thresholds
    "onset": 0.5,
    "offset": 0.5,
    # remove speech regions shorter than that many seconds.
    "min_duration_on": 0.0,
    # fill non-speech regions shorter than that many seconds.
    "min_duration_off": 0.05,
}
pipeline.instantiate(HYPER_PARAMETERS)
padding = 0.25


lang_map = {
    "en": "english",
    "fr": "french",
    "es": "spanish",
    "de": "german",
    "it": "italian",
}

whisper_model = WhisperASR(model_size="large-v2", language="english")


def align_wavs_vad(
    job: Task, wavs_path: str, csv_path: str, language: str, start_id_regex: str, end_id_regex: str, assigned_only: bool = True
) -> Tuple[str, str]:
    whisper_model.load(language=lang_map[language])
    app_logger.info(f"wav_path: {wavs_path}")

    filenames = glob(os.path.join(wavs_path, "*.wav"))
    app_logger.info(f"Found {len(filenames)} wav files")

    temp_dir = tempfile.mkdtemp()

    # create a wavs dir in temp dir
    output_wavs_dir = os.path.join(temp_dir, "wavs")
    # no error if exists
    os.mkdir(output_wavs_dir)
    try:
        dfs = []
        for filename in filenames:
            app_logger.info(f"Processing {filename}")
            vad_path = os.path.join(temp_dir, filename + ".vad.bin")
            if os.path.exists(vad_path):
                app_logger.info(f"Detected VAD for {filename}  at {vad_path}- loading from file")
                vad = pickle.load(open(vad_path, "rb"))
            else:
                app_logger.info(f"Running VAD for {filename}")
                try:
                    vad = pipeline(filename)
                except Exception as e:
                    app_logger.error(f"Failed to run VAD for {filename}")
                    app_logger.error(e)
                    continue
                app_logger.info(f"finished VAD for {filename}")
                i = 0
                app_logger.info(f"Saving VAD for {filename}")
                with open(vad_path, "wb") as f:
                    pickle.dump(vad, f)
                app_logger.info(f"Saved VAD for {filename}")

            data = AudioSegment.from_file(filename)
            start_loc = int(re.search(start_id_regex, filename).group(1))
            end_loc = int(re.search(end_id_regex, filename).group(1))

            app_logger.info(f"start_loc: {start_loc}, end_loc: {end_loc}")

            sentences = {}
            inverseSentences = {}
            df_sentences = pd.read_csv(csv_path)
            id_int = df_sentences["unique_identifier"].apply(lambda x: int(x[2:]))
            df_sentences["id_int"] = id_int
            df_sentences.set_index("id_int", inplace=True)
            # include only ids in between start_loc and end_loc
            df_sentences = df_sentences.loc[start_loc:end_loc]

            app_logger.info(f"There are {len(df_sentences)} sentences in this range")
            for index, row in df_sentences.iterrows():
                sentenceNum = int(index)
                sentence = row["text"]
                sentences[sentenceNum] = sentence
                if sentence not in inverseSentences:
                    inverseSentences[sentence] = sentenceNum
                else:
                    tmp = sentence
                    while tmp in inverseSentences:
                        tmp += " _"
                    inverseSentences[tmp] = sentenceNum
            sentenceNumber = -1
            segments = {}
            segments_path = os.path.join(temp_dir, filename + ".segments.json")
            if os.path.exists(segments_path):
                app_logger.info(f"Detected segments for {filename}  at {segments_path}- loading from file")
                segments = json.load(open(segments_path))
            else:
                app_logger.info(f"Running ASR for {filename}")
                timeline = vad.get_timeline().support()
                for segment in tqdm(timeline):
                    start, end = list(segment)
                    start = max(0, start - padding)
                    end = min(end + padding, len(data) / 1000)
                    seg = {}
                    seg["SegmentStart"] = start
                    seg["SegmentEnd"] = end
                    outputAudio = AudioSegment.empty()
                    outputAudio += data[seg["SegmentStart"] * 1000 : seg["SegmentEnd"] * 1000]
                    # save audio to a tmp file
                    temp_file = os.path.join(temp_dir, "tmp.wav")
                    outputAudio.export(temp_file, format="wav")
                    # run ASR
                    try:
                        result = whisper_model.predict({"instances": [{"url": temp_file}]})
                        asr = result["predictions"][0]
                        seg["asr"] = asr
                    except:
                        app_logger.error(f"Failed to run ASR for {filename}")
                        seg["asr"] = ""
                        pass
                    segments[start] = seg
                # save segments
                print(f"Saving segments for {filename}")
                with open(segments_path, "w") as fout:
                    json.dump(segments, fout, indent=4)
                print(f"Saved segments for {filename}")
            print(f"Matching segments to sentences for {filename}")
            segments_list = [v for k, v in segments.items()]
            sentences_list = [v for k, v in sentences.items()]
            distances_matrix = np.ones((len(segments_list), len(sentences_list))) * 1000
            for ik in range(len(segments_list)):
                for jk, sentence in enumerate(sentences_list):
                    try:
                        distances_matrix[ik, jk] = edit_distance(segments_list[ik]["asr"], sentence) / min(len(segments_list[ik]["asr"]), len(sentence))
                    except:
                        distances_matrix[ik, jk] = np.inf

            # get the best match for each segment
            best_matches = np.argmin(distances_matrix, axis=1)
            # # make a dataframe
            columns = ["status", "filename", "sentenceNumber", "sentence", "asr", "start", "end", "ed_dist", "len_dif"]
            df = pd.DataFrame(columns=columns)
            best_matched_sentences = [sentences_list[k] for k in best_matches]

            # print the results
            for ik in range(len(segments_list)):
                asr = segments_list[ik]["asr"]
                sentence = best_matched_sentences[ik]
                ed_dist = distances_matrix[ik, best_matches[ik]]
                try:
                    len_dif = abs(len(asr) - len(sentence)) / min(len(asr), len(sentence))
                except:
                    len_dif = np.inf
                start = segments_list[ik]["SegmentStart"]
                end = segments_list[ik]["SegmentEnd"]
                sentenceNumber = inverseSentences[sentence]
                if ed_dist < 0.25 and len_dif < 0.15:
                    status = "assigned"
                else:
                    status = "not_assigned"

                row = {
                    "status": status,
                    "filename": filename,
                    "sentenceNumber": sentenceNumber,
                    "sentence": sentence,
                    "asr": asr,
                    "start": start,
                    "end": end,
                    "ed_dist": ed_dist,
                    "len_dif": len_dif,
                }
                df = df.append(row, ignore_index=True)
            # if there is inf  drop it
            df = df.replace([np.inf, -np.inf], np.nan)
            df.dropna(inplace=True)

            app_logger.info(f"Assigned {len(df[df.status=='assigned'])} segments")
            app_logger.info(f"Not assigned {len(df[df.status=='not_assigned'])} segments")

            # if there are multiple rows with same sentenceNumber take the last one and drop the rest
            df = df.sort_values(by=["sentenceNumber"])
            df = df.drop_duplicates(subset=["sentenceNumber"], keep="last")

            app_logger.info(f"Status counts for {filename}:")
            app_logger.info(df.status.value_counts())
            # df.to_csv(filename + ".csv", index=False)

            # create "assigned" and "not_assigned" folders
            os.makedirs(os.path.join(output_wavs_dir, "assigned"), exist_ok=True)
            os.makedirs(os.path.join(output_wavs_dir, "not_assigned"), exist_ok=True)

            # for each row in the dataframe if the status is assigned, create a wav file with the start and end times of the segment
            # if not assigned, create a wav file with the start and end times of the segment
            app_logger.info(f"Trimming audio for {filename}, it will be saved in {output_wavs_dir}")
            # columns should be following: local_path,file_name,unique_identifier,text,sentence_length,sentence_type
            columns = ["status", "local_path", "file_name", "unique_identifier", "text", "sentence_length", "sentence_type"]
            df_final = pd.DataFrame(columns=columns)
            for index, row in tqdm(df.iterrows(), total=len(df)):
                start = row["start"]
                end = row["end"]
                asr = row["asr"]
                sentence = row["sentence"]
                status = row["status"]
                file_path = row["filename"]
                filename = df_sentences.loc[row["sentenceNumber"]]["file_name"]
                # filename = f"{language.upper()}" + format_int(row["sentenceNumber"]) + ".wav"
                if status == "assigned":
                    wav_path = os.path.join(output_wavs_dir, "assigned", filename)
                else:
                    wav_path = os.path.join(output_wavs_dir, "not_assigned", filename)

                outpath = trim_audio(file_path, start, end, wav_path)
                # create a row for the csv file
                myrow = {
                    "status": status,
                    "local_path": outpath,
                    "file_name": filename,
                    "unique_identifier": df_sentences.loc[row["sentenceNumber"]]["unique_identifier"],
                    "text": df_sentences.loc[row["sentenceNumber"]]["text"],
                    "sentence_length": df_sentences.loc[row["sentenceNumber"]]["sentence_length"],
                    "sentence_type": df_sentences.loc[row["sentenceNumber"]]["sentence_type"],
                }
                df_final = df_final.append(myrow, ignore_index=True)
            dfs.append(df_final)

        df_final = pd.concat(dfs)
        # keep only assigned sentences
        if assigned_only:
            # only use assigned sentences
            df_final = df_final[df_final.status == "assigned"]

        # drop duplicates
        df_final = df_final.drop_duplicates(subset=["unique_identifier"], keep="first")

        # save the csv file
        csv_path = os.path.join(output_wavs_dir, "final.csv")

        df_final.to_csv(csv_path, index=False)
        app_logger.info(f"Saved the csv file in {csv_path}")
        whisper_model.unload()
        return output_wavs_dir, csv_path

    except Exception as e:
        app_logger.error(f"Error in aligning {filename}: {e}")
        app_logger.error(traceback.format_exc())
        shutil.rmtree(output_wavs_dir)
        whisper_model.unload()
        return None
