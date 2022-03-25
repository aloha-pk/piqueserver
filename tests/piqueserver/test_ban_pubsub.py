import asyncio
from typing import Any, Dict
from unittest.mock import Mock

import pytest
from aiohttp import web

from piqueserver import bansubscribe


class banmanagertest(unittest.TestCase):
    def test_create(self):
        banm = bansubscribe.BanSubscribeManager(Mock())
        banm.loop.stop()
