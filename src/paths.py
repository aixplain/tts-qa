from datetime import datetime
from pathlib import Path


now_str = datetime.strftime(datetime.now(), "%Y-%m-%d_%H-%M-%S")


class Paths:
    PROJECT_ROOT_DIR = Path(__file__).parent.parent
    DATASETS_DIR: Path = Path("/data")
    LOCAL_BUCKET_DIR: Path = DATASETS_DIR / "tts-qa"
    OUTPUTS_DIR: Path = PROJECT_ROOT_DIR / "outputs"
    REPORTS_DIR: Path = PROJECT_ROOT_DIR / "reports"
    SRC_DIR: Path = PROJECT_ROOT_DIR / "src"
    TESTS_DIR: Path = PROJECT_ROOT_DIR / "tests"

    RAW_DATASETS_DIR: Path = DATASETS_DIR / "raw"
    PROCESSED_DATASETS_DIR: Path = DATASETS_DIR / "processed"
    EXTERNAL_DATASETS_DIR: Path = DATASETS_DIR / "external"
    FEATURES_DATASETS_DIR: Path = DATASETS_DIR / "features"

    DATASET_SCRIPTS_DIR: Path = SRC_DIR / "scripts"

    MODELS_DIR: Path = OUTPUTS_DIR / "models"
    PREDICTIONS_DIR: Path = OUTPUTS_DIR / "predictions"

    FIGURES_DIR: Path = REPORTS_DIR / "figures"

    PIPELINE_PATH: Path = MODELS_DIR / "pipeline.pkl"
    BEST_MODEL_PATH: Path = MODELS_DIR / "model_best.pkl"

    OUTPUT_DIR_PATTERN: str = f"{OUTPUTS_DIR}/" + "{run_type}/{model_name}/{run_tag}/" + now_str


paths = Paths()
