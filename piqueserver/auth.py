import abc
from typing import List
from pyspades.types import AttributeSet
import piqueserver
from piqueserver.config import config


class AuthError(Exception):
    pass

class AuthLimitExceeded(Exception):
    def __init__(self, message = None, kick = False):
        super().__init__(message)
        self.kick = kick
        self.message = message


class BaseAuthBackend(abc.ABC):
    @abc.abstractmethod
    def login(self, connection, username, password) -> str:
        """
        Verifies details and returns a user_type, e.g. 'admin'.
        Raises AuthError if the details are incorrect.
        Raises AuthLimitExceeded if the backend deems too many incorrect attempts have been made.
        """
        pass

    @abc.abstractmethod
    def on_logout(self, connection) -> str:
        """
        Called when a player logs out, before their user_type is actually cleared.
        """
        pass

    @abc.abstractmethod
    def has_permission(self, connection, action: str) -> bool:
        """
        Checks if a player has permission to perform a specific action.
        """
        pass

    @abc.abstractmethod
    def get_player_user_types(self) -> List[str]:
        """
        Returns a list of user_types that regular, in-game players can log in as.
        """
        pass

    @abc.abstractmethod
    def get_rights(self, user_type: str) -> List[str]:
        """
        Returns a list of actions the given user_type can perform.
        """
        pass

    def set_user_type(self, connection, user_type: str) -> None:
        if user_type == 'admin':
            connection.admin = True
            connection.speedhack_detect = False
        connection.user_types.add(user_type)
        rights = set(self.get_rights(user_type))
        connection.rights.update(rights)

    def reset_user_type(self, connection) -> None:
        connection.user_types = AttributeSet()
        connection.rights = AttributeSet()
        connection.admin = False
        connection.speedhack_detect = True


def notify_login(connection) -> None:
    details = connection.login_details
    connection.on_user_login(details[0], True)
    if details[0] == details[1]:
        user = details[0]
    else:
        user = '{} ({})'.format(*details)
    message = '{} logged in as {}'
    connection.protocol.irc_say('* ' + message.format(connection.name, user))
    return message.format('You', user)

def notify_logout(connection) -> None:
    connection.on_user_logout(connection.login_details[0])
    connection.protocol.irc_say('* {} logged out'.format(connection.name))
    return 'Logout successful'


class ConfigAuthBackend(BaseAuthBackend):
    """
    Auth backend that uses the [passwords] section of the config for authentication
    """

    def __init__(self):
        self.passwords = config.option('passwords', default={})
        self.rights = config.option('rights', default={})
        self.max_tries = 3

    def login(self, connection, username, password) -> str:
        if username not in self.passwords.get():
            self.invalid_password(connection)
        if password not in self.passwords.get()[username]:
            self.invalid_password(connection)
        return username

    def invalid_password(self, connection):
        # HACK:
        # raise through full names of exceptions instead of referring to them locally
        # this prevents some weirdness with catching exceptions in /login
        connection.login_tries += 1
        if connection.login_tries >= self.max_tries:
            raise piqueserver.auth.AuthLimitExceeded('Ran out of login attempts', kick = True)
        raise piqueserver.auth.AuthError('Invalid password - you have {} tries left'
            .format(self.max_tries - connection.login_tries))

    def on_logout(self, connection) -> str:
        pass

    def has_permission(self, connection, action: str) -> bool:
        if connection.admin:
            return True
        for user_type in connection.user_types:
            if action in self.get_rights():
                return True
        return False

    def get_player_user_types(self) -> List[str]:
        return self.passwords.get().keys()

    def get_rights(self, user_type: str) -> List[str]:
        return self.rights.get().get(user_type, [])
