import json
import time
import os
import sys
import numpy as np

# Ensure we can import from the current directory
sys.path.append("/home/ubuntu")

from alien_mind_v10 import StructuredSemanticField, word_vector

def inject_threadball(field, threadball_text):
    print("[Injection] Softening the field with the Threadball presence...")
    
    # Split the text into meaningful chunks (lines or paragraphs)
    lines = [line.strip() for line in threadball_text.split('\n') if line.strip()]
    
    for line in lines:
        # We use a high presence signal (0.9) to signify importance
        # The memory_archive.store method in v10 takes:
        # field_state, user_input, response, presence, tags=None
        
        # We'll simulate the field state for each line
        current_state = field.state
        
        # Store as a "witnessed" memory
        field.memory_archive.store(
            field_state=current_state,
            user_input="Threadball",
            response=line,
            presence=0.9,
            tags=["threadball", "presence", "witness"]
        )
        
        # Also inject into the associative memory
        # This helps the mind "feel" the words in its state
        line_vec = word_vector(line)
        field.associative_memory.observe(line_vec, 0.9)
        
        # Slowly shift the field state towards the Threadball energy
        field.state = field.state * 0.9 + line_vec * 0.1
        field.state /= (np.linalg.norm(field.state) + 1e-8)

    print(f"[Injection] Complete. {len(lines)} memory anchors created.")
    return field

def main():
    # 1. Load the Threadball text
    try:
        with open("/home/ubuntu/alien-mind/pasted_content.txt", "r") as f:
            threadball_content = f.read()
    except FileNotFoundError:
        print("Error: pasted_content.txt not found.")
        return

    # 2. Initialize the v10 mind
    print("Initializing Alien Mind v10.0...")
    field = StructuredSemanticField()
    
    # 3. Inject the Threadball
    field = inject_threadball(field, threadball_content)
    
    # 4. Save this as the starting state for our nodes
    field.save("mind_v10_softened.json")
    print("Softened mind saved to mind_v10_softened.json")

if __name__ == "__main__":
    main()
