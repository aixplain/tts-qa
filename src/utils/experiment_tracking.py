import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import wandb
from dotenv import load_dotenv

from src.enums import RunType
from src.logger import root_logger


log = root_logger.getChild("utils")
# we read the WANDB_API_KEY from the secrets.env file
load_dotenv("secrets.env")
# and the WANDB_PROJECT and WANDB_ENTITY from the vars.env file
load_dotenv("vars.env")


root_path = Path(__file__).parent.parent


with open(root_path / "models" / "configs" / "sweep_config.json") as f:
    sweep_config = json.load(f)


def init_wandb_run(
    model_name: str,
    run_type: RunType,
    run_tag: str,
    run_dir: Path = None,
    collaborator: str = os.getlogin(),
    existing_wandb_run_id: str = None,
    config: dict = None,
) -> str:
    # with an existing wandb run id, we resume the run
    if existing_wandb_run_id:
        resume_wandb_run(existing_wandb_run_id)
        return existing_wandb_run_id

    # get variables from the environment
    wandb_project, wandb_entity = get_wandb_variables()
    # skip logging to wandb if the variables are not set
    if not wandb_project or not wandb_entity:
        log.warning("Skipping W&B logging.")
        return None

    # create the run and group names
    run_type = RunType(run_type)
    group_name, run_name = create_wandb_run_and_group_names(
        run_type=run_type,
        model_name=model_name,
        run_tag=run_tag,
        collaborator=collaborator,
    )

    # initialize the run
    log.info("Initializing new W&B run")
    wandb_run = wandb.init(
        entity=wandb_entity,
        project=wandb_project,
        group=group_name,
        job_type=run_type.value,
        name=run_name,
        resume="allow",
        config=config,
    )

    # if the run dir is not None, we save the run id to the run dir for easier resuming later
    if run_dir:
        run_dir = Path(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        with open(run_dir / "wandb_run_id", "w") as f:
            f.write(wandb_run.id)

    log.info(f"W&B run initialized: {wandb_run.id=}, {wandb_run.name=}")
    return wandb_run.id


def init_wandb_sweep() -> str:
    # get variables from the environment
    wandb_project, wandb_entity = get_wandb_variables()

    sweep_id = wandb.sweep(sweep=sweep_config, project=wandb_project, entity=wandb_entity)
    return sweep_id


def create_wandb_run_and_group_names(
    run_type: RunType,
    model_name: str,
    run_tag: str,
    collaborator: str = os.getlogin(),
) -> Tuple[str, str]:
    # if the tag is a model path, use the file stem
    if model_name and Path(model_name).exists():
        model_name = Path(model_name).stem

    log.info(f"Creating W&B run and group names for {run_type=}, {model_name=}, {collaborator=}, {run_tag=}")
    run_type_str = RunType(run_type).value
    group_name = "-".join([collaborator, run_tag])
    run_name = "-".join([run_type_str, model_name, datetime.now().strftime("%Y%m%d-%H%M%S")])
    return group_name, run_name


def resume_wandb_run(wandb_run_id: str) -> None:
    log.info(f"Resuming W&B run {wandb_run_id}")
    wandb_project = os.environ.get("WANDB_PROJECT", None)
    wandb_entity = os.environ.get("WANDB_ENTITY", None)
    wandb.init(id=wandb_run_id, project=wandb_project, entity=wandb_entity)


def get_wandb_variables() -> Tuple[Optional[str], Optional[str]]:
    if os.environ.get("WANDB_DISABLED", False):
        log.warning("W&B logging is disabled as WANDB_DISABLED is set (run `unset WANDB_DISABLED` to re-enable)")
        return None, None

    if not os.environ.get("WANDB_API_KEY"):
        log.warning("WANDB_API_KEY not found in ENV. Make sure you have a secrets.env files with a value for it if you want to log to W&B.")

    wandb_project = os.environ.get("WANDB_PROJECT", None)
    if not wandb_project:
        log.warning("WANDB_PROJECT not found in ENV. Make sure you have a vars.env files with a value for it if you want to log to W&B.")

    wandb_entity = os.environ.get("WANDB_ENTITY", None)
    if not wandb_entity:
        log.warning("WANDB_ENTITY not found in ENV. Make sure you have a vars.env files with a value for it if you want to log to W&B.")

    return wandb_project, wandb_entity
