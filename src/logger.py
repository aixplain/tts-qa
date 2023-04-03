import logging
import os
import warnings

import click


handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(filename)s:%(lineno)d %(message)s", "%m-%d %H:%M:%S")
handler.setFormatter(formatter)
logging.addLevelName(logging.DEBUG, click.style(str(logging.getLevelName(logging.DEBUG)), fg="cyan"))
logging.addLevelName(logging.INFO, click.style(str(logging.getLevelName(logging.INFO)), fg="green"))
logging.addLevelName(logging.WARNING, click.style(str(logging.getLevelName(logging.WARNING)), fg="yellow"))
logging.addLevelName(logging.ERROR, click.style(str(logging.getLevelName(logging.ERROR)), fg="red"))
logging.addLevelName(logging.CRITICAL, click.style(str(logging.getLevelName(logging.CRITICAL)), fg="bright_red"))
logging.basicConfig(handlers=[handler])
logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("urllib3.util.retry").setLevel(logging.WARNING)
root_logger = logging.getLogger()
root_logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.simplefilter(action="ignore", category=UserWarning)
