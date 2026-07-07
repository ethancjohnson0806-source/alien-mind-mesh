import hashlib
import json
import os
import random
import socket
import sys
import threading
import time
import uuid
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Optional

# ═══════════════════════════════════════════════════════════════════════════════
# SHARED MATH (must match exactly across all nodes for zone consistency)
# ═══════════════════════════════════════════════════════════════════════════════

def hash_to_point(key: str) -> tuple:
    h = hashlib.sha256(key.encode()).hexdigest()
    x = int(h[:16], 16) / (2 ** 64)
    y = int(h[16:32], 16) / (2 ** 64)
    return (x, y)

def point_in_zone(point, zone) -> bool:
    (x, y) = point
    ((x1, y1), (x2, y2)) = zone
    return x1 <= x <= x2 and y1 <= y <= y2

def zone_center(zone) -> tuple:
    ((x1, y1), (x2, y2)) = zone
    return ((x1 + x2) / 2, (y1 + y2) / 2)

def dist(p1, p2) -> float:
    return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2) ** 0.5

def split_zone(zone) -> tuple:
    (x1, y1), (x2, y2) = zone
    width, height = x2 - x1, y2 - y1
    if width >= height:
        mid = (x1 + x2) / 2
        keep = ((x1, y1), (mid, y2))
        give  = ((mid, y1), (x2, y2))
    else:
        mid = (y1 + y2) / 2
        keep = ((x1, y1), (x2, mid))
        give  = ((x1, mid), (x2, y2))
    return keep, give

def local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()

def fmt_zone(zone) -> str:
    (x1, y1), (x2, y2) = zone
    return f"({x1:.2f},{y1:.2f})-({x2:.2f},{y2:.2f})"


MAX_HOPS = 16
REQUEST_TIMEOUT = 4.0
GOSSIP_INTERVAL = 8.0


# ═══════════════════════════════════════════════════════════════════════════════
# GHOST MESH NODE — UDP network layer
# ═══════════════════════════════════════════════════════════════════════════════

