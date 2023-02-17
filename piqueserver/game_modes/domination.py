# Copyrights for portions of this file are held by one or more contributors from the Ace of Spades community.
# All other copyrights are held jointly by collaborators from the aloha.pk community.
# This file is a redistribution by the aloha.pk organization. More information: https://aloha.pk/pub/github-org

from pyspades.constants import CTF_MODE, TC_MODE
def apply_script(protocol, connection, config):
    class GameModeConnection(connection):
        def on_join(self):
            return connection.on_join(self)
    class GameModeProtocol(protocol):
        game_mode = TC_MODE
    return GameModeProtocol, GameModeConnection