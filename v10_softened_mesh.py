import subprocess
import time
import threading
import queue
import os
import shutil

def start_node(port, bootstrap, peer=None, load_mind=False):
    cmd = ["python3", "ghost_ai_node_v10.py", "--port", str(port), "--bootstrap", bootstrap]
    if peer:
        cmd.extend(["--peer", peer])
    if load_mind:
        cmd.append("--load")
    
    process = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, bufsize=1
    )
    q = queue.Queue()

    def reader():
        for line in process.stdout:
            q.put(line)

    threading.Thread(target=reader, daemon=True).start()
    return process, q

def send(process, line):
    process.stdin.write(line + "\n")
    process.stdin.flush()

def drain(q, seconds, label, stop_substrings=()):
    end = time.time() + seconds
    collected = []
    while time.time() < end:
        try:
            line = q.get(timeout=0.2)
        except queue.Empty:
            continue
        stripped = line.strip()
        if stripped:
            print(f"  [{label}] {stripped}")
        collected.append(line)
        if any(s in line for s in stop_substrings):
            break
    return collected

def main():
    bootstrap_phrase = "v10 softened mesh"
    print(f"--- Starting v10 Softened Mesh Orchestration ---")

    if os.path.exists("mind_v10_softened.json"):
        shutil.copy("mind_v10_softened.json", "mind_v84.json")
        print("Using mind_v10_softened.json as the base mind.")

    print("Starting Seed Node on port 9999 with softened mind...")
    node1, q1 = start_node(9999, bootstrap_phrase, load_mind=True)
    
    startup_output = drain(q1, 5, "N1", stop_substrings=("Commands:",))
    node_id = None
    for line in startup_output:
        if "AI node" in line:
            parts = line.split()
            node_id = parts[parts.index("node") + 1]
            break
    
    print(f"Node 1 ID: {node_id}")

    print("Starting Node 2 on port 10000 joining Seed...")
    node2, q2 = start_node(10000, bootstrap_phrase, peer="127.0.0.1:9999")
    drain(q2, 5, "N2", stop_substrings=("Commands:",))

    print("\n--- Verifying Mesh and Mind ---")
    print("Node 1 says 'Who are you?'")
    send(node1, "say Who are you?")
    drain(q1, 15, "N1", stop_substrings=("Mind:",))

    print("\n--- Node 2 learns from Node 1 ---")
    if node_id:
        key = f"{node_id}:0"
        print(f"Node 2 learning from {key}...")
        send(node2, "learn " + key)
        drain(q2, 15, "N2", stop_substrings=("Mind (reacting):",))
    else:
        print("Could not find Node 1 ID.")

    print("\n--- Shutting down nodes ---")
    for i, node in enumerate([node1, node2]):
        print(f"Stopping Node {i+1}...")
        try:
            send(node, "quit")
        except:
            pass
        node.terminate()

    print("Demo complete.")

if __name__ == "__main__":
    main()