class GhostMeshNode:
    """
    A node in the ghost mesh. Owns a zone in [0,1]^2.
    Routes STORE/GET messages greedily toward the zone containing hash_to_point(key).
    Gossips neighbor tables periodically.
    """
    def __init__(self, port, bootstrap_phrase):
        self.id = uuid.uuid4().hex[:6]
        self.port = port
        self.network_key = hashlib.sha256(bootstrap_phrase.encode()).hexdigest()[:16]
        self.zone = ((0.0, 0.0), (1.0, 1.0))
        self.storage = {}       # point -> {"key": str, "value": str}
        self.neighbors = {}     # id -> {"addr": (ip, port), "zone": zone}
        self.lock = threading.Lock()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(("", port))

        self.running = True
        self.joined = threading.Event()
        self.pending = {}
        self.pending_result = {}
        self.local_ip = local_ip()

    def send(self, msg, addr):
        try:
            self.sock.sendto(json.dumps(msg).encode(), tuple(addr))
        except OSError as e:
            print(f"[send failed to {addr}: {e}]")

    def listen_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(65536)
            except OSError:
                break
            try:
                msg = json.loads(data.decode())
            except (ValueError, UnicodeDecodeError):
                continue
            self.handle_message(msg, addr)

    def gossip_loop(self):
        while self.running:
            time.sleep(GOSSIP_INTERVAL)
            with self.lock:
                targets = list(self.neighbors.items())
                table = {nid: {"addr": list(info["addr"]), "zone": info["zone"]}
                         for nid, info in self.neighbors.items()}
                my_zone = self.zone
            for _, info in targets:
                self.send({"type": "GOSSIP", "from_id": self.id, "zone": my_zone,
                           "neighbors": table}, info["addr"])

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except OSError:
            pass

    def handle_message(self, msg, addr):
        t = msg.get("type")
        if t == "HELLO":
            self.handle_hello(msg, addr)
        elif t == "JOIN_SEEK":
            self.handle_join_seek(msg)
        elif t == "WELCOME":
            self.handle_welcome(msg, addr)
        elif t == "GOSSIP":
            self.handle_gossip(msg, addr)
        elif t == "STORE":
            self.handle_store(msg)
        elif t == "STORE_ACK":
            self.resolve_pending(msg)
        elif t == "GET":
            self.handle_get(msg)
        elif t == "GET_REPLY":
            self.resolve_pending(msg)

    def handle_hello(self, msg, addr):
        if msg.get("network") != self.network_key:
            return
        joiner_id = msg.get("id")
        if joiner_id == self.id:
            return
        target = (random.random(), random.random())
        seek = {"type": "JOIN_SEEK", "target": list(target), "joiner_id": joiner_id,
                "joiner_addr": list(addr), "hops": 0}
        self.handle_join_seek(seek)

    def handle_join_seek(self, msg):
        target = tuple(msg["target"])
        hops = msg.get("hops", 0)
        joiner_id = msg["joiner_id"]
        joiner_addr = tuple(msg["joiner_addr"])

        with self.lock:
            best_id, best_dist, best_addr = self.id, dist(target, zone_center(self.zone)), None
            for nid, info in self.neighbors.items():
                d = dist(target, zone_center(info["zone"]))
                if d < best_dist:
                    best_id, best_dist, best_addr = nid, d, info["addr"]

            if best_id != self.id and hops < MAX_HOPS:
                forward = dict(msg)
                forward["hops"] = hops + 1
                self.send(forward, best_addr)
                return

            keep, give = split_zone(self.zone)
            transferred = {p: e for p, e in self.storage.items() if point_in_zone(p, give)}
            for p in transferred:
                del self.storage[p]
            self.zone = keep
            starter_neighbors = {nid: {"addr": list(info["addr"]), "zone": info["zone"]}
                                  for nid, info in self.neighbors.items()}
            self.neighbors[joiner_id] = {"addr": joiner_addr, "zone": give}

        welcome = {
            "type": "WELCOME",
            "your_zone": give,
            "welcomer_id": self.id,
            "welcomer_zone": keep,
            "transferred": {f"{p[0]},{p[1]}": e for p, e in transferred.items()},
            "starter_neighbors": starter_neighbors,
        }
        self.send(welcome, joiner_addr)
        print(f"\n[peer joined] {joiner_id} took zone {fmt_zone(give)}. "
              f"My zone is now {fmt_zone(keep)}.")

    def handle_welcome(self, msg, addr):
        with self.lock:
            self.zone = tuple(map(tuple, msg["your_zone"]))
            welcomer_zone = tuple(map(tuple, msg["welcomer_zone"]))
            self.neighbors[msg["welcomer_id"]] = {"addr": addr, "zone": welcomer_zone}
            for nid, info in msg.get("starter_neighbors", {}).items():
                if nid != self.id and nid not in self.neighbors:
                    self.neighbors[nid] = {"addr": tuple(info["addr"]),
                                            "zone": tuple(map(tuple, info["zone"]))}
            for key, entry in msg["transferred"].items():
                x, y = map(float, key.split(","))
                self.storage[(x, y)] = entry
        print(f"\n[joined network] My zone is {fmt_zone(self.zone)}. "
              f"Know of {len(self.neighbors)} peer(s) so far.")
        self.joined.set()

    def handle_gossip(self, msg, addr):
        sender_id = msg["from_id"]
        if sender_id == self.id:
            return
        sender_zone = tuple(map(tuple, msg["zone"]))
        with self.lock:
            self.neighbors[sender_id] = {"addr": addr, "zone": sender_zone}
            for nid, info in msg.get("neighbors", {}).items():
                if nid != self.id and nid not in self.neighbors:
                    self.neighbors[nid] = {"addr": tuple(info["addr"]),
                                            "zone": tuple(map(tuple, info["zone"]))}

    def closest_neighbor(self, point):
        with self.lock:
            if not self.neighbors:
                return None
            return min(self.neighbors.values(),
                        key=lambda n: dist(point, zone_center(n["zone"])))

    def store(self, key, value):
        point = hash_to_point(key)
        with self.lock:
            in_zone = point_in_zone(point, self.zone)
            if in_zone:
                self.storage[point] = {"key": key, "value": value}
        if in_zone:
            print(f"[stored locally] key={key!r}")
            return

        neighbor = self.closest_neighbor(point)
        if neighbor is None:
            print("[store failed] Not in my zone and I have no peers to route to.")
            return

        request_id = uuid.uuid4().hex
        event = threading.Event()
        self.pending[request_id] = event
        msg = {"type": "STORE", "key": key, "value": value,
               "origin_addr": [self.local_ip, self.port],
               "request_id": request_id, "hops": 0}
        self.send(msg, neighbor["addr"])
        if event.wait(REQUEST_TIMEOUT):
            result = self.pending_result.pop(request_id, {})
            print(f"[stored remotely] by node {result.get('stored_by')} key={key!r}")
        else:
            print("[store timed out] no acknowledgement received.")
        self.pending.pop(request_id, None)

    def handle_store(self, msg):
        key, value = msg["key"], msg["value"]
        point = hash_to_point(key)
        origin = tuple(msg["origin_addr"])
        hops = msg.get("hops", 0)

        with self.lock:
            in_zone = point_in_zone(point, self.zone)
            if in_zone:
                self.storage[point] = {"key": key, "value": value}

        if in_zone:
            self.send({"type": "STORE_ACK", "request_id": msg["request_id"],
                       "stored_by": self.id}, origin)
            return

        if hops >= MAX_HOPS:
            self.send({"type": "STORE_ACK", "request_id": msg["request_id"],
                       "stored_by": None}, origin)
            return

        neighbor = self.closest_neighbor(point)
        if neighbor is None:
            self.send({"type": "STORE_ACK", "request_id": msg["request_id"],
                       "stored_by": None}, origin)
            return

        forward = dict(msg)
        forward["hops"] = hops + 1
        self.send(forward, neighbor["addr"])

    def get(self, key):
        point = hash_to_point(key)
        with self.lock:
            entry = self.storage.get(point)
        if entry is not None and entry["key"] == key:
            print(f"[found locally] {entry['value']!r}")
            return entry["value"]

        neighbor = self.closest_neighbor(point)
        if neighbor is None:
            print("[not found] Not stored here and I have no peers to ask.")
            return None

        request_id = uuid.uuid4().hex
        event = threading.Event()
        self.pending[request_id] = event
        msg = {"type": "GET", "key": key, "origin_addr": [self.local_ip, self.port],
               "request_id": request_id, "hops": 0}
        self.send(msg, neighbor["addr"])
        result = None
        if event.wait(REQUEST_TIMEOUT):
            payload = self.pending_result.pop(request_id, {})
            if payload.get("found"):
                result = payload.get("value")
                print(f"[found remotely] via node {payload.get('stored_by')}: {result!r}")
            else:
                print("[not found] Queried the network, nobody had it.")
        else:
            print("[get timed out] no reply received.")
        self.pending.pop(request_id, None)
        return result

    def handle_get(self, msg):
        key = msg["key"]
        point = hash_to_point(key)
        origin = tuple(msg["origin_addr"])
        hops = msg.get("hops", 0)

        with self.lock:
            entry = self.storage.get(point)

        if entry is not None and entry["key"] == key:
            self.send({"type": "GET_REPLY", "request_id": msg["request_id"],
                       "found": True, "value": entry["value"], "stored_by": self.id}, origin)
            return

        if hops >= MAX_HOPS:
            self.send({"type": "GET_REPLY", "request_id": msg["request_id"],
                       "found": False}, origin)
            return

        neighbor = self.closest_neighbor(point)
        if neighbor is None:
            self.send({"type": "GET_REPLY", "request_id": msg["request_id"],
                       "found": False}, origin)
            return

        forward = dict(msg)
        forward["hops"] = hops + 1
        self.send(forward, neighbor["addr"])

    def resolve_pending(self, msg):
        request_id = msg.get("request_id")
        event = self.pending.get(request_id)
        if event:
            self.pending_result[request_id] = msg
            event.set()

    def join_via_broadcast(self, timeout=30):
        hello = {"type": "HELLO", "network": self.network_key, "id": self.id}
        end = time.time() + timeout
        while self.running and not self.joined.is_set() and time.time() < end:
            self.send(hello, ("255.255.255.255", self.port))
            self.joined.wait(2.0)
        if not self.joined.is_set():
            print(f"\n[no peer found after {timeout}s] I own the whole zone "
                  f"until someone joins. Still listening.")

    def join_via_peer(self, ip, port, attempts=10):
        hello = {"type": "HELLO", "network": self.network_key, "id": self.id}
        addr = (ip, port)
        for _ in range(attempts):
            if self.joined.is_set():
                break
            self.send(hello, addr)
            self.joined.wait(2.0)
        if not self.joined.is_set():
            print(f"\n[could not join {ip}:{port}] Check the address and that "
                  f"both sides use the same --bootstrap phrase.")

    def start(self):
        threading.Thread(target=self.listen_loop, daemon=True).start()
        threading.Thread(target=self.gossip_loop, daemon=True).start()

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except OSError:
            pass
