"""
Babel: reach the heavens by building a tower

Derived from onectf.py by Yourself

Release thread:
http://www.buildandshoot.com/viewtopic.php?t=2586
"""

import math
from pyspades.constants import CTF_MODE
from pyspades.collision import vector_collision

FLAG_SPAWN_POS = (256, 256)

HIDE_POS = (math.inf, math.inf, 128)

DISABLED, ONE_CTF, REVERSE_ONE_CTF = range(3)

ONE_CTF_MODE = ONE_CTF

BABEL_CTF_MESSAGE = 'Take the intel to the enemy base to score.'


def apply_script(protocol, connection, config):

    class OneCTFConnection(connection): 
        def on_flag_take(self):
            if self.protocol.one_ctf or self.protocol.reverse_one_ctf:
                flag = self.team.flag
                if flag.player is not None:
                    return False
            value = connection.on_flag_take(self)
            if value == False:
                return value
            if self.protocol.one_ctf or self.protocol.reverse_one_ctf:
                flag = self.team.flag
                flag.set(*HIDE_POS)
                flag.update()
            return value

        def on_flag_drop(self):
            if self.protocol.one_ctf or self.protocol.reverse_one_ctf:
                flag = self.team.flag
                position = self.world_object.position
                x, y, z = int(
                    position.x), int(
                    position.y), max(
                    0, int(
                        position.z))
                z = self.protocol.map.get_z(x, y, z)
                flag.set(x, y, z)
                flag.update()
            return connection.on_flag_drop(self)

        def on_position_update(self):
            if self.protocol.reverse_one_ctf:
                if vector_collision(
                        self.world_object.position,
                        self.team.other.base):
                    other_flag = self.team.other.flag
                    if other_flag.player is self:
                        connection.capture_flag(self)
            return connection.on_position_update(self)

        def capture_flag(self):
            if self.protocol.reverse_one_ctf:
                self.send_chat(BABEL_CTF_MESSAGE)
                return False
            return connection.capture_flag(self)

        def on_flag_capture(self):
            if self.protocol.one_ctf or self.protocol.reverse_one_ctf:
                self.protocol.onectf_reset_flags()
            return connection.on_flag_capture(self)

    class OneCTFProtocol(protocol):
        game_mode = CTF_MODE
        one_ctf = False
        reverse_one_ctf = False

        def onectf_reset_flag(self, flag):
            z = self.map.get_z(*self.one_ctf_spawn_pos)
            pos = (self.one_ctf_spawn_pos[0], self.one_ctf_spawn_pos[1], z)
            if flag is not None:
                flag.player = None
                flag.set(*pos)
                flag.update()
            return pos

        def onectf_reset_flags(self):
            if self.one_ctf or self.reverse_one_ctf:
                self.onectf_reset_flag(self.blue_team.flag)
                self.onectf_reset_flag(self.green_team.flag)

        def on_game_end(self):
            if self.one_ctf or self.reverse_one_ctf:
                self.onectf_reset_flags()
            return protocol.on_game_end(self)

        def on_map_change(self, map_):
            self.one_ctf = self.reverse_one_ctf = False
            self.one_ctf_spawn_pos = FLAG_SPAWN_POS
            extensions = self.map_info.extensions
            if ONE_CTF_MODE == ONE_CTF:
                self.one_ctf = True
            elif ONE_CTF_MODE == REVERSE_ONE_CTF:
                self.reverse_one_ctf = True
            elif 'one_ctf' in extensions:
                self.one_ctf = extensions['one_ctf']
            if not self.one_ctf and 'reverse_one_ctf' in extensions:
                self.reverse_one_ctf = extensions['reverse_one_ctf']
            if 'one_ctf_spawn_pos' in extensions:
                self.one_ctf_spawn_pos = extensions['one_ctf_spawn_pos']
            return protocol.on_map_change(self, map_)

        def on_flag_spawn(self, x, y, z, flag, entity_id):
            pos = self.onectf_reset_flag(flag.team.other.flag)
            protocol.on_flag_spawn(
                self, pos[0], pos[1], pos[2], flag, entity_id)
            return pos

    return OneCTFProtocol, OneCTFConnection
