
import socket
import threading
import time
import utils.logger as logger
from typing import Set, Tuple
import json5 as json
import os
import zlib

log = logger.Logger("discovery")


def discover_peers(
    local_host: str,
    local_port: int,
    broadcast_port: int,
    username: str,
    public_key: str,
    broadcast_interval: int = 1,
) -> Set[Tuple[str, int]]:
    """
    New peers discovery in network through UDP broadcasting messages

    :param local_host: Local peer host
    :type local_host: str
    :param local_port: Local peer port
    :type local_port: int
    :param broadcast_port: Broadcasting port
    :type broadcasting port: int
    :param username: Local peer's username
    :type username: str
    :param public_key: Local peer's DH public key
    :type public_key: str
    :param broadcast_interval: Broadcasting messages interval
    :type broadcast_interval: int
    :return: Discovered peers
    :rtype: set
    """
    peers = set()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def listen_for_broadcast():
        """Listens for broadcasting messages to find new peers"""
        with sock as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            try:
                if os.name == "posix":
                    udp_socket.bind(('', broadcast_port))
                else:
                    udp_socket.bind((local_host, broadcast_port))
            except socket.error as e:
                log.error(f"Could not bind socket: {e}")
                return

            log.debug(f"Listening for broadcasts on {local_host}:{broadcast_port}")
            while True:
                try:
                    data, addr = udp_socket.recvfrom(4096)
                    peer_info = json.loads(zlib.decompress(data).decode())

                    peer_port = peer_info["port"]
                    try:
                        peer_port = int(peer_port)
                    except ValueError:
                        log.debug(f"Invalid peer port received: {peer_port}")
                        continue

                    peer = (addr[0], peer_port, peer_info["username"],
                            bytes.fromhex(peer_info["public_key"]))
                    if peer == (local_host, local_port, username, bytes.fromhex(public_key)):
                        log.debug(f"Ignoring self broadcast from {peer}")
                        continue

                    if peer not in peers:
                        peers.add(peer)
                        log.info(f"Discovered new peer: {peer_info} at {addr}")
                except socket.error as e:
                    log.error(f"Error in receiving broadcast: {e}")
                except UnicodeDecodeError as e:
                    log.error(f"Error decoding broadcast message: {e}")

    def send_broadcast():
        """Sends broadcasting messages to remined others about its peer."""
        # Create udp socket
        with sock as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            message = {"host": local_host, "port": local_port,
                       "public_key": public_key, "username": username}
            broadcast_address = ("<broadcast>", broadcast_port)

            # Compressing message so it is 100% delievered
            compressed = zlib.compress(json.dumps(message, ensure_ascii=False)
                                      .encode())

            while True:
                try:
                    udp_socket.sendto(compressed, broadcast_address)
                    log.debug(f"Broadcasting: {message}")
                except socket.error as e:
                    log.error(f"Error in sending broadcast: {e}")
                finally:
                    time.sleep(
                        broadcast_interval
                    )  # Repeat every broadcast_interval

    threading.Thread(target=listen_for_broadcast, daemon=True).start()
    threading.Thread(target=send_broadcast, daemon=True).start()

    return peers
