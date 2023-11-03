import os

from dotenv import find_dotenv, load_dotenv

from src.paths import paths


load_dotenv(find_dotenv(paths.PROJECT_ROOT_DIR / "vars.env"), override=True)

import os
import tempfile
import time
from copy import deepcopy

import librosa
import numpy as np
import pandas as pd
import scipy.io.wavfile as wav
import scipy.signal as signal
import soundfile as sf
import torch
from aixplain.factories.model_factory import ModelFactory
from pyannote.audio import Model
from pyannote.audio.pipelines import VoiceActivityDetection
from pydub import AudioSegment
from pydub.utils import mediainfo


torch.set_num_threads(1)


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
    # for timelines that has diff lover than 0.2 sec remove segment
    timeline_temp = [segment for segment in timeline if list(segment)[1] - list(segment)[0] > 0.25]
    if len(timeline_temp) > 0:
        timeline = timeline_temp
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
    try:
        audio_duration = end_time - start_time
    except:
        print(f"Error in audio duration calculation, do not triming file {path}")
        # get audio dur in secs
        audio_duration = librosa.get_duration(filename=path)
        end_time = audio_duration
        start_time = 0

    return {
        "trim_start": start_time,
        "trim_end": end_time,
        "trimmed_audio_duration": audio_duration,
        "longest_pause": longest_pause,
    }


def asr_aws(s3path, language="en"):
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

                transcription = " ".join(df_details["text"])
                return transcription
        except Exception as e:
            print(e)
            count += 1
            time.sleep(1)
            continue
    return ""


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

                start_time = df_details["start_time"].values[0]
                end_time = df_details["end_time"].values[-1]
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
    start_time = max(0, start)
    end_time = min(end, len(sound) / 1000)
    trimmed_sound = sound[start_time * 1000 : end_time * 1000]
    trimmed_sound.export(out_path, format="wav")
    return out_path, start_time, end_time


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


