import os


os.environ["TEAM_API_KEY"] = "2b3632015768088470d98273667a627e0e5a7d2d659ec3cf4b06bfa368eaa1a8"
import time

import librosa
import pandas as pd
import soundfile as sf
from aixplain.factories.model_factory import ModelFactory
from pyannote.audio import Model
from pyannote.audio.pipelines import VoiceActivityDetection
from pydub import AudioSegment
from pydub.utils import mediainfo


modelPyannote = Model.from_pretrained("pyannote/segmentation", use_auth_token="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")
vad_pipeline = VoiceActivityDetection(segmentation=modelPyannote)
HYPER_PARAMETERS = {
    # onset/offset activation thresholds
    "onset": 0.5,
    "offset": 0.5,
    # remove speech regions shorter than that many seconds.
    "min_duration_on": 0.0,
    # fill non-speech regions shorter than that many seconds.
    "min_duration_off": 0.05,
}
vad_pipeline.instantiate(HYPER_PARAMETERS)


api_keys_azure = {
    "en": {
        "api_key": "2b3632015768088470d98273667a627e0e5a7d2d659ec3cf4b06bfa368eaa1a8",
        "id": "62fab6ecb39cca09ca5bc378",
        "model": ModelFactory.create_asset_from_id("62fab6ecb39cca09ca5bc378"),
    },
    "es": {
        "api_key": "2b3632015768088470d98273667a627e0e5a7d2d659ec3cf4b06bfa368eaa1a8",
        "id": "62fab6ecb39cca09ca5bc375",
        "model": ModelFactory.create_asset_from_id("62fab6ecb39cca09ca5bc375"),
    },
    "fr": {
        "api_key": "2b3632015768088470d98273667a627e0e5a7d2d659ec3cf4b06bfa368eaa1a8",
        "id": "62fab6ecb39cca09ca5bc389",
        "model": ModelFactory.create_asset_from_id("62fab6ecb39cca09ca5bc389"),
    },
    "it": {
        "api_key": "2b3632015768088470d98273667a627e0e5a7d2d659ec3cf4b06bfa368eaa1a8",
        "id": "62fab6ecb39cca09ca5bc353",
        "model": ModelFactory.create_asset_from_id("62fab6ecb39cca09ca5bc353"),
    },
    "de": {
        "api_key": "2b3632015768088470d98273667a627e0e5a7d2d659ec3cf4b06bfa368eaa1a8",
        "id": "62fab6ecb39cca09ca5bc334",
        "model": ModelFactory.create_asset_from_id("62fab6ecb39cca09ca5bc334"),
    },
}


api_keys_aws = {
    "en": {
        "api_key": "2b3632015768088470d98273667a627e0e5a7d2d659ec3cf4b06bfa368eaa1a8",
        "id": "60ddef908d38c51c5885dd1e",
        "model": ModelFactory.create_asset_from_id("60ddef908d38c51c5885dd1e"),
    },
    "es": {
        "api_key": "2b3632015768088470d98273667a627e0e5a7d2d659ec3cf4b06bfa368eaa1a8",
        "id": "60ddefd68d38c51c588608c6",
        "model": ModelFactory.create_asset_from_id("60ddefd68d38c51c588608c6"),
    },
    "fr": {
        "api_key": "2b3632015768088470d98273667a627e0e5a7d2d659ec3cf4b06bfa368eaa1a8",
        "id": "60ddefde8d38c51c58860d8d",
        "model": ModelFactory.create_asset_from_id("60ddefde8d38c51c58860d8d"),
    },
    "it": {
        "api_key": "2b3632015768088470d98273667a627e0e5a7d2d659ec3cf4b06bfa368eaa1a8",
        "id": "60ddefa38d38c51c5885e979",
        "model": ModelFactory.create_asset_from_id("60ddefa38d38c51c5885e979"),
    },
    "de": {
        "api_key": "2b3632015768088470d98273667a627e0e5a7d2d659ec3cf4b06bfa368eaa1a8",
        "id": "60ddefc48d38c51c5885fd69",
        "model": ModelFactory.create_asset_from_id("60ddefc48d38c51c5885fd69"),
    },
}


def asr_and_trim_azure(s3path, language="en"):
    model = api_keys_azure[language]["model"]
    response = {}
    count = 0
    while count < 3 and response == {}:
        try:
            model_response = model.run(data=s3path, name=f"ASR model ({language})")
            if model_response["status"] == "SUCCESS":
                details = model_response["details"]

                df_details = pd.DataFrame(details)
                df_details.head()

                df_details["pauses"] = df_details["start_time"].shift(-1) - df_details["end_time"]
                df_details["pauses"] = df_details["pauses"].fillna(0)
                transcription = " ".join(df_details["text"])

                start_time = df_details.loc[0, "start_time"]
                end_time = df_details.loc[len(df_details) - 1, "end_time"]
                audio_duration = end_time - start_time

                response["asr_text"] = transcription
                response["trim_start"] = start_time
                response["trim_end"] = end_time
                response["trimmed_audio_duration"] = audio_duration
                response["longest_pause"] = df_details["pauses"].max()
                return response
        except Exception as e:
            print(e)
            count += 1
            time.sleep(1)
            continue
    return {
        "asr_text": "",
        "trim_start": 0,
        "trim_end": 0,
        "trimmed_audio_duration": 0,
        "longest_pause": 0,
    }


