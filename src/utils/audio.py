import os
import time

import librosa
import pandas as pd
import soundfile as sf
from aixtend.factories.model_factory import ModelFactory
from pydub import AudioSegment
from pydub.utils import mediainfo


api_keys = {
    "en": {
        "api_key": "66c4c7ad2eb5620207e8ee6a3a5799d5100c9798d8d64206965ca519db5f5f24",
        "id": "62fab6ecb39cca09ca5bc378",
        "model": ModelFactory.create_asset_from_id("62fab6ecb39cca09ca5bc378"),
    },
    "es": {
        "api_key": "66c4c7ad2eb5620207e8ee6a3a5799d5100c9798d8d64206965ca519db5f5f24",
        "id": "62fab6ecb39cca09ca5bc375",
        "model": ModelFactory.create_asset_from_id("62fab6ecb39cca09ca5bc375"),
    },
    "fr": {
        "api_key": "66c4c7ad2eb5620207e8ee6a3a5799d5100c9798d8d64206965ca519db5f5f24",
        "id": "62fab6ecb39cca09ca5bc389",
        "model": ModelFactory.create_asset_from_id("62fab6ecb39cca09ca5bc389"),
    },
    "it": {
        "api_key": "66c4c7ad2eb5620207e8ee6a3a5799d5100c9798d8d64206965ca519db5f5f24",
        "id": "62fab6ecb39cca09ca5bc353",
        "model": ModelFactory.create_asset_from_id("62fab6ecb39cca09ca5bc353"),
    },
    "de": {
        "api_key": "66c4c7ad2eb5620207e8ee6a3a5799d5100c9798d8d64206965ca519db5f5f24",
        "id": "62fab6ecb39cca09ca5bc334",
        "model": ModelFactory.create_asset_from_id("62fab6ecb39cca09ca5bc334"),
    },
}


def asr_and_trim(s3path, language="en"):
    model = api_keys[language]["model"]
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
    normalized_sound.export(out_path, format="wav")
    return out_path


# trim the audio using start end end time in secs
def trim_audio(path, start, end, out_path):
    sound = AudioSegment.from_file(path, format="wav")
    trimmed_sound = sound[start * 1000 : end * 1000]
    trimmed_sound.export(out_path, format="wav")
    return out_path


# convert the audio to mono
def convert_to_mono(path, out_path):
    sound = AudioSegment.from_file(path, format="wav")
    mono_sound = sound.set_channels(1)
    mono_sound.export(out_path, format="wav")
    return out_path
