This is a fork of `piqueserver <https://github.com/piqueserver/piqueserver>`__.

\:tada: Features
----------------

-  Many administrator features
-  A lot of epic commands
-  A remote console (using SSH)
-  Map rotation
-  Map metadata (name, version, author, and map configuration)
-  Map extensions (water damage, etc.)
-  A map generator
-  An IRC client for managing your server
-  A JSON query webserver
-  A status server with map overview
-  Server/map scripts
-  Airstrikes
-  Melee attacks with the pickaxe
-  New gamemodes (deathmatch / runningman)
-  Rollback feature (rolling back to the original map)
-  Spectator mode
-  Dirt grenades
-  Platforms with buttons
-  Ban subscribe service
-  A ton of other features

\:rocket: Installation
----------------------

Python 3.10 or above is required.

.. code:: bash

    git clone https://github.com/aloha-pk/piqueserver
    cd piqueserver
    python3 -m venv venv
    source venv/bin/activate

    pip install .

    # now `piqueserver` will be available on the $PATH when venv is active

To install with optional features:

.. code:: bash

    pip3 install .[ssh,from]

Optional features:

- `ssh`: enable ssh manhole server support
- `from`: enable the `from` command to geolocate players by ip

\:rocket: Running
-----------------

Then copy the default configuration as a base to work off

.. code:: bash

    piqueserver --copy-config

A-a-and lift off!

.. code:: bash

    piqueserver

Custom config location
~~~~~~~~~~~~~~~~~~~~~~

If you wish to use a different location to ``~/.config/piqueserver/``
for config files, specify a directory with the ``-d`` flag:

.. code:: bash

    piqueserver --copy-config -d custom_dir
    piqueserver -d custom_dir

\:speech_balloon: FAQ
---------------------

Working with multiple versions is a pain. 0.76 will be suported in the
future only.

\:blush: Contribute
-------------------

Don't be shy and submit us a PR or an issue! Help is always appreciated

\:wrench: Development
---------------------

Use ``python3`` and ``pip`` to setup the development environment:

.. code:: bash

    $ python3 -m venv venv && source venv/bin/activate
    (venv) $ pip install -e '.[dev]' # install in-place
    (venv) $ deactivate # Deactivate virtualenv
