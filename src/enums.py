# We use this file to define all the enums used in the project

# from enum import Enum
# Example:
# class Color(Enum):
#     RED = 1
#     GREEN = 2
#     BLUE = 3

from enum import Enum


class RunType(Enum):
    DATASET_ANALYSIS = "dataset_analysis"
    EVALUATION = "evaluation"
    TRAINING = "training"


class DatasetType(Enum):
    TRAIN = "train"
    TEST = "test"
    VALIDATION = "validation"
