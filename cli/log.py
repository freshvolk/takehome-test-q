import logging

NC = "\033[0m"
PURPLE = "\033[0;35m"
CYAN = "\033[0;36m"
YELLOW = "\033[0;33m"
RED = "\033[0;31m"


class _Fmt(logging.Formatter):
    LEVELS = {
        logging.INFO: f"{PURPLE}[CLI]{NC} {CYAN}[INFO]{NC}",
        logging.WARNING: f"{PURPLE}[CLI]{NC} {YELLOW}[WARN]{NC}",
        logging.ERROR: f"{PURPLE}[CLI]{NC} {RED}[ERROR]{NC}",
    }

    def format(self, record):
        return f"{self.LEVELS.get(record.levelno, f'{PURPLE}[CLI]{NC}')} {record.getMessage()}"


log = logging.getLogger("cli")
log.addHandler(logging.StreamHandler())
log.handlers[0].setFormatter(_Fmt())
log.setLevel(logging.INFO)
