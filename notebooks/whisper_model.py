import os
import tempfile
import traceback
import urllib.request
from typing import Dict
from uuid import uuid4

import whisper


MODEL_DIR = os.getenv("MODEL_DIR", "/mnt/models")
MODEL_NAME = os.getenv("MODEL_NAME", "whisper_model")


class WhisperASR:
    def __init__(self, model_size="tiny", language="English"):
        self.model = None
        self.ready = False
        options = dict(language=language)
        self.transcribe_options = dict(task="transcribe", **options)
        self.model_size = model_size

    def load(self):
        model_path = os.path.join(MODEL_DIR, MODEL_NAME)
        self.model = whisper.load_model(self.model_size, download_root=model_path)
        self.ready = True

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
