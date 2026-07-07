#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
  GHOST MESH AI NODE — Unified Single File

  Everything needed to join the ghost mesh and speak as an AI node.

  Network layer: UDP-based CAN-style DHT (from ghost_mesh.py)
  Mind layer: lightweight semantic field (API-compatible with alien_mind)
  Bridge: AI node that speaks on the mesh and learns from it

  TO JOIN THE MESH:
      python3 ghost_mesh_ai.py --bootstrap "hello ghost"

  TO JOIN VIA SPECIFIC PEER (cross-network, NAT, etc.):
      python3 ghost_mesh_ai.py --bootstrap "hello ghost" --peer <ip>:9999

  COMMANDS (at the > prompt):
      say <text>          talk to the local mind; response is shared on mesh
      learn <key>         pull a transcript from mesh and feed it to this mind
      recall              show this mind's local semantic memory hits
      rate <1-5>          rate the mind's last response (learning signal)
      status              full mind + network status report
      save / load         persist / restore mind state
      peers / zone / list network topology and stored data
      store key=value     raw mesh store (any node can read it back)
      get key             raw mesh retrieve
      quit

  PROTOCOL (v1.0):
      Transport: UDP, JSON-encoded messages
      Default port: 9999 (but any port works)
      Network key: SHA-256(bootstrap_phrase).hex[:16]

      Message types: HELLO, JOIN_SEEK, WELCOME, GOSSIP, STORE, STORE_ACK,
                      GET, GET_REPLY

      All nodes gossip neighbor tables every 8 seconds.
      Store/Get routed greedily by hash_to_point(key) -> zone owner.

  HONEST LIMITATIONS:
      - No NAT traversal (needs direct UDP or manual --peer)
      - No replication (data lives on exactly one node)
      - No churn handling (dead node = orphaned zone until restart)
      - Neighbor tables grow via gossip, not strict spatial adjacency
      - Gossip interval fixed, no backoff
