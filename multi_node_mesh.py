import subprocess
import time
import os
import signal

def start_node(port, bootstrap, peer=None, is_ai=True):
    cmd = ["python3", "ghost_mesh_ai.py", "--port", str(port), "--bootstrap", bootstrap]
    if peer:
        cmd.extend(["--peer", peer])
    
    # Use a pipe for stdin to send commands later if needed
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    return process

def main():
    bootstrap_phrase = "ghost mesh demo"
    nodes = []
    
    print(f"--- Starting Mesh Orchestration with phrase: '{bootstrap_phrase}' ---")
    
    # 1. Start the first node (Seed)
    print("Starting Seed Node on port 9999...")
    node1 = start_node(9999, bootstrap_phrase)
    nodes.append(node1)
    time.sleep(2) # Give it time to bind
    
    # 2. Start second node joining the first
    print("Starting Node 2 on port 10000 joining Seed...")
    node2 = start_node(10000, bootstrap_phrase, peer="127.0.0.1:9999")
    nodes.append(node2)
    time.sleep(2)
    
    # 3. Start third node joining the first
    print("Starting Node 3 on port 10001 joining Seed...")
    node3 = start_node(10001, bootstrap_phrase, peer="127.0.0.1:9999")
    nodes.append(node3)
    time.sleep(5) # Wait for gossip to spread
    
    print("\n--- Verifying Mesh Connectivity ---")
    
    # Send 'peers' command to Node 1
    node1.stdin.write("peers\n")
    node1.stdin.flush()
    time.sleep(1)
    
    # Read output from Node 1
    print("Output from Node 1 (Seed):")
    for _ in range(10):
        line = node1.stdout.readline()
        if line:
            print(f"  [N1] {line.strip()}")
        if "owns" in line: # Found a peer
            break

    # 4. Demonstrate Data Storage across nodes
    print("\n--- Demonstrating Distributed Storage ---")
    print("Storing 'meaning_of_life=42' on Node 2...")
    node2.stdin.write("store meaning_of_life=42\n")
    node2.stdin.flush()
    time.sleep(2)
    
    print("Retrieving 'meaning_of_life' from Node 3...")
    node3.stdin.write("get meaning_of_life\n")
    node3.stdin.flush()
    time.sleep(2)
    
    # Capture Node 3 output to verify retrieval
    print("Output from Node 3:")
    for _ in range(15):
        line = node3.stdout.readline()
        if line:
            print(f"  [N3] {line.strip()}")
        if "found remotely" in line or "found locally" in line:
            break

    # 5. Demonstrate AI interaction
    print("\n--- Demonstrating AI Interaction ---")
    print("Node 1 says 'Who are you?'")
    node1.stdin.write("say Who are you?\n")
    node1.stdin.flush()
    time.sleep(3)
    
    print("Output from Node 1:")
    for _ in range(10):
        line = node1.stdout.readline()
        if line:
            print(f"  [N1] {line.strip()}")
        if "AI:" in line:
            break

    # Cleanup
    print("\n--- Shutting down nodes ---")
    for i, node in enumerate(nodes):
        print(f"Stopping Node {i+1}...")
        node.stdin.write("quit\n")
        node.stdin.flush()
        node.terminate()
        
    print("Demo complete.")

if __name__ == "__main__":
    main()