class CustomVAD:
    SAMPLING_RATE = 16000
    PADDING = 0.025
    ENERGY_THRESHOLD = 500000
    WINDOW_SIZE = 0.02

    def __init__(self, pyannote_model_path, silero_model_path, hyper_parameters=None):
        self.pyannote_model = Model.from_pretrained(pyannote_model_path, use_auth_token="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")
        self.silero_model, self.silero_utils = torch.hub.load(repo_or_dir=silero_model_path, model="silero_vad", force_reload=True, onnx=False)
        self.pipeline = VoiceActivityDetection(segmentation=self.pyannote_model)
        if hyper_parameters is None:
            hyper_parameters = {"onset": 0.5, "offset": 0.5, "min_duration_on": 0.0, "min_duration_off": 0.05}
        self.pipeline.instantiate(hyper_parameters)

        (self.get_speech_timestamps, self.save_audio, self.read_audio, self.VADIterator, self.collect_chunks) = self.silero_utils

    @staticmethod
    def pad(waveform, segment):
        start, end = segment
        start = max(0, start - CustomVAD.PADDING)
        end = min(len(waveform) / CustomVAD.SAMPLING_RATE, end + CustomVAD.PADDING)
        return start, end

    def run_pyannote_vad(self, file):
        vad_segments = self.pipeline(file)
        pyannote_timeline = vad_segments.get_timeline().support()
        response_timeline = [(segment.start, segment.end) for segment in pyannote_timeline]
        # get start of first and end of last
        if len(response_timeline) > 0:
            start = response_timeline[0][0]
            end = response_timeline[-1][1]
        else:
            start = 0
            end = 0
        response_timeline = (start, end)
        return response_timeline

    def run_silero_vad(self, file):
        wav = self.read_audio(file, sampling_rate=CustomVAD.SAMPLING_RATE)
        silero_timeline = self.get_speech_timestamps(wav, self.silero_model, sampling_rate=CustomVAD.SAMPLING_RATE)
        silero_timeline = [(segment["start"] / CustomVAD.SAMPLING_RATE, segment["end"] / CustomVAD.SAMPLING_RATE) for segment in silero_timeline]
        # get start of first and end of last
        if len(silero_timeline) > 0:
            start = silero_timeline[0][0]
            end = silero_timeline[-1][1]
        else:
            start = 0
            end = 0
        silero_timeline = (start, end)
        return silero_timeline

    def my_custom_vad(self, pyannote_segment, silero_segment, waveform):
        merged_timeline = []
        # Your logic for merging or comparing pyannote and silero timelines
        pyannote_start, pyannote_end = list(deepcopy(pyannote_segment))
        silero_start, silero_end = list(deepcopy(silero_segment))

        # If the segments are close enough, merge them
        if abs(pyannote_start - silero_start) < 0.05:
            merged_start = min(pyannote_start, silero_start)
        else:
            # Divide the segment into smaller windows and check energy
            start_start = min(pyannote_start, silero_start)
            start_end = max(pyannote_start, silero_start)
            merged_timeline = []
            merged_start = start_end
            num_windows = int((start_end - start_start) / CustomVAD.WINDOW_SIZE)
            for i in range(num_windows):
                window_start = int((start_start + i * CustomVAD.WINDOW_SIZE) * CustomVAD.SAMPLING_RATE)
                window_end = int(window_start + CustomVAD.WINDOW_SIZE * CustomVAD.SAMPLING_RATE)
                window_samples = waveform[window_start:window_end]
                window_energy = np.sum(window_samples**2) / len(window_samples)

                if window_energy > CustomVAD.ENERGY_THRESHOLD:
                    merged_timeline.append((start_start + i * CustomVAD.WINDOW_SIZE, start_start + (i + 1) * CustomVAD.WINDOW_SIZE, window_energy))
            if len(merged_timeline) > 0:
                merged_start = merged_timeline[0][0]

        if abs(pyannote_end - silero_end) < 0.05:
            merged_end = max(pyannote_end, silero_end)
        else:
            end_start = min(pyannote_end, silero_end)
            end_end = max(pyannote_end, silero_end)
            merged_timeline = []
            merged_end = end_start
            num_windows = int((end_end - end_start) / CustomVAD.WINDOW_SIZE)
            for i in range(num_windows):
                window_start = int((end_start + i * CustomVAD.WINDOW_SIZE) * CustomVAD.SAMPLING_RATE)
                window_end = int(window_start + CustomVAD.WINDOW_SIZE * CustomVAD.SAMPLING_RATE)
                window_samples = waveform[window_start:window_end]
                window_energy = np.sum(window_samples**2) / len(window_samples)

                if window_energy > CustomVAD.ENERGY_THRESHOLD:
                    merged_timeline.append((end_start + i * CustomVAD.WINDOW_SIZE, end_start + (i + 1) * CustomVAD.WINDOW_SIZE, window_energy))
            if len(merged_timeline) > 0:
                merged_end = merged_timeline[-1][1]

        custom_segment = (merged_start, merged_end)

        return custom_segment

    def process_file(self, file):
        audio = AudioSegment.from_file(file, format="wav")
        waveform = np.array(audio.get_array_of_samples())
        original_sampling_rate = audio.frame_rate
        resampled_waveform = signal.resample(waveform, int(len(waveform) * CustomVAD.SAMPLING_RATE / original_sampling_rate))
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_wav_file = os.path.join(temp_dir, "temp_audio.wav")
            wav.write(temp_wav_file, CustomVAD.SAMPLING_RATE, resampled_waveform.astype("int16"))
            pyannote_segment = self.run_pyannote_vad(file)
            silero_segment = self.run_silero_vad(file)
        print(pyannote_segment, silero_segment)
        pyannote_segment = self.pad(resampled_waveform, pyannote_segment)
        silero_segment = self.pad(resampled_waveform, silero_segment)

        custom_segment = self.my_custom_vad(pyannote_segment, silero_segment, resampled_waveform)
        custom_segment = self.pad(resampled_waveform, custom_segment)
        response = {
            "resampled_waveform": resampled_waveform,
            "pyannote_segment": pyannote_segment,
            "silero_segment": silero_segment,
            "custom_segment": custom_segment,
        }
        return response
