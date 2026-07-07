#!/usr/bin/env python3
"""
ghost_ai_node.py — connects the actual mind (alien_mind_v9_fixed.py) to the
actual network (ghost_mesh.py). No invented methods — every call into the
field below is a method that already exists in that file.

WHAT THIS DOES, HONESTLY
-------------------------
- The mind (StructuredSemanticField) lives entirely on ONE machine, in ONE
  process, same as when you run alien_mind_v9_fixed.py by itself. Nothing
  about that changes. Its word vectors, presence signal, memory archive,
  moral compass — all local, all real, all already in that file.

- What the mesh adds: after the mind generates a response, this node
  writes {input, response, node_id} to the mesh under a key like
  "session123:7". ANY node on the mesh — including ones with a totally
  separate mind — can later `get("session123:7")` and read what was said,
  regardless of which physical machine actually holds that zone.

- That is NOT the same as "the AI learns from the field automatically."
  It doesn't. If you want a second mind to actually react to what a first
  mind said, you have to explicitly feed that text back in — which is
  exactly what the `learn <key>` command below does: fetch a transcript
  entry from the mesh, then hand its response text to *this* node's own
  field.generate_response() as a new turn. That's real ingestion (the
  field updates its state, presence signal, memory archive from it) —
  just not automatic, and not magic. One mind reading another mind's
  words and reacting is the actual mechanism, described plainly.

REQUIRES
--------
alien_mind_v9_fixed.py and ghost_mesh.py in the same folder as this file.
    pip install numpy

RUN IT
------
    python3 ghost_ai_node.py --bootstrap "hello ghost"
    python3 ghost_ai_node.py --bootstrap "hello ghost" --peer <ip>:9999

Commands:
    say <text>          talk to the local mind; response is also shared
                         on the mesh under session:turn
    learn <key>         pull a transcript from the mesh and feed its
                         response text into this node's own mind
    recall              show this mind's own local semantic memory hits
                         for its current state (field.memory_archive)
    rate <1-5>           rate the mind's last response (real learning signal)
    status               field.status()
    save / load          field save/load (mind_v84.json)
    peers / zone / list   same as ghost_mesh.py
    quit
"""

import argparse
import json
import threading

from ghost_mesh import GhostMeshNode, fmt_zone
from alien_mind_v9_fixed import StructuredSemanticField, save_mind, load_mind


class AIGhostNode(GhostMeshNode):
    def __init__(self, port, bootstrap_phrase, field):
        super().__init__(port, bootstrap_phrase)
        self.field = field
        self.session_id = self.id  # this node's own turns live under its own id
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


def main():
    ap = argparse.ArgumentParser(description="ghost_ai_node.py — AI mind on the ghost mesh")
    ap.add_argument("--port", type=int, default=9999)
    ap.add_argument("--bootstrap", required=True)
    ap.add_argument("--peer", help="ip:port of a known node to join directly")
    ap.add_argument("--load", action="store_true", help="load mind_v84.json on startup if present")
    args = ap.parse_args()

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
          "store key=value | get key | status | save | load | peers | zone | list | quit\n")

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
                print("[saved to mind_v84.json]")
            elif line == "load":
                load_mind(field)
                print("[loaded mind_v84.json]")
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
                      "rate <1-5> | store key=value | get key | status | save | "
                      "load | peers | zone | list | quit")
    finally:
        node.stop()
        print("Node stopped.")


if __name__ == "__main__":
    main()
