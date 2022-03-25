from twisted.trial import unittest
from unittest.mock import Mock

from piqueserver import banpublish
from piqueserver import bansubscribe


class banmanagertest(unittest.TestCase):
    def test_create(self):
        banm = bansubscribe.BanSubscribeManager(Mock())
        banm.loop.stop()
