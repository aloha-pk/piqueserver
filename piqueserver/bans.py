import abc
from ast import Str
from typing import Tuple, Optional, List, Any

import os
import json
import time
from ipaddress import IPv4Network, ip_address, ip_network
from twisted.logger import Logger
from twisted.internet import reactor
from twisted.internet.task import LoopingCall, coiterate
from piqueserver.utils import ensure_dir_exists
from piqueserver.networkdict import NetworkDict
from piqueserver.config import config


# network, name, reason, duration
Ban = Tuple[IPv4Network, str, str, Optional[int]]


log = Logger()


# i would REALLY like to make this async, but i'm not totally sure that's feasible atm - muffin
class BaseBanManager(abc.ABC):
    """
    Ban backend - nothing to do with banpublish or bansubscribe!
    """


    banpublish_update_callback = None


    def __init__(self, protocol):
        self.protocol = protocol

    @abc.abstractmethod
    def ban_overlaps(self, network) -> Optional[IPv4Network]:
        """
        Check the ban database for the existence of any IPs/networks that overlap with the one provided.
        
        For example, if 192.168.1.0/23 is already banned, then calling ban_overlaps() with network 192.168.0.0/24 will return True.
        """
        pass

    @abc.abstractmethod
    def get_ban(self, network) -> Optional[Ban]:
        """
        Get if IP is banned or is a subnet of a banned network. If so, return that ban.
        """
        pass

    @abc.abstractmethod
    def get_all_bans(self) -> List[Ban]:
        """
        Gets a list of all bans in the database. May be empty.
        """
        pass

    @abc.abstractmethod
    def add_ban(self, network, name, reason, duration) -> Optional[str]:
        """
        Add an IP/network to the ban database.

        name, reason and duration may be None.

        Returns an optional error string message. Not an exception as they're non-fatal errors
        """
        pass

    @abc.abstractmethod
    def remove_ban(self, network) -> int:
        """
        Removes all banned IPs/networks within the one provided

        Returns how many bans were removed
        """
        pass

    @abc.abstractmethod
    def undo_ban(self) -> Optional[Ban]:
        """
        Removes the last ban in the database
        """
        pass

    def kick_network(self, network) -> Optional[str]:
        kicked_name = None

        for connection in list(self.protocol.connections.values()):
            if ip_address(connection.address[0]) in network:
                kicked_name = connection.name
                connection.kick(silent=True)

        return kicked_name

    def banpublish_update(self):
        """
        Tells BanPublish to update its internal list.
        Call this after modifications to the database / flushes to disk.
        """

        if self.banpublish_update_callback is not None:
            if not callable(self.banpublish_update_callback):
                log.error(f"BanPublish callback is set incorrectly: expected callable, got {type(self.banpublish_update_callback)}")
                return
            self.banpublish_update_callback()


