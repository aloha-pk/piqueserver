import abc
from typing import Tuple, List

Details = Tuple[str, str] # username, password


class AuthError(Exception):
    pass

class AuthLimitExceeded(Exception):
    def __init__(self, message, kick = False):
        super().__init__(message)
        self.kick = kick
        self.message = message


class BaseAuthBackend(abc.ABC):
    @abc.abstractmethod
    def login(self, details: Details) -> str:
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


class ConfigAuthBackend(BaseAuthBackend):
    """Auth backend that uses the [passwords] section of the connfig for
    authentication"""
    def login(self, username):
        pass