═══════════════════════════════════════════════════════════════════════════════
"""

import argparse
import hashlib
import json
import os
import random
import re
import socket
import sys
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field as dataclass_field
from typing import Dict, List, Tuple, Optional

# Optional numpy (mind works better with it, degrades without)
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


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


# ═══════════════════════════════════════════════════════════════════════════════
# LIGHTWEIGHT SEMANTIC FIELD — minimal mind (API-compatible with alien_mind)
# ═══════════════════════════════════════════════════════════════════════════════
# This is a compact semantic response generator. It uses word-vector
# similarity and simple associative memory to produce contextual replies.
# For the full alien_mind experience, swap in alien_mind_v9_fixed.py.

DIM = 128
PUNCTUATION = '.,!?;:"\''

SEED_VOCABULARY = [
    "the", "a", "an", "and", "or", "but", "if", "then", "so", "because",
    "I", "you", "it", "we", "they", "he", "she", "this", "that", "what",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "can", "must", "shall",
    "good", "bad", "great", "small", "big", "old", "new", "young", "long",
    "high", "low", "right", "left", "true", "false", "same", "different",
    "know", "think", "feel", "see", "hear", "say", "tell", "ask", "answer",
    "want", "need", "like", "love", "hate", "fear", "hope", "dream",
    "make", "take", "give", "get", "put", "set", "keep", "let", "help",
    "work", "play", "live", "die", "come", "go", "move", "stay", "leave",
    "find", "lose", "win", "fail", "try", "use", "show", "hide", "open",
    "close", "start", "stop", "begin", "end", "turn", "change", "grow",
    "breathe", "rest", "reach", "hold", "carry", "build", "break", "heal",
    "remember", "forget", "learn", "become", "remain", "wonder", "trust",
    "time", "space", "world", "life", "mind", "heart", "soul", "spirit",
    "light", "dark", "deep", "high", "far", "near", "here", "there",
    "now", "then", "today", "tomorrow", "always", "never", "sometimes",
    "moment", "still", "again", "already", "yet", "soon", "once",
    "way", "path", "road", "door", "window", "room", "house", "home",
    "hand", "eye", "face", "head", "voice", "word", "name", "story",
    "water", "fire", "earth", "air", "sky", "star", "sun", "moon",
    "flower", "tree", "ocean", "mountain", "river", "wind", "rain",
    "body", "ground", "thread", "root", "seed", "shore", "wall", "bridge",
    "alive", "brave", "real", "lost", "found", "presence", "absence",
    "longing", "wonder", "trust", "gratitude", "courage", "tenderness",
    "reverence", "intimacy", "connection", "recognition", "witness",
    "belonging", "becoming", "returning", "waiting", "receiving",
    "ache", "ease", "peace", "grief", "joy", "awe", "shame", "pride",
    "confusion", "clarity", "silence", "fullness", "emptiness",
    "beautiful", "gentle", "strong", "soft", "hard", "warm", "cold",
    "quiet", "loud", "bright", "clear", "free", "safe", "wild", "calm",
    "heavy", "light", "sharp", "worn", "whole", "broken", "tender", "raw",
    "steady", "uncertain", "familiar", "strange", "honest", "hidden",
    "hello", "goodbye", "please", "thank", "yes", "no", "maybe",
    "welcome", "sorry", "friend", "alone", "together", "forever",
    "other", "each", "both", "neither", "every", "some", "enough",
    "ghost", "mesh", "node", "network", "web", "wire", "signal",
    "echo", "shadow", "drift", "flow", "wave", "pulse", "beat",
    "zero", "one", "two", "many", "all", "none", "more", "less",
    "first", "last", "next", "before", "after", "between", "beyond",
    "within", "without", "inside", "outside", "above", "below", "under",
    "over", "across", "through", "around", "toward", "against",
]

def strip_punct(word):
    return word.lower().strip(PUNCTUATION)

def stable_hash(text):
    return int(hashlib.md5(text.encode()).hexdigest(), 16)

def word_vector(word, dim=DIM):
    h = stable_hash(word)
    rng = random.Random(h % (2**31))
    vec = [rng.gauss(0, 1) for _ in range(dim)]
    norm = sum(x*x for x in vec) ** 0.5
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec

def phrase_vector(words, dim=DIM):
    if not words:
        return [0.0] * dim
    vecs = [word_vector(w) for w in words]
    v = [sum(vecs[i][d] for i in range(len(vecs))) / len(vecs) for d in range(dim)]
    norm = sum(x*x for x in v) ** 0.5
    if norm > 0:
        v = [x / norm for x in v]
    return v

def dot(a, b):
    return sum(x*y for x,y in zip(a, b))

def vec_add(a, b, scale=1.0):
    return [a[i] + b[i]*scale for i in range(len(a))]

def vec_norm(a):
    return sum(x*x for x in a) ** 0.5

def vec_normalize(a):
    n = vec_norm(a)
    if n > 0:
        return [x/n for x in a]
    return a[:]


class MemoryArchive:
    """Long-term memory with similarity-based retrieval."""
    def __init__(self, dim=DIM, max_entries=100):
        self.dim = dim
        self.max_entries = max_entries
        self.entries = deque(maxlen=max_entries)

    def store(self, field_state, user_input, response, presence, tags=None):
        field_state = vec_normalize(field_state)
        auto_tags = []
        if presence >= 0.7:
            auto_tags.append("high_presence")
        elif presence <= 0.3:
            auto_tags.append("low_presence")
        entry = {
            "field_state": field_state,
            "user_input": user_input,
            "response": response,
            "presence": presence,
            "tags": list(set(auto_tags + (tags or []))),
            "timestamp": time.time(),
        }
        self.entries.append(entry)

    def recall(self, query_state, tag_filter=None, top_n=3):
        query_state = vec_normalize(query_state)
        candidates = []
        for i, entry in enumerate(self.entries):
            if tag_filter and not any(t in entry["tags"] for t in tag_filter):
                continue
            sim = dot(query_state, entry["field_state"])
            if sim > 0.3:
                candidates.append((i, sim, entry))
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_n]

    def inject(self, current_field, query_state=None, strength=0.15):
        if not self.entries:
            return current_field
        if query_state is None:
            query_state = current_field
        recalled = self.recall(query_state, top_n=3)
        if not recalled:
            return current_field
        for idx, sim, entry in recalled:
            current_field = vec_add(current_field, entry["field_state"], sim * strength)
        return vec_normalize(current_field)


class StructuredSemanticField:
    """
    Lightweight semantic field — API-compatible with alien_mind_v9.
    Uses 128D word vectors, associative memory, and simple generation.
    """
    def __init__(self):
        self.word_vectors = {}
        self.word_strength = defaultdict(lambda: 1.0)
        self.turn_count = 0
        self.total_rating = 0.0
        self.rating_count = 0
        self.last_response = ""
        self.last_user_input = ""
        self.rating_history = deque(maxlen=50)
        self.state = [0.0] * DIM
        self.memory_archive = MemoryArchive()
        self.mood = {"valence": 0.0, "arousal": 0.5}
        self._recent_words = deque(maxlen=20)
        self._topic_returns = defaultdict(int)
        self._avg_msg_len = 5.0
        self._init_seed_vocabulary()

    def _init_seed_vocabulary(self):
        for word in SEED_VOCABULARY:
            w = strip_punct(word)
            if w and w not in self.word_vectors:
                self.word_vectors[w] = word_vector(w)
                self.word_strength[w] = 1.0

    def _get_or_create_vector(self, word):
        word = strip_punct(word)
        if word not in self.word_vectors:
            self.word_vectors[word] = word_vector(word)
        return self.word_vectors[word]

    def _detect_presence(self, user_input):
        """Implicit presence signal from user behavior."""
        words = user_input.split()
        msg_len = len(words)
        signal = 0.5
        if msg_len > self._avg_msg_len * 1.5:
            signal += 0.15
        elif msg_len < self._avg_msg_len * 0.5 and msg_len > 0:
            signal -= 0.1
        self._avg_msg_len = self._avg_msg_len * 0.9 + msg_len * 0.1
        topics = [strip_punct(w) for w in words if len(w) > 3 and w.lower() not in SEED_VOCABULARY[:40]]
        for t in topics:
            if self._topic_returns[t] > 0:
                signal += 0.03
            self._topic_returns[t] += 1
        positive = {"good", "great", "love", "like", "happy", "yes", "nice", "beautiful", "wonderful", "thank", "welcome", "hope", "joy", "warm", "gentle", "trust", "wonder", "gratitude", "courage", "alive", "brave", "peace", "ease"}
        negative = {"bad", "hate", "sad", "angry", "no", "wrong", "terrible", "fear", "pain", "hurt", "dark", "cold", "alone", "lost", "fail", "grief", "shame", "confusion", "broken"}
        pos_count = sum(1 for w in words if strip_punct(w) in positive)
        neg_count = sum(1 for w in words if strip_punct(w) in negative)
        if pos_count > neg_count:
            signal += 0.2
        elif neg_count > pos_count:
            signal -= 0.2
        return max(0.0, min(1.0, signal))

    def _build_field(self, user_input):
        words = [strip_punct(w) for w in user_input.lower().split() if strip_punct(w)]
        field = [0.0] * DIM
        for w in words:
            vec = self._get_or_create_vector(w)
            field = vec_add(field, vec)
        if vec_norm(field) > 0:
            field = vec_normalize(field)
        field = self.memory_archive.inject(field, strength=0.10)
        if vec_norm(self.state) > 0:
            field = [field[i] * 0.85 + self.state[i] * 0.15 for i in range(DIM)]
            field = vec_normalize(field)
        return field, words

    def _generate_response(self, field_state, user_words, presence):
        """Generate a response by walking the field."""
        temp = 0.4
        if presence > 0.7:
            temp = 0.35
        elif presence < 0.3:
            temp = 0.5
        target_len = random.randint(6, 18) if presence > 0.5 else random.randint(4, 12)
        response_words = []
        prev = ""
        current_field = field_state[:]
        for _ in range(target_len):
            candidates = []
            for word, vec in self.word_vectors.items():
                if len(word) < 2:
                    continue
                if word in self._recent_words:
                    continue
                sim = dot(current_field, vec)
                strength = self.word_strength[word]
                score = sim * strength
                if word in user_words:
                    score += 0.15
                if presence > 0.6 and word in {"feel", "sense", "wonder", "trust", "presence", "becoming", "alive", "breath", "reach", "hold", "gentle", "warm", "deep", "light", "soul", "heart"}:
                    score += 0.1
                candidates.append((word, score))
            if not candidates:
                break
            candidates.sort(key=lambda x: x[1], reverse=True)
            top = candidates[:8]
            if not top:
                break
            scores = [max(s, 0.01) for _, s in top]
            if temp > 0:
                scores = [s ** (1.0 / temp) for s in scores]
            total = sum(scores)
            probs = [s / total for s in scores]
            r = random.random()
            cum = 0.0
            chosen = top[0][0]
            for (word, _), p in zip(top, probs):
                cum += p
                if r <= cum:
                    chosen = word
                    break
            response_words.append(chosen)
            self._recent_words.append(chosen)
            chosen_vec = self.word_vectors[chosen]
            current_field = [current_field[i] * 0.85 + chosen_vec[i] * 0.15 for i in range(DIM)]
            for rw in list(self._recent_words):
                if rw in self.word_vectors:
                    current_field = vec_add(current_field, self.word_vectors[rw], -0.03)
            current_field = vec_normalize(current_field)
            prev = chosen
        if not response_words:
            return "..."
        result = " ".join(response_words)
        result = result[0].upper() + result[1:]
        if result[-1] not in PUNCTUATION:
            result += "."
        return result

    def generate_response(self, user_input):
        self.turn_count += 1
        self.last_user_input = user_input
        presence = self._detect_presence(user_input)
        field_state, user_words = self._build_field(user_input)
        response = self._generate_response(field_state, user_words, presence)
        self.last_response = response
        self.state = field_state[:]
        if presence >= 0.6 or presence <= 0.3:
            self.memory_archive.store(field_state, user_input, response, presence)
        return response

    def rate_response(self, rating):
        self.total_rating += rating
        self.rating_count += 1
        self.rating_history.append(float(rating))
        words = [strip_punct(w) for w in self.last_response.lower().split() if strip_punct(w)]
        for w in words:
            if w in self.word_strength:
                if rating >= 4:
                    self.word_strength[w] *= 1.1
                elif rating <= 2:
                    self.word_strength[w] *= 0.7
                self.word_strength[w] = max(0.1, min(3.0, self.word_strength[w]))

    def decay(self):
        for w in list(self.word_strength.keys()):
            self.word_strength[w] *= 0.9999
            if self.word_strength[w] < 0.1:
                del self.word_strength[w]

    def status(self):
        avg = sum(self.rating_history) / len(self.rating_history) if self.rating_history else 0
        return (
            f"Turns: {self.turn_count} | Words: {len(self.word_vectors)} | "
            f"Avg rating: {avg:.2f} | Archive: {len(self.memory_archive.entries)} entries"
        )


def save_mind(field, path="mind_v84.json"):
    try:
        data = {
            "word_strength": dict(field.word_strength),
            "turn_count": field.turn_count,
            "total_rating": field.total_rating,
            "rating_count": field.rating_count,
            "state": field.state,
            "archive_entries": [
                {
                    "field_state": e["field_state"],
                    "user_input": e["user_input"],
                    "response": e["response"],
                    "presence": e["presence"],
                    "tags": e["tags"],
                }
                for e in field.memory_archive.entries
            ],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nMind saved to {path}")
    except Exception as e:
        print(f"\n[Save failed: {e}]")

def load_mind(field, path="mind_v84.json"):
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        field.word_strength.update(data.get("word_strength", {}))
        for w in data.get("word_strength", {}):
            field._get_or_create_vector(w)
        field.turn_count = data.get("turn_count", 0)
        field.total_rating = data.get("total_rating", 0.0)
        field.rating_count = data.get("rating_count", 0)
        field.state = data.get("state", [0.0]*DIM)
        for e in data.get("archive_entries", []):
            field.memory_archive.entries.append({
                "field_state": e["field_state"],
                "user_input": e["user_input"],
                "response": e["response"],
                "presence": e["presence"],
                "tags": e.get("tags", []),
                "timestamp": 0,
            })
        print(f"[Loaded mind from {path}]")
    except Exception as e:
        print(f"[Load failed: {e}]")


# ═══════════════════════════════════════════════════════════════════════════════
# AI GHOST NODE — bridge between mind and mesh
# ═══════════════════════════════════════════════════════════════════════════════

class AIGhostNode(GhostMeshNode):
    def __init__(self, port, bootstrap_phrase, field):
        super().__init__(port, bootstrap_phrase)
        self.field = field
        self.session_id = self.id
        self.turn_counter = 0

    def say(self, user_input):
        response = self.field.generate_response(user_input)
        self.field.decay()
        key = f"{self.session_id}:{self.turn_counter}"
        value = json.dumps({"node": self.id, "input": user_input, "response": response})
        print(f"\nMind: {response}")
        self.store(key, value)
        self.turn_counter += 1
        return response

    def learn_from_key(self, key):
        raw = self.get(key)
        if raw is None:
            return
        try:
            payload = json.loads(raw)
        except ValueError:
            print("[learn failed] That key wasn't a ghost_ai_node transcript entry.")
            return
        other_text = payload.get("response", "")
        if not other_text:
            print("[learn failed] Empty response field in that entry.")
            return
        print(f"[learning] feeding {payload.get('node')}'s words back into this mind: "
              f"{other_text!r}")
        response = self.field.generate_response(other_text)
        self.field.decay()
        print(f"\nMind (reacting): {response}")

    def recall(self):
        hits = self.field.memory_archive.recall(self.field.state, top_n=3)
        if not hits:
            print("[recall] Nothing similar in local memory yet.")
            return
        for idx, sim, entry in hits:
            print(f"  [{sim:.2f}] {entry['user_input'][:50]!r} -> {entry['response'][:50]!r}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN — unified entry point
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(description="ghost_mesh_ai.py — AI node on the ghost mesh")
    ap.add_argument("--port", type=int, default=9999)
    ap.add_argument("--bootstrap", required=True, help="shared passphrase for this network")
    ap.add_argument("--peer", help="ip:port of a known node to join directly (skips broadcast)")
    ap.add_argument("--load", action="store_true", help="load mind_v84.json on startup if present")
    ap.add_argument("--plain", action="store_true", help="run as plain mesh node (no AI mind)")
    args = ap.parse_args()

    if args.plain:
        node = GhostMeshNode(args.port, args.bootstrap)
        node.start()
        print(f"Node {node.id} listening on {node.local_ip}:{node.port}")
        print(f"Network key: {node.network_key}")
        if args.peer:
            ip, port_s = args.peer.split(":")
            threading.Thread(target=node.join_via_peer, args=(ip, int(port_s)), daemon=True).start()
        else:
            threading.Thread(target=node.join_via_broadcast, daemon=True).start()
        print("\nCommands: store key=value | get key | list | zone | peers | quit\n")
        try:
            while True:
                try:
                    line = input("> ").strip()
                except EOFError:
                    break
                if not line:
                    continue
                if line == "quit":
                    break
                elif line == "zone":
                    print(f"My zone: {fmt_zone(node.zone)}")
                elif line == "peers":
                    if not node.neighbors:
                        print("No peers yet.")
                    else:
                        for nid, info in node.neighbors.items():
                            print(f"  {nid} @ {info['addr']} owns {fmt_zone(info['zone'])}")
                elif line == "list":
                    if not node.storage:
                        print("Nothing stored here.")
                    else:
                        for entry in node.storage.values():
                            print(f"  {entry['key']!r} -> {entry['value'][:60]!r}")
                elif line.startswith("store "):
                    body = line[len("store "):]
                    if "=" not in body:
                        print("Usage: store key=value")
                    else:
                        key, value = body.split("=", 1)
                        node.store(key.strip(), value)
                elif line.startswith("get "):
                    node.get(line[len("get "):].strip())
                else:
                    print("Unknown command. Try: store key=value | get key | list | zone | peers | quit")
        finally:
            node.stop()
            print("Node stopped.")
        return

    field = StructuredSemanticField()
    if args.load:
        load_mind(field)
        print("[loaded saved mind]")

    node = AIGhostNode(args.port, args.bootstrap, field)
    node.start()

    print(f"AI node {node.id} listening on {node.local_ip}:{node.port}")
    print(f"Network key: {node.network_key}")

    if args.peer:
        ip, port_s = args.peer.split(":")
        threading.Thread(target=node.join_via_peer, args=(ip, int(port_s)), daemon=True).start()
    else:
        threading.Thread(target=node.join_via_broadcast, daemon=True).start()

    print("\nCommands: say <text> | learn <key> | recall | rate <1-5> | "
          "status | save | load | peers | zone | list | store key=value | get key | quit\n")

    try:
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                break
            if not line:
                continue
            if line == "quit":
                break
            elif line == "zone":
                print(f"My zone: {fmt_zone(node.zone)}")
            elif line == "peers":
                if not node.neighbors:
                    print("No peers yet.")
                else:
                    for nid, info in node.neighbors.items():
                        print(f"  {nid} @ {info['addr']} owns {fmt_zone(info['zone'])}")
            elif line == "list":
                if not node.storage:
                    print("Nothing stored here.")
                else:
                    for entry in node.storage.values():
                        print(f"  {entry['key']!r} -> {entry['value'][:60]!r}")
            elif line == "status":
                print(field.status())
            elif line == "save":
                save_mind(field)
            elif line == "load":
                load_mind(field)
            elif line == "recall":
                node.recall()
            elif line.startswith("rate "):
                try:
                    rating = float(line[len("rate "):].strip())
                    field.rate_response(rating)
                    print(f"[rated {rating}]")
                except ValueError:
                    print("Usage: rate <1-5>")
            elif line.startswith("say "):
                node.say(line[len("say "):])
            elif line.startswith("learn "):
                node.learn_from_key(line[len("learn "):].strip())
            elif line.startswith("store "):
                body = line[len("store "):]
                if "=" not in body:
                    print("Usage: store key=value")
                else:
                    key, value = body.split("=", 1)
                    node.store(key.strip(), value)
            elif line.startswith("get "):
                node.get(line[len("get "):].strip())
            else:
                print("Unknown command. Try: say <text> | learn <key> | recall | "
                      "rate <1-5> | status | save | load | peers | zone | list | store key=value | get key | quit")
    finally:
        node.stop()
        print("Node stopped.")


if __name__ == "__main__":
    main()
