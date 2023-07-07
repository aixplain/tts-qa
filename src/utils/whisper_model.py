import os
import tempfile
import traceback
import urllib.request
from typing import Dict
from uuid import uuid4

import whisper
import whisper_timestamped as whisperts

from src.logger import root_logger


app_logger = root_logger.getChild("whisper-asr")

MODEL_DIR = os.getenv("MODEL_DIR", "/mnt/models")
MODEL_NAME = os.getenv("MODEL_NAME", "whisper_model")

lang_map = {
    "en": "english",
    "fr": "french",
    "es": "spanish",
    "de": "german",
    "it": "italian",
}

inverse_lang_map = {v: k for k, v in lang_map.items()}


class WhisperTimestampedASR:
    def __init__(self, model_size="tiny", language="english", device="cpu"):
        app_logger.info(f"Initializeing Whisper model: {model_size}")
        self.model = None
        self.ready = False
        self.device = device
        self.transcribe_options = dict(detect_disfluencies=False, vad=True, verbose=None, language=inverse_lang_map[language])
        self.model_size = model_size

    def load(self, language: str = None):
        app_logger.info(f"Loading Whisper model: {self.model_size}")
        if self.ready:
            app_logger.warning("Whisper model already loaded need to unload first")
            return True
        if language:
            app_logger.info(f"Setting language to {language}")
            self.transcribe_options["language"] = language
        self.model = whisperts.load_model(self.model_size, device=self.device)
        self.ready = True
        app_logger.info(f"Whisper model loaded")

    def unload(self):
        self.model = None
        self.ready = False
        app_logger.info(f"Whisper model unloaded")

    def get_file_from_url(self, url, tempdir):
        _, extension = os.path.splitext(url)
        extension = extension[1:]
        extension = extension.split("?")[0]
        input_path = os.path.join(tempdir, f"{str(uuid4())}.{extension}")
        urllib.request.urlretrieve(url, input_path)
        return input_path

    def predict(self, request: Dict) -> Dict:
        try:
            transcriptions = []
            segments = []
            inputs = request["instances"]
            with tempfile.TemporaryDirectory(prefix="whisper-asr-") as tempdir:
                for request in inputs:
                    # check if url is s3 link or local
                    if request["url"].startswith("s3://"):
                        audio_file = self.get_file_from_url(request["url"], tempdir)
                    else:
                        audio_file = request["url"]
                    audio = whisperts.load_audio(audio_file)
                    results = whisperts.transcribe(self.model, audio, **self.transcribe_options)
                    text = results["text"]
                    segments = results["segments"]
                    # remove spaces at the beginning and end of the string
                    text = text.strip()
                    transcriptions.append(text)
                    segments.append(segments)

            return {"predictions": transcriptions, "segments": segments}
        except ValueError as e:
            print(traceback.format_exc())
            raise ValueError(f"Failed to process request: {e}")


class WhisperASR:
    def __init__(self, model_size="tiny", language="English"):
        app_logger.info(f"Initializeing Whisper model: {model_size}")
        self.model = None
        self.ready = False
        options = dict(language=language)
        self.transcribe_options = dict(task="transcribe", **options)
        self.model_size = model_size

    def load(self, language: str = None):
        app_logger.info(f"Loading Whisper model: {self.model_size}")
        if self.ready:
            app_logger.warning("Whisper model already loaded need to unload first")
            return True
        if language:
            app_logger.info(f"Setting language to {language}")
            self.transcribe_options["language"] = language
        model_path = os.path.join(MODEL_DIR, MODEL_NAME)
        self.model = whisper.load_model(self.model_size, download_root=model_path)
        self.ready = True
        app_logger.info(f"Whisper model loaded")

    def unload(self):
        self.model = None
        self.ready = False
        app_logger.info(f"Whisper model unloaded")

    def get_file_from_url(self, url, tempdir):
        _, extension = os.path.splitext(url)
        extension = extension[1:]
        extension = extension.split("?")[0]
        input_path = os.path.join(tempdir, f"{str(uuid4())}.{extension}")
        urllib.request.urlretrieve(url, input_path)
        return input_path

    def predict(self, request: Dict) -> Dict:
        try:
            transcriptions = []
            inputs = request["instances"]
            with tempfile.TemporaryDirectory(prefix="whisper-asr-") as tempdir:
                for request in inputs:
                    # check if url is s3 link or local
                    if request["url"].startswith("s3://"):
                        audio_file = self.get_file_from_url(request["url"], tempdir)
                    else:
                        audio_file = request["url"]

                    transcriptions.append(self.model.transcribe(audio_file, **self.transcribe_options)["text"])

            return {"predictions": transcriptions}
        except ValueError as e:
            print(traceback.format_exc())
            raise ValueError(f"Failed to process request: {e}")
