import os
from ._timeparse import timeparse
from ._async import as_deferred, as_future, EndCall


def ensure_dir_exists(filename: str) -> None:
    d = os.path.dirname(filename)
    os.makedirs(d, exist_ok=True)