def trim_only(path):
    vad = vad_pipeline(path)
    timeline = vad.get_timeline().support()
    longest_pause = 0
    previous_end = 0
    for i, segment in enumerate(timeline):
        start, end = list(segment)
        if i == 0:
            start_time = start
        if i == len(timeline) - 1:
            end_time = end
        if i > 0:
            pause = start - previous_end
            if pause > longest_pause:
                longest_pause = pause
        previous_end = end
    audio_duration = end_time - start_time
    return {
        "trim_start": start_time,
        "trim_end": end_time,
        "trimmed_audio_duration": audio_duration,
        "longest_pause": longest_pause,
    }


def asr_and_trim_aws(s3path, language="en"):
    model = api_keys_aws[language]["model"]
    response = {}
    count = 0
    while count < 3 and response == {}:
        try:
            model_response = model.run(data=s3path, name=f"ASR model ({language})")
            if model_response["status"] == "SUCCESS":
                details = model_response["details"]["segments"]

                df_details = pd.DataFrame(details)
                df_details.dropna(inplace=True)

                df_details["pauses"] = df_details["start_time"].shift(-1) - df_details["end_time"]
                df_details["pauses"] = df_details["pauses"].fillna(0)
                transcription = " ".join(df_details["text"])

                start_time = df_details.loc[0, "start_time"]
                end_time = df_details.loc[len(df_details) - 1, "end_time"]
                audio_duration = end_time - start_time

                response["asr_text"] = transcription
                response["trim_start"] = start_time
                response["trim_end"] = end_time
                response["trimmed_audio_duration"] = audio_duration
                response["longest_pause"] = df_details["pauses"].max()
                return response
        except Exception as e:
            print(e)
            count += 1
            time.sleep(1)
            continue
    return {
        "asr_text": "",
        "trim_start": 0,
        "trim_end": 0,
        "trimmed_audio_duration": 0,
        "longest_pause": 0,
    }


def evaluate_audio(path):
    response = {}
    info = mediainfo(path)
    sound = AudioSegment.from_file(path)
    response["Filepath"] = path
    response["file_type"] = os.path.splitext(path)[1]
    response["file_name"] = os.path.basename(path)
    response["sampling_rate"] = int(info["sample_rate"])
    response["sample_format"] = info["sample_fmt"]
    response["format"] = info["format_name"]
    response["n_channel"] = int(info["channels"])
    response["bit_rate"] = int(info["bit_rate"])
    response["codec"] = info["codec_name"]
    response["peak_volume_db"] = sound.max_dBFS
    response["duration"] = float(info["duration"])
    response["size"] = os.path.getsize(path)
    response["is_wav"] = True if info["format_name"] == "wav" else False
    response["is_mono"] = True if info["channels"] == "1" else False
    response["isPCM"] = True if response["codec"] == "pcm_s16le" else False
    response["is_16bit"] = True if response["sample_format"] == "s16" else False
    response["is_88khz"] = True if response["sampling_rate"] == 88000 else False

    is_valid = False
    if (
        response["is_wav"]
        and response["is_mono"]
        and response["is_16bit"]
        and response["isPCM"]
        and response["is_88khz"]
        and response["peak_volume_db"] >= -6
        and response["peak_volume_db"] <= -3
        and response["duration"] > 0
    ):
        is_valid = True
    response["isValid"] = is_valid
    return response


#  convert the sampling rate to 88kHz
def convert_to_88k(path, out_path):
    y, sr = librosa.load(path, sr=None)
    y_88k = librosa.resample(y, orig_sr=sr, target_sr=88000)
    sf.write(out_path, y_88k, 88000)
    return out_path


# normalize the audio peak_volume_db to be between -6 and -3 db
def normalize_audio(path, out_path):
    sound = AudioSegment.from_file(path, format="wav")
    if sound.max_dBFS > -3:
        normalized_sound = sound - (sound.max_dBFS + 3.5)
    elif sound.max_dBFS < -6:
        normalized_sound = sound + (-5.5 - sound.max_dBFS)
    else:
        normalized_sound = sound
    normalized_sound.export(out_path, format="wav")
    return out_path


# trim the audio using start end end time in secs
def trim_audio(path, start, end, out_path):
    sound = AudioSegment.from_file(path, format="wav")
    # make sure that the start and end are in between the audio duration
    start = max(0, start)
    end = min(end, len(sound) / 1000)
    trimmed_sound = sound[start * 1000 : end * 1000]
    trimmed_sound.export(out_path, format="wav")
    return out_path


# convert the audio to mono
def convert_to_mono(path, out_path):
    sound = AudioSegment.from_file(path, format="wav")
    mono_sound = sound.set_channels(1)
    mono_sound.export(out_path, format="wav")
    return out_path


def convert_to_s16le(path, out_path):
    sound = AudioSegment.from_file(path, format="wav")
    s16le_sound = sound.set_sample_width(2)
    s16le_sound.export(out_path, format="wav")
    return out_path
