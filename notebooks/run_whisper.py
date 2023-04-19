#!/usr/bin/env python

import json
import os
from glob import glob
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from src.features.whisper_model import WhisperASR
from src.logger import root_logger
from src.paths import paths


logger = root_logger.getChild(__name__)


if __name__ == "__main__":
    files = glob(str(paths.PROCESSED_DATASETS_DIR.resolve()) + "/*.csv")
    for file in files:
        df_trans = pd.read_csv(file, index_col=None)
        language = df_trans["language"][0]

        for model_size in ["tiny", "base", "small", "medium"]:
            if language == "English":
                model_size = model_size + ".en"

            logger.info(f"Loading model {model_size} for {language}")
            model = WhisperASR(model_size=model_size, language=language)
            model.load()
            save_dir = paths.FEATURES_DATASETS_DIR / f"whisper_{language}_{model_size}"
            if not save_dir.exists():
                save_dir.mkdir()

            # TQDM DF
            for i, row in tqdm(df_trans.iterrows(), total=df_trans.shape[0]):
                filepath = row["filename"]
                filepath = Path(filepath)

                filename = filepath.name
                save_path = str((save_dir / filename).resolve()) + ".json"
                if os.path.exists(save_path):
                    continue
                try:
                    request = {"instances": [{"url": row["filename"]}]}
                    response = model.predict(request)
                except:
                    logger.error(f"Error processing {filepath}")
                    continue

                with open(save_path, "w") as f:
                    json.dump(response, f, ensure_ascii=False)
