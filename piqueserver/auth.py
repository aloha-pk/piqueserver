import abc
from typing import Tuple, List, Any
from pyspades.types import AttributeSet
import piqueserver
from piqueserver.config import config


LoginInfo = Tuple[List[str], Any] # user_types, and anything the backend wants to store


class AuthAlreadyLoggedIn(Exception):
    pass

class AuthError(Exception):
    pass

class AuthLimitExceeded(Exception):
    def __init__(self, message = None, kick = False):
        super().__init__(message)
        self.kick = kick
        self.message = message


class BaseAuthBackend(abc.ABC):
    @abc.abstractmethod
    async def login(self, connection, *details) -> LoginInfo:
        """
        Verifies details and returns a user_type, e.g. 'admin'.

        Raises AuthError if the details are incorrect.

        Raises AuthLimitExceeded if the backend deems too many incorrect attempts have been made.

        Raises ValueError if not enough details have been passed in.
        """
        pass

    @abc.abstractmethod
    async def on_logout(self, connection) -> str:
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
    def get_all_user_types(self) -> List[str]:
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

    @abc.abstractmethod
    def get_user_info(self, connection) -> str:
        """
        Accesses connection.login_info and returns a human-readable description of a
        player's current login status.
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
    auth = connection.protocol.auth_backend
    for user_type in connection.login_info[0]:
        connection.on_user_login(user_type, True)
    user_info = auth.get_user_info(connection)
    message = '{} logged in as {}'
    connection.send_chat(message.format('You', user_info))
    connection.protocol.irc_say('* ' + message.format(connection.name, user_info))

def notify_logout(connection) -> None:
    for user_type in connection.login_info[0]:
        connection.on_user_logout(user_type)
    connection.send_chat('Logout successful')
    connection.protocol.irc_say('* {} logged out'.format(connection.name))
    connection.login_info = None


class ConfigAuthBackend(BaseAuthBackend):
    """
    Auth backend that uses the [passwords] section of the config for authentication
    """

    def __init__(self):
        self.passwords = config.option('passwords', default={})
        self.rights = config.option('rights', default={})
        self.max_tries = 3

    async def login(self, connection, *details) -> LoginInfo:
        if len(details) > 1:
            raise ValueError("Too many arguments")
        password = details[0]

        for user_type, passwords in self.passwords.get().items():
            if password in passwords:
                if (connection.login_info and
                    user_type in connection.login_info[0]):
                    raise piqueserver.auth.AuthAlreadyLoggedIn()
                return ([user_type], None)

        # HACK:
        # raise through full names of exceptions instead of referring to them locally
        # this prevents some weirdness with catching exceptions in /login
        connection.login_tries += 1
        if connection.login_tries >= self.max_tries:
            raise piqueserver.auth.AuthLimitExceeded('Ran out of login attempts', kick = True)
        raise piqueserver.auth.AuthError('Invalid password - you have {} tries left'
            .format(self.max_tries - connection.login_tries))

    async def on_logout(self, connection) -> str:
        pass

    def has_permission(self, connection, action: str) -> bool:
        if connection.admin:
            return True
        for user_type in connection.user_types:
            if action in self.get_rights(user_type):
                return True
        return False

    def get_all_user_types(self) -> List[str]:
        return self.passwords.get().keys()

    def get_rights(self, user_type: str) -> List[str]:
        return self.rights.get().get(user_type, [])

    def get_user_info(self, connection) -> str:
        return ', '.join(connection.login_info[0]) # just the user types