import subprocess
import time
import threading
import queue


def start_node(port, bootstrap, peer=None):
    cmd = ["python3", "ghost_ai_node.py", "--port", str(port), "--bootstrap", bootstrap]
    if peer:
        cmd.extend(["--peer", peer])
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
    bootstrap_phrase = "ghost mesh demo"
    print(f"--- Starting Mesh Orchestration with phrase: '{bootstrap_phrase}' ---")

    print("Starting Seed Node on port 9999...")
    node1, q1 = start_node(9999, bootstrap_phrase)
    time.sleep(2)

    print("Starting Node 2 on port 10000 joining Seed...")
    node2, q2 = start_node(10000, bootstrap_phrase, peer="127.0.0.1:9999")
    time.sleep(2)

    print("Starting Node 3 on port 10001 joining Seed...")
    node3, q3 = start_node(10001, bootstrap_phrase, peer="127.0.0.1:9999")
    time.sleep(5)  # let gossip spread

    print("\n--- Verifying Mesh Connectivity ---")
    send(node1, "peers")
    print("Output from Node 1 (Seed):")
    drain(q1, 3, "N1", stop_substrings=("owns",))

    print("\n--- Demonstrating Distributed Storage ---")
    print("Storing 'meaning_of_life=42' on Node 2...")
    send(node2, "store meaning_of_life=42")
    drain(q2, 3, "N2")

    print("Retrieving 'meaning_of_life' from Node 3...")
    send(node3, "get meaning_of_life")
    print("Output from Node 3:")
    drain(q3, 4, "N3", stop_substrings=("found remotely", "found locally", "not found"))

    print("\n--- Demonstrating AI Interaction ---")
    print("Node 1 says 'Who are you?'")
    send(node1, "say Who are you?")
    print("Output from Node 1:")
    drain(q1, 5, "N1", stop_substrings=("Mind:",))

    print("\n--- Shutting down nodes ---")
    for i, node in enumerate([node1, node2, node3]):
        print(f"Stopping Node {i+1}...")
        try:
            send(node, "quit")
        except (BrokenPipeError, OSError):
            pass
        node.terminate()

    print("Demo complete.")


if __name__ == "__main__":
    main()
