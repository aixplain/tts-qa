import json
import os
import pickle
import re

import editdistance
import numpy as np
import pandas as pd
from pyannote.audio import Model
from pyannote.audio.pipelines import VoiceActivityDetection
from pydub import AudioSegment
from tqdm import tqdm
from whisper_model import WhisperASR


def edit_distance(s1, s2):
    return editdistance.eval(s1, s2)


def format_int(i):
    return str(i).zfill(8)


# trim the audio using start end end time in secs
def trim_audio(path, start, end, out_path):
    sound = AudioSegment.from_file(path, format="wav")
    trimmed_sound = sound[start * 1000 : end * 1000]
    trimmed_sound.export(out_path, format="wav")
    return out_path


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


print("Loading Whisper model...")

whisper_model = WhisperASR(model_size="large-v2", language="french")
whisper_model.load()


batch = "batches/"
padding = 0.25

from glob import glob


filenames = glob(batch + "From*.wav")
for filename in filenames:
    print(f"Processing {filename}")
    if os.path.exists(filename + ".vad.bin"):
        print(f"Detected VAD for {filename} - loading from file")
        vad = pickle.load(open(filename + ".vad.bin", "rb"))
    else:
        print(f"Running VAD for {filename}")
        vad = pipeline(filename)
        i = 0
        print(f"Saving VAD for {filename}")
        with open(filename + ".vad.bin", "wb") as f:
            pickle.dump(vad, f)
        print(f"Saved VAD for {filename}")

    data = AudioSegment.from_file(filename)
    # read start_loc and end_loc from wav file name  using regex
    start_loc = int(re.search(r"From (\d+) -", filename).group(1))
    end_loc = int(re.search(r"- (\d+)", filename).group(1))
    print(f"start_loc: {start_loc}, end_loc: {end_loc}")

    sentences = {}
    inverseSentences = {}
    df_sentences = pd.read_csv("batches/fr - fr.csv")
    id_int = df_sentences["unique_identifier"].apply(lambda x: int(x[2:]))
    df_sentences["id_int"] = id_int
    df_sentences.set_index("id_int", inplace=True)
    # include only ids in between start_loc and end_loc
    df_sentences = df_sentences.loc[start_loc:end_loc]
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
    if os.path.exists(filename + ".segments.json"):
        print(f"Detected segments for {filename} - loading from file")
        segments = json.load(open(filename + ".segments.json"))
    else:
        print(f"Running ASR for {filename}")
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
            outputAudio.export(batch + "TMP/tmp.wav", format="wav")
            # run ASR
            try:
                result = whisper_model.predict({"instances": [{"url": batch + "TMP/tmp.wav"}]})
                asr = result["predictions"][0]
                seg["asr"] = asr
            except:
                seg["asr"] = ""
                pass
            segments[start] = seg
        # save segments
        print(f"Saving segments for {filename}")
        with open(filename + ".segments.json", "w") as fout:
            json.dump(segments, fout, indent=4)
        print(f"Saved segments for {filename}")

    print(f"Matching segments to sentences for {filename}")
    segments_list = [v for k, v in segments.items()]
    sentences_list = [v for k, v in sentences.items()]
    distances_matrix = np.ones((len(segments_list), len(sentences))) * 1000

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

    # if there are multiple rows with same sentenceNumber take the last one and drop the rest
    df = df.sort_values(by=["sentenceNumber"])
    df = df.drop_duplicates(subset=["sentenceNumber"], keep="last")

    print(f"Status counts for {filename}:")
    print(df.status.value_counts())

    # create a folder for wav files
    wav_folder = os.path.join(batch, os.path.basename(filename).replace(".wav", ""))
    if os.path.exists(wav_folder):
        print(f"Folder {wav_folder} already exists, skipping")
        continue
    os.makedirs(wav_folder, exist_ok=True)

    # create "assigned" and "not_assigned" folders
    os.makedirs(os.path.join(wav_folder, "assigned"), exist_ok=True)
    os.makedirs(os.path.join(wav_folder, "not_assigned"), exist_ok=True)

    # for each row in the dataframe if the status is assigned, create a wav file with the start and end times of the segment
    # if not assigned, create a wav file with the start and end times of the segment
    print(f"Trimming audio for {filename}, it will be saved in {wav_folder}")
    for index, row in tqdm(df.iterrows(), total=len(df)):
        start = row["start"]
        end = row["end"]
        asr = row["asr"]
        sentence = row["sentence"]
        status = row["status"]
        if status == "assigned":
            wav_path = os.path.join(wav_folder, "assigned", "FR" + format_int(row["sentenceNumber"]) + ".wav")
        else:
            wav_path = os.path.join(wav_folder, "not_assigned", "FR" + format_int(row["sentenceNumber"]) + ".wav")

        outpath = trim_audio(filename, start, end, wav_path)
