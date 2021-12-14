from piqueserver.commands import (command, get_player, join_arguments,
                                  player_only)
from piqueserver.auth import AuthAlreadyLoggedIn, AuthError, AuthLimitExceeded, notify_login, notify_logout
from twisted.internet.defer import ensureDeferred

S_AUTH_LIMITED_EXCEEDED = "Login attempt limit exceeded"

@command()
@player_only
def login(connection, *details):
    """
    Log in if you're staff or a trusted member of this server
    /login <details>
    You will be kicked if a wrong password is given 3 times in a row
    """
    if not details:
        return "Please provide login details"
    
    if connection.login_disabled:
        # player has already exceeded the auth limit
        return S_AUTH_LIMITED_EXCEEDED
    
    auth = connection.protocol.auth_backend
    
    async def _login():
        try:
            connection.login_info = await auth.login(connection, *details)
            auth.reset_user_type(connection)
            user_types = connection.login_info[0]
            for user_type in user_types:
                auth.set_user_type(connection, user_type)
            notify_login(connection)
        except AuthAlreadyLoggedIn:
            connection.send_chat("You're already logged in as {}".format(auth.get_user_info(connection)))
        except AuthError as ae:
            connection.send_chat(str(ae))
        except AuthLimitExceeded as ale:
            connection.login_disabled = True
            message = ale.message or S_AUTH_LIMITED_EXCEEDED
            if ale.kick:
                connection.kick(message)
            connection.send_chat(message)

    ensureDeferred(_login())

@command()
@player_only
def logout(connection):
    """
    Log out, if you're logged in
    /logout
    """
    async def _logout():
        auth = connection.protocol.auth_backend
        
        valid_user_types = auth.get_all_user_types()
        if not any(t in connection.user_types for
                t in valid_user_types):
            connection.send_chat("You are not logged in")
            return

        await auth.on_logout(connection)
        auth.reset_user_type(connection)
        notify_logout(connection)

    ensureDeferred(_logout())

@command()
def pm(connection, value, *arg):
    """
    Send a private message to a given player
    /pm <player> <message>
    """
    player = get_player(connection.protocol, value)
    message = join_arguments(arg)
    if len(message) == 0:
        return "Please specify your message"
    player.send_chat('PM from %s: %s' % (connection.name, message))
    return 'PM sent to %s' % player.name


@command('admin')
def to_admin(connection, *arg):
    """
    Send a message to all admins currently online
    /admin <message>
    """
    protocol = connection.protocol
    message = join_arguments(arg)
    if not message:
        return "Enter a message you want to send, like /admin I'm stuck"
    prefix = '(TO ADMINS)'
    irc_relay = protocol.irc_relay
    if irc_relay:
        if irc_relay.factory.bot and irc_relay.factory.bot.colors:
            prefix = '\x0304' + prefix + '\x0f'
        irc_relay.send(prefix + ' <%s> %s' % (connection.name, message))
    for player in protocol.players.values():
        if player.admin and player is not connection:
            player.send_chat('To ADMINS from %s: %s' %
                             (connection.name, message))
    return 'Message sent to all admins currently online'