class DefaultBanManager(BaseBanManager):
    """
    Ban manager that uses a NetworkDict as its database and saves to a local bans.txt JSON file
    """

    def __init__(self, protocol):
        super().__init__(protocol)

        self.database = NetworkDict()
        bans_config = config.section('bans')
        self.bans_file = bans_config.option('file', default='bans.txt')

        # attempt to load a saved bans list
        try:
            with open(os.path.join(config.config_dir, self.bans_file.get()), 'r') as f:
                self.database.read_list(json.load(f))
            log.debug("Loaded {count} bans", count=len(self.database))
        except FileNotFoundError:
            log.debug("Skip loading bans: file unavailable",
                      count=len(self.database))
        except IOError as e:
            log.error('Could not read bans file ({}): {}'.format(self.bans_file.get(), e))
        except ValueError as e:
            log.error('Could not parse bans file ({}): {}'.format(self.bans_file.get(), e))
            
        self.vacuum_loop = LoopingCall(self.vacuum_bans)
        # Run the vacuum every 6 hours, and kick it off it right now
        self.vacuum_loop.start(60 * 60 * 6, True)

    def ban_overlaps(self, network) -> Optional[IPv4Network]:
        network1 = ip_network(str(network), strict=False)
        n1_from = int(network1[0])
        n1_to = int(network1[-1])
    
        if network1.num_addresses == 1:
            # a single IP cannot overlap any network
            return False
    
        for network2 in self.database.networks.keys():
            n2_from = int(network2[0])
            n2_to = int(network2[-1])
    
            if (n2_from != n2_to and
                (n2_from <= n1_from <= n2_to or
                 n1_from <= n2_from <= n1_to)):
                return network2
    
        return None

    def get_ban(self, network) -> Optional[Ban]:
        try:
            result = self.database.get_entry(network)
            return ip_network(str(network), strict=False), *result
        except KeyError:
            return None

    def get_contained_bans(self, network1: IPv4Network) -> List[IPv4Network]:
        if network1.num_addresses == 1:
            # a single IP cannot contain any other networks
            return []

        n1_from = int(network1[0])
        n1_to = int(network1[-1])
        contained = []

        for network2 in self.database.networks.keys():
            if network1 == network2:
                continue

            n2_from = int(network2[0])
            n2_to = int(network2[-1])
            if n1_from <= n2_from and n2_to <= n1_to:
                contained.append(network2)

        return contained

    def get_all_bans(self) -> List[Ban]:
        results = []
        for network, value in self.database.networks.items():
            results.append((network, *value))
        return results

    def add_ban(self, network, name, reason, duration) -> Optional[str]:
        """
        Ban an ip with an optional reason and duration in seconds. If duration
        is None, ban is permanent.
        """
        network = ip_network(str(network), strict=False)
        kicked_name = self.kick_network(network)
        if kicked_name:
            name = name or kicked_name
        if self.get_ban(network):
            msg = 'IP/Network {network} is already banned'.format(network=network)
            log.info(msg)
            return msg
        overlap = self.ban_overlaps(network)
        if overlap:
            msg = 'IP/Network {network} overlaps with network {overlap}'.format(
                network=network, overlap=overlap)
            log.info(msg)
            return msg
        if duration:
            duration = time.time() + duration
        else:
            duration = None
        self.database[network] = (name or '(unknown)', reason, duration)
        self.save_bans()
        return None

    def remove_ban(self, network) -> int:
        network = ip_network(str(network), strict=False)
        to_remove = [network] + self.get_contained_bans(network)
        amount_removed = 0
        for net in to_remove:
            results = self.database.remove(net)
            log.info('Removing banned network: {network} {results}',
                    network=net, results=results)
            amount_removed += len(results)
        self.save_bans()
        return amount_removed

    def undo_ban(self) -> Optional[Ban]:
        try:
            result = self.database.pop()
            network = ip_network(result[0])
            log.info('Removing banned network: {network} {ban}',
                    network=network, ban=result[1])
            self.save_bans()
            return (network, *result[1])
        except KeyError:
            return None

    def save_bans(self):
        ban_file = os.path.join(config.config_dir, self.bans_file.get())
        ensure_dir_exists(ban_file)

        start_time = reactor.seconds()
        with open(ban_file, 'w') as f:
            json.dump(self.database.make_list(), f, indent=2)
        log.debug("Saving {count} bans took {time:.2f} seconds",
                  count=len(self.database),
                  time=reactor.seconds() - start_time)

        self.banpublish_update()

    def vacuum_bans(self):
        """remove any bans that might have expired. This takes a while, so it is
        split up over the event loop"""

        def do_vacuum_bans():
            """do the actual clearing of bans"""

            bans_count = len(self.database)
            log.info("starting ban vacuum with {count} bans",
                     count=bans_count)
            start_time = time.time()

            # create a copy of the items, so we don't have issues modifying
            # while iteraing
            for ban in list(self.database.iteritems()):
                ban_expiry = ban[1][2]
                if ban_expiry is None:
                    # entry never expires
                    continue
                if ban[1][2] < start_time:
                    # expired
                    del self.database[ban[0]]
                yield
            log.debug("Ban vacuum took {time:.2f} seconds, removed {count} bans",
                      count=bans_count - len(self.database),
                      time=time.time() - start_time)
            self.save_bans()

        # TODO: use cooperate() here instead, once you figure out why it's
        # swallowing errors. Perhaps try add an errback?
        coiterate(do_vacuum_bans())