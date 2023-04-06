import os
import sys
import time

# do the above process in a thread pool
from concurrent.futures import ThreadPoolExecutor

import matplotlib.pyplot as plt
import pandas as pd
from aixtend.factories.model_factory import ModelFactory
from pydub import AudioSegment
from pydub.utils import mediainfo
from tqdm import tqdm


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


def asr_and_trim(s3Path, language="en"):
    model = api_keys[language]["model"]
    response = {}
    try:
        model_response = model.run(data=s3Path, name=f"ASR model ({language})")
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

            response["asr_transcription"] = transcription
            response["trim_start_time"] = start_time
            response["trim_end_time"] = end_time
            response["trimmed_audio_duration"] = audio_duration
            response["longest_pause"] = df_details["pauses"].max()

    except Exception as e:
        response = {
            "message": "Failed",
            "error": str(e),
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
    response["codec"] = info["codec_name"]
    response["is_wav"] = True if info["format_name"] == "wav" else False
    response["is_mono"] = True if info["channels"] == "1" else False
    response["is_PCM"] = True if response["codec"] == "pcm_s16le" else False
    response["is_16bit"] = True if response["sample_format"] == "s16" else False
    response["is_88khz"] = True if response["sampling_rate"] == 88000 else False
    response["peak_volume_db"] = sound.max_dBFS
    response["duration"] = float(info["duration"])

    is_valid = False
    if (
        response["is_wav"]
        and response["is_mono"]
        and response["is_16bit"]
        and response["is_PCM"]
        and response["is_88khz"]
        and response["peak_volume_db"] >= -6
        and response["peak_volume_db"] <= -3
        and response["duration"] > 0
    ):
        is_valid = True
    response["is_valid"] = is_valid
    return response
