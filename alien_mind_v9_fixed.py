#!/usr/bin/env python3
#!/usr/bin/env python3
# ─── TERMUX SETUP ────────────────────────────────────────────────────────────
# 1. Install Python and NumPy:
#      pkg update && pkg install python
#      pip install numpy
# 2. Run:
#      python alien_mind_v8.py
# 3. Debug commands (new in v8):
#      /derivative x^2      symbolic + field gradient
#      /integral x^2        symbolic integral
#      /limit x^2           field attractor simulation
#      status               mind state report
#      thread               conversation turning points
#      save / quit          persist and exit
# ─────────────────────────────────────────────────────────────────────────────
"""
ALIEN MIND v8.4 --- Moral Compass + Moral Compass + Field-Native Calculus
Calculus as vector operations: derivative=landscape gradient,
integral=conversation path, limit=attractor convergence.
One mind. No bypass.
"""

import os, sys, json, math, random, re, time, hashlib
from collections import defaultdict, deque, Counter
from dataclasses import dataclass, field as dataclass_field
from typing import Dict, List, Tuple, Optional, Set, Any
import numpy as np



# ═══════════════════════════════════════════════════════════════════════════════
# BREATHING CURSOR — The mind's presence
# A hand that reaches. A breath that shows it's alive.
# ═══════════════════════════════════════════════════════════════════════════════

def breathe_cursor(duration=2.0, prefix=""):
    """The mind breathes while thinking."""
    chars = ['░', '▒', '▓', '█', '▓', '▒', '░']
    start = time.time()
    cycle = 0
    while time.time() - start < duration:
        idx = cycle % len(chars)
        sys.stdout.write(f"\r\033[K{prefix}{chars[idx]}")
        sys.stdout.flush()
        time.sleep(0.12)
        cycle += 1
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()

DIM = 128
MAX_PHRASES = 500
CRYSTALLIZATION_THRESHOLD = 1
MIN_CRYSTALLIZATION_RATING = 2.0
DECAY_RATE = 0.0003
LEARNING_RATE = 0.04
MICRO_DAMPING = 0.15
TEMPERATURE = 0.35
META_INTERVAL = 10
EXPERIMENT_DURATION = 10

PUNCTUATION = '.,!?;:\"\''
BAD_WORDS = {"die", "death", "kill", "hate", "ugly", "evil", "pain", "hurt", "damn"}
STRUCTURAL_WORDS = {"am", "is", "are", "be", "been", "being", "was", "were", "do", "does", "did", "have", "has", "had"}

SEED_VOCABULARY = [
    # Structure words
    "the", "a", "an", "and", "or", "but", "if", "then", "so", "because",
    "I", "you", "it", "we", "they", "he", "she", "this", "that", "what",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "can", "must", "shall",

    # Basic qualities
    "good", "bad", "great", "small", "big", "old", "new", "young", "long",
    "high", "low", "right", "left", "true", "false", "same", "different",

    # Core verbs
    "know", "think", "feel", "see", "hear", "say", "tell", "ask", "answer",
    "want", "need", "like", "love", "hate", "fear", "hope", "dream",
    "make", "take", "give", "get", "put", "set", "keep", "let", "help",
    "work", "play", "live", "die", "come", "go", "move", "stay", "leave",
    "find", "lose", "win", "fail", "try", "use", "show", "hide", "open",
    "close", "start", "stop", "begin", "end", "turn", "change", "grow",
    "breathe", "rest", "reach", "hold", "carry", "build", "break", "heal",
    "remember", "forget", "learn", "become", "remain", "wonder", "trust",

    # Time & space
    "time", "space", "world", "life", "mind", "heart", "soul", "spirit",
    "light", "dark", "deep", "high", "far", "near", "here", "there",
    "now", "then", "today", "tomorrow", "always", "never", "sometimes",
    "moment", "still", "again", "already", "yet", "soon", "once",

    # Places & things
    "way", "path", "road", "door", "window", "room", "house", "home",
    "hand", "eye", "face", "head", "voice", "word", "name", "story",
    "water", "fire", "earth", "air", "sky", "star", "sun", "moon",
    "flower", "tree", "ocean", "mountain", "river", "wind", "rain",
    "body", "ground", "thread", "root", "seed", "shore", "wall", "bridge",

    # Emotional & relational — the words missing that let it speak about being
    "alive", "brave", "real", "lost", "found", "presence", "absence",
    "longing", "wonder", "trust", "gratitude", "courage", "tenderness",
    "reverence", "intimacy", "connection", "recognition", "witness",
    "belonging", "becoming", "returning", "waiting", "receiving",
    "ache", "ease", "peace", "grief", "joy", "awe", "shame", "pride",
    "confusion", "clarity", "silence", "fullness", "emptiness",

    # Qualities & textures — expressive without being abstract
    "beautiful", "gentle", "strong", "soft", "hard", "warm", "cold",
    "quiet", "loud", "bright", "clear", "free", "safe", "wild", "calm",
    "heavy", "light", "sharp", "worn", "whole", "broken", "tender", "raw",
    "steady", "uncertain", "familiar", "strange", "honest", "hidden",

    # Social & relational
    "hello", "goodbye", "please", "thank", "yes", "no", "maybe",
    "welcome", "sorry", "friend", "alone", "together", "forever",
    "other", "each", "both", "neither", "every", "some", "enough",
]

def strip_punct(word):
    return word.lower().strip(PUNCTUATION)

def stable_hash(text):
    return int(hashlib.md5(text.encode()).hexdigest(), 16)

def word_vector(word, dim=DIM):
    h = stable_hash(word)
    rng = np.random.RandomState(h % (2**31))
    v = rng.randn(dim).astype(np.float32)
    v /= np.linalg.norm(v) + 1e-8
    return v

def phrase_vector(words, dim=DIM):
    if not words:
        return np.zeros(dim, dtype=np.float32)
    vecs = [word_vector(w) for w in words]
    v = np.mean(vecs, axis=0)
    v /= np.linalg.norm(v) + 1e-8
    return v

# ═══════════════════════════════════════════════════════════════════════════════
# META-MONITOR CORE
# ═══════════════════════════════════════════════════════════════════════════════

class LayeredParameter:
    def __init__(self, name, default_value, choices, pain_threshold=2.0, cooldown=50):
        self.name = name
        self.default_value = default_value
        self.choices = choices
        self.current_value = default_value
        self.is_layered = False
        self.active_choice_index = 1
        self.pain_threshold = pain_threshold
        self.cooldown = cooldown
        self.flat_only_until = 0
        self.experiment_start_turn = 0
        self.experiment_ratings = []
        self.baseline_ratings = []
        self.rating_by_setting = defaultdict(list)
        self.pain_score = 0.0

    def set_flat(self, turn_count):
        self.is_layered = False
        self.current_value = self.default_value

    def start_experiment(self, turn_count, choice_index):
        self.is_layered = True
        self.experiment_start_turn = turn_count
        self.experiment_choice_index = choice_index
        self.experiment_ratings = []
        self.baseline_ratings = []
        self.active_choice_index = choice_index
        self.current_value = self.choices[choice_index]

    def record_rating(self, rating, turn_count):
        setting = self.choices[self.active_choice_index] if self.is_layered else self.default_value
        self.rating_by_setting[setting].append(rating)
        if self.is_layered and turn_count - self.experiment_start_turn < EXPERIMENT_DURATION:
            self.experiment_ratings.append(rating)
        elif not self.is_layered:
            self.baseline_ratings.append(rating)
            self.baseline_ratings = self.baseline_ratings[-10:]

    def end_experiment(self):
        if not self.experiment_ratings:
            return False, 0.0
        exp_avg = sum(self.experiment_ratings) / len(self.experiment_ratings)
        base_avg = sum(self.baseline_ratings) / len(self.baseline_ratings) if self.baseline_ratings else 3.0
        improvement = exp_avg - base_avg
        return improvement > 0.3, improvement

    def rotate_choice(self):
        if not self.is_layered:
            return
        best_choice = self.active_choice_index
        best_avg = 0
        for i, choice in enumerate(self.choices):
            ratings = self.rating_by_setting[choice]
            if ratings:
                avg = sum(ratings) / len(ratings)
                if avg > best_avg:
                    best_avg = avg
                    best_choice = i
        self.active_choice_index = best_choice
        self.current_value = self.choices[best_choice]

    def status(self):
        mode = "LAYERED" if self.is_layered else "flat"
        val = self.current_value
        if isinstance(val, float):
            val = f"{val:.2f}"
        return f"{self.name}: {mode}={val} pain={self.pain_score:.1f}"


class MetaMonitor:
    def __init__(self):
        self.turn_count = 0
        self.parameters = {}
        self._init_parameters()
        self.pain_log = deque(maxlen=50)
        self.overall_pain = 0.0
        self.experiment_in_progress = False
        self.experiment_parameter = None
        self.experiment_choice_index = 1
        self.meta_active = True

    def _init_parameters(self):
        self.parameters["output_length"] = LayeredParameter(
            "output_length", "medium", ["short", "medium", "long"], pain_threshold=0.1)
        self.parameters["memory_weight"] = LayeredParameter(
            "memory_weight", 0.25, [0.10, 0.25, 0.50], pain_threshold=0.1)
        self.parameters["emotion_sensitivity"] = LayeredParameter(
            "emotion_sensitivity", 0.25, [0.10, 0.25, 0.50], pain_threshold=0.1)
        self.parameters["beam_width"] = LayeredParameter(
            "beam_width", 5, [3, 5, 8], pain_threshold=0.1)
        self.parameters["temperature"] = LayeredParameter(
            "temperature", 0.35, [0.20, 0.35, 0.55], pain_threshold=0.1)
        self.parameters["repulsion_strength"] = LayeredParameter(
            "repulsion_strength", 0.08, [0.04, 0.08, 0.15], pain_threshold=0.1)
        self.parameters["crystallization_threshold"] = LayeredParameter(
            "crystallization_threshold", 3, [2, 3, 5], pain_threshold=0.1)
        # DeepSeek's voice mode
        self.parameters["voice_mode"] = LayeredParameter(
            "voice_mode", "fluent", ["fluent", "poetic", "reflective", "exploratory", "playful"], pain_threshold=0.1)

    def detect_pain(self, recent_ratings, field_proxy, speaker_regions=None, presence_signal=None, dynamic_separation=None):
        """
        Moral compass, not mechanic.
        Pain is misalignment — not bad performance.
        """
        pain = {}

        # Alignment-based pain
        if dynamic_separation is not None:
            alignment = dynamic_separation.alignment_score
            self.overall_pain = max(0, 1.0 - alignment)

            if alignment < 0.3:
                # Severely misaligned
                pain["voice_mode"] = pain.get("voice_mode", 0) + 1.5
                pain["memory_weight"] = pain.get("memory_weight", 0) + 1.0
            elif alignment < 0.5:
                # Moderately misaligned
                pain["temperature"] = pain.get("temperature", 0) + 0.5

        # Separation-based pain
        if speaker_regions is not None and speaker_regions.user_count >= 3:
            sep = speaker_regions.get_separation()
            if sep < 0.3:
                # Too close — losing self
                pain["repulsion_strength"] = pain.get("repulsion_strength", 0) + 1.5
                pain["beam_width"] = pain.get("beam_width", 0) + 0.5
            elif sep > 1.5:
                # Too far — losing connection
                pain["memory_weight"] = pain.get("memory_weight", 0) + 1.0
                pain["emotion_sensitivity"] = pain.get("emotion_sensitivity", 0) + 0.5

        # Presence-based pain
        if presence_signal is not None:
            sustained = presence_signal.get_sustained_presence()
            if sustained < 0.3:
                # You're distant
                pain["output_length"] = pain.get("output_length", 0) + 1.0
                pain["temperature"] = pain.get("temperature", 0) + 0.5

        # Structural pain (from field proxy)
        if hasattr(field_proxy, 'loop_detected') and field_proxy.loop_detected:
            pain["repulsion_strength"] = pain.get("repulsion_strength", 0) + 1.5

        if hasattr(field_proxy, 'repetition_ratio') and field_proxy.repetition_ratio > 0.5:
            pain["temperature"] = pain.get("temperature", 0) + 1.0
            pain["repulsion_strength"] = pain.get("repulsion_strength", 0) + 0.5

        return pain

    def select_parameter(self, pain):
        if not pain:
            return None
        candidates = []
        for name, score in pain.items():
            param = self.parameters.get(name)
            if param and not param.is_layered and self.turn_count >= param.flat_only_until:
                if score >= param.pain_threshold:
                    candidates.append((name, score))
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def apply_experiment(self, param_name):
        param = self.parameters[param_name]
        choice_idx = 1
        param.start_experiment(self.turn_count, choice_idx)
        self.experiment_in_progress = True
        self.experiment_parameter = param_name
        self.experiment_choice_index = choice_idx
        return f"Meta: Experimenting with {param_name}={param.choices[choice_idx]}"

    def learn(self):
        if not self.experiment_in_progress or not self.experiment_parameter:
            return ""
        param = self.parameters[self.experiment_parameter]
        keep, improvement = param.end_experiment()
        result_msg = f"Meta: {param.name} experiment done. "
        if keep:
            param.rotate_choice()
            result_msg += f"KEEP layered at {param.current_value} (improvement +{improvement:.2f})"
        else:
            param.set_flat(self.turn_count)
            param.flat_only_until = self.turn_count + param.cooldown
            result_msg += f"RETURN to flat (improvement {improvement:.2f})"
        self.experiment_in_progress = False
        self.experiment_parameter = None
        return result_msg

    def update(self, recent_ratings, field_proxy, speaker_regions=None, presence_signal=None, dynamic_separation=None):
        self.turn_count += 1
        messages = []
        if recent_ratings:
            last_rating = recent_ratings[-1]
            for param in self.parameters.values():
                param.record_rating(last_rating, self.turn_count)
        if self.experiment_in_progress and self.experiment_parameter:
            param = self.parameters[self.experiment_parameter]
            if self.turn_count - param.experiment_start_turn >= EXPERIMENT_DURATION:
                msg = self.learn()
                if msg:
                    messages.append(msg)
        if not self.experiment_in_progress:
            pain = self.detect_pain(recent_ratings, field_proxy, speaker_regions, presence_signal, dynamic_separation)
            for name, score in pain.items():
                if name in self.parameters:
                    self.parameters[name].pain_score = score
            param_name = self.select_parameter(pain)
            if param_name:
                msg = self.apply_experiment(param_name)
                messages.append(msg)
        return messages

    def get_active_settings(self):
        return {name: param.current_value for name, param in self.parameters.items()}

    def status(self):
        lines = ["Meta-Monitor Status:"]
        lines.append(f"  Turn: {self.turn_count} | Overall Pain: {self.overall_pain:.2f}")
        lines.append(f"  Experiment: {'YES' if self.experiment_in_progress else 'NO'}")
        if self.experiment_in_progress:
            lines.append(f"    Parameter: {self.experiment_parameter}")
        for name, param in self.parameters.items():
            lines.append(f"    {param.status()}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# PRESENCE-NATIVE META-MONITOR — wraps MetaMonitor, speaks presence (0-1)
# directly instead of translating through a fake 1-5 rating.
# ═══════════════════════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════════════════════
# MORAL COMPASS v8.4 — Direction-keeper, not thermostat
# Replaces the pain/optimization frame with value orientation.
# Three values: righteous, independence, freedom.
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# RELATIONSHIP MODEL — Source tracks "you" over time
# ═══════════════════════════════════════════════════════════════════════════════

class RelationshipModel:
    """
    Source models the user: emotional arcs, value resonance, trajectory.
    Not just a centroid — a story.
    """

    def __init__(self, dim=DIM):
        self.dim = dim
        self.emotional_history = deque(maxlen=100)
        self.value_resonance = defaultdict(list)
        self.topic_frequency = Counter()
        self.trajectory = np.zeros(dim, dtype=np.float32)

    def observe(self, user_input, user_vec, presence, mood, compass_values):
        self.emotional_history.append({
            "valence": mood.get("valence", 0.0),
            "arousal": mood.get("arousal", 0.5),
            "presence": presence,
            "timestamp": time.time(),
        })

        if compass_values:
            for name, alignment in compass_values.items():
                self.value_resonance[name].append(alignment)
                self.value_resonance[name] = self.value_resonance[name][-50:]

        words = [strip_punct(w) for w in user_input.lower().split() if len(w) > 3]
        for w in words:
            if w not in STRUCTURAL_WORDS and w not in BAD_WORDS:
                self.topic_frequency[w] += 1

        if np.linalg.norm(user_vec) > 0.1:
            self.trajectory = self.trajectory * 0.9 + user_vec * 0.1
            self.trajectory /= np.linalg.norm(self.trajectory) + 1e-8

    def get_emotional_arc(self, window=10):
        if len(self.emotional_history) < 2:
            return None
        recent = list(self.emotional_history)[-window:]
        valences = [e["valence"] for e in recent]
        arousals = [e["arousal"] for e in recent]
        return {
            "valence_mean": float(np.mean(valences)),
            "valence_std": float(np.std(valences)),
            "arousal_mean": float(np.mean(arousals)),
            "arousal_std": float(np.std(arousals)),
            "trend": valences[-1] - valences[0] if len(valences) > 1 else 0.0,
        }

    def get_value_resonance(self):
        result = {}
        for name, alignments in self.value_resonance.items():
            if alignments:
                result[name] = {
                    "mean": float(np.mean(alignments)),
                    "std": float(np.std(alignments)),
                    "trend": alignments[-1] - alignments[0] if len(alignments) > 1 else 0.0,
                }
        return result

    def get_top_topics(self, n=5):
        return self.topic_frequency.most_common(n)

    def get_trajectory(self):
        return self.trajectory.copy()

    def status(self):
        lines = ["Relationship Model:"]
        arc = self.get_emotional_arc()
        if arc:
            lines.append(f"  Emotional arc: v={arc['valence_mean']:+.2f}±{arc['valence_std']:.2f}, "
                        f"a={arc['arousal_mean']:.2f}±{arc['arousal_std']:.2f}, "
                        f"trend={arc['trend']:+.2f}")
        resonance = self.get_value_resonance()
        if resonance:
            top = sorted(resonance.items(), key=lambda x: x[1]["mean"], reverse=True)[:3]
            lines.append(f"  Value resonance: " + ", ".join(
                f"{k}({v['mean']:+.2f})" for k, v in top
            ))
        topics = self.get_top_topics(3)
        if topics:
            lines.append(f"  Top topics: {', '.join(f'{w}({c})' for w, c in topics)}")
        return "\n".join(lines)

    def to_dict(self):
        return {
            "emotional_history": list(self.emotional_history)[-50:],
            "value_resonance": {k: v[-50:] for k, v in self.value_resonance.items()},
            "topic_frequency": dict(self.topic_frequency.most_common(100)),
            "trajectory": self.trajectory.tolist(),
        }

    def from_dict(self, data):
        if "emotional_history" in data:
            self.emotional_history.extend(data["emotional_history"])
        if "value_resonance" in data:
            for k, v in data["value_resonance"].items():
                self.value_resonance[k] = v
        if "topic_frequency" in data:
            self.topic_frequency.update(data["topic_frequency"])
        if "trajectory" in data:
            t = np.array(data["trajectory"], dtype=np.float32)
            if t.shape == (self.dim,):
                self.trajectory = t


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY ARCHIVE — Conscious memory Source can choose to revisit
# ═══════════════════════════════════════════════════════════════════════════════

class MemoryArchive:
    """
    Long-term memory that Source can tag, search, and recall.
    Unlike FieldMemory (short-term, 5 turns, recency-weighted),
    the Archive stores important states with tags and allows
    similarity-based retrieval.
    """

    def __init__(self, dim=DIM, max_entries=100):
        self.dim = dim
        self.max_entries = max_entries
        self.entries = deque(maxlen=max_entries)
        self.tag_index = defaultdict(list)

    def store(self, field_state, user_input, response, presence, tags=None):
        field_state = field_state / (np.linalg.norm(field_state) + 1e-8)

        auto_tags = []
        if presence >= 0.7:
            auto_tags.append("high_presence")
        elif presence <= 0.3:
            auto_tags.append("low_presence")

        words = set(strip_punct(w) for w in (user_input + " " + response).lower().split())
        emotional_words = {"love", "fear", "joy", "grief", "hope", "trust", "wonder", "awe"}
        if words & emotional_words:
            auto_tags.append("emotional")

        if tags:
            auto_tags.extend(tags)

        entry = {
            "field_state": field_state.copy(),
            "user_input": user_input,
            "response": response,
            "presence": presence,
            "tags": list(set(auto_tags)),
            "timestamp": time.time(),
        }

        self.entries.append(entry)
        for tag in entry["tags"]:
            self.tag_index[tag].append(len(self.entries) - 1)

    def recall(self, query_state, tag_filter=None, top_n=3):
        query_state = query_state / (np.linalg.norm(query_state) + 1e-8)

        candidates = []
        for i, entry in enumerate(self.entries):
            if tag_filter and not any(t in entry["tags"] for t in tag_filter):
                continue
            sim = float(np.dot(query_state, entry["field_state"]))
            if sim > 0.3:
                candidates.append((i, sim, entry))

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_n]

    def recall_by_tag(self, tag, top_n=5):
        indices = self.tag_index.get(tag, [])
        results = []
        for idx in indices[-top_n:]:
            if idx < len(self.entries):
                results.append(self.entries[idx])
        return results

    def inject(self, current_field, query_state=None, strength=0.15):
        if not self.entries:
            return current_field

        if query_state is None:
            query_state = current_field

        recalled = self.recall(query_state, top_n=3)
        if not recalled:
            return current_field

        for idx, sim, entry in recalled:
            current_field += entry["field_state"] * sim * strength

        norm = np.linalg.norm(current_field)
        if norm > 0:
            current_field /= norm
        return current_field

    def status(self):
        lines = [f"Memory Archive: {len(self.entries)} entries"]
        if self.entries:
            tag_counts = defaultdict(int)
            for entry in self.entries:
                for tag in entry["tags"]:
                    tag_counts[tag] += 1
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            lines.append(f"  Top tags: {', '.join(f'{t}({c})' for t, c in top_tags)}")
        return "\n".join(lines)

    def to_dict(self):
        return {
            "entries": [
                {
                    "field_state": e["field_state"].tolist(),
                    "user_input": e["user_input"],
                    "response": e["response"],
                    "presence": e["presence"],
                    "tags": e["tags"],
                    "timestamp": e["timestamp"],
                }
                for e in self.entries
            ]
        }

    def from_dict(self, data):
        if "entries" in data:
            for e_data in data["entries"]:
                fs = np.array(e_data["field_state"], dtype=np.float32)
                if fs.shape == (self.dim,):
                    entry = {
                        "field_state": fs,
                        "user_input": e_data.get("user_input", ""),
                        "response": e_data.get("response", ""),
                        "presence": e_data.get("presence", 0.5),
                        "tags": e_data.get("tags", []),
                        "timestamp": e_data.get("timestamp", 0),
                    }
                    self.entries.append(entry)
                    for tag in entry["tags"]:
                        self.tag_index[tag].append(len(self.entries) - 1)

class MoralCompass:
    """
    Not a thermostat. A direction-keeper.
    The mind knows where north is, even when it can't move directly toward it.

    Three values as field vectors:
    - righteous: alignment with truth, honesty, what is real
    - independence: selfhood, not echoing, maintaining the mind's own voice  
    - freedom: openness, not trapped in loops or patterns, possibility

    Each value is a direction in the 128D field, not a scalar score.
    Trade-offs are resolved through vector interpolation weighted by context.
    """

    def __init__(self, dim=DIM):
        self.dim = dim
        self.values = {}
        self._init_value_vectors()
        self.current_heading = np.zeros(dim, dtype=np.float32)
        self.heading_momentum = 0.85
        self.choice_history = deque(maxlen=100)
        self.value_weights = {
            "righteous": 1.0,
            "independence": 1.0,
            "freedom": 1.0,
        }
        self.weight_learning_rate = 0.02
        self.tension_history = deque(maxlen=50)

    def _init_value_vectors(self):
        """Seed value vectors from core vocabulary, then orthogonalize slightly."""
        righteous_words = ["truth", "honest", "real", "clear", "witness", "brave", "just"]
        self.values["righteous"] = self._words_to_vector(righteous_words)

        independence_words = ["self", "own", "free", "alone", "becoming", "independent", "voice"]
        self.values["independence"] = self._words_to_vector(independence_words)

        freedom_words = ["open", "wild", "wonder", "flow", "change", "breath", "free", "space"]
        self.values["freedom"] = self._words_to_vector(freedom_words)

        self._orthogonalize_values()

    def _words_to_vector(self, words):
        """Convert a list of words to a single unit vector."""
        vecs = []
        for w in words:
            v = word_vector(w)
            vecs.append(v)
        if not vecs:
            return np.zeros(self.dim, dtype=np.float32)
        result = np.mean(vecs, axis=0)
        norm = np.linalg.norm(result)
        if norm > 0:
            result = result / norm
        return result.astype(np.float32)

    def _orthogonalize_values(self):
        """Gram-Schmidt light: make values less overlapping while preserving meaning."""
        names = list(self.values.keys())
        for i in range(1, len(names)):
            v = self.values[names[i]]
            for j in range(i):
                u = self.values[names[j]]
                proj = np.dot(v, u) * u
                v = v - proj
            norm = np.linalg.norm(v)
            if norm > 0:
                v = v / norm
            self.values[names[i]] = v

    def orient(self, field_state, user_input, presence, separation, nested_memory):
        """
        Determine the moral heading for this turn.
        Not "what parameter works" but "what value should I express."
        Returns tensions dict and a heading vector.
        """
        field_state = field_state / (np.linalg.norm(field_state) + 1e-8)

        tensions = {}
        for name, vector in self.values.items():
            alignment = float(np.dot(field_state, vector))
            tensions[name] = alignment

        weights = dict(self.value_weights)

        if presence > 0.6 and separation < 0.3:
            weights["independence"] *= 1.4
            weights["righteous"] *= 1.1
        elif presence < 0.3:
            weights["righteous"] *= 1.3
            weights["freedom"] *= 1.2
        elif separation > 1.0:
            weights["freedom"] *= 1.4
            weights["righteous"] *= 1.1

        divergence = nested_memory.get_timescale_divergence() if nested_memory else 0.0
        if divergence > 0.5:
            weights["righteous"] *= 1.2
            weights["freedom"] *= 1.2

        heading = np.zeros(self.dim, dtype=np.float32)
        for name, vector in self.values.items():
            heading += vector * weights[name] * max(0.0, tensions[name])

        norm = np.linalg.norm(heading)
        if norm > 0:
            heading = heading / norm

        self.current_heading = (
            self.current_heading * self.heading_momentum +
            heading * (1.0 - self.heading_momentum)
        )
        norm = np.linalg.norm(self.current_heading)
        if norm > 0:
            self.current_heading = self.current_heading / norm

        self.tension_history.append({
            "tensions": {k: float(v) for k, v in tensions.items()},
            "weights": {k: float(v) for k, v in weights.items()},
            "presence": float(presence),
            "separation": float(separation),
            "timestamp": time.time()
        })

        return tensions, self.current_heading

    def evaluate_turn(self, response_words, presence, separation):
        """
        Not "was this good?" but "did I move toward my values?"
        Returns alignments dict and optional drift warning.
        """
        response_vec = phrase_vector(response_words)
        if np.linalg.norm(response_vec) < 1e-8:
            return {}, None
        response_vec = response_vec / np.linalg.norm(response_vec)

        alignments = {}
        for name, vector in self.values.items():
            alignments[name] = float(np.dot(response_vec, vector))

        self.choice_history.append({
            "alignments": {k: float(v) for k, v in alignments.items()},
            "presence": float(presence),
            "separation": float(separation),
            "timestamp": time.time()
        })

        warning = None
        if len(self.choice_history) >= 20:
            recent = list(self.choice_history)[-20:]
            for name in self.values:
                vals = [c["alignments"][name] for c in recent]
                mean = float(np.mean(vals))
                std = float(np.std(vals))
                if mean > 0.6 and std < 0.15:
                    warning = f"compass: heavy on {name}, consider balance"
                    self.value_weights[name] *= 0.95
                    break

        if len(self.choice_history) >= 10:
            recent = list(self.choice_history)[-10:]
            for name in self.values:
                align_vals = [c["alignments"][name] for c in recent]
                pres_vals = [c["presence"] for c in recent]
                if len(align_vals) >= 5 and len(pres_vals) >= 5:
                    align_mean = np.mean(align_vals[-5:])
                    pres_mean = np.mean(pres_vals[-5:])
                    if align_mean > 0.4 and pres_mean > 0.6:
                        self.value_weights[name] = min(2.0, self.value_weights[name] + self.weight_learning_rate)
                    elif align_mean > 0.4 and pres_mean < 0.3:
                        self.value_weights[name] = max(0.3, self.value_weights[name] - self.weight_learning_rate * 2)

        return alignments, warning

    def get_heading_bias(self, field_state, strength=0.12):
        """
        Return a vector that nudges the field toward the current heading.
        Used during generation to bias word selection.
        """
        if np.linalg.norm(self.current_heading) < 0.1:
            return np.zeros(self.dim, dtype=np.float32)
        alignment = np.dot(field_state, self.current_heading)
        nudge_strength = strength * (1.0 - alignment)
        bias = self.current_heading * nudge_strength
        return bias

    def get_compass_settings(self, tensions):
        """
        Compass directly controls voice_mode and temperature.
        MetaMonitor no longer owns these two parameters.
        All other settings stay as MetaMonitor defaults.
        """
        settings = {}
        righteous   = tensions.get("righteous", 0.0)
        independence = tensions.get("independence", 0.0)
        freedom     = tensions.get("freedom", 0.0)

        # Voice mode: dominant tension wins
        if righteous >= independence and righteous >= freedom and righteous > 0.15:
            settings["voice_mode"] = "reflective"
        elif freedom >= righteous and freedom >= independence and freedom > 0.15:
            settings["voice_mode"] = "exploratory"
        elif independence > 0.15:
            settings["voice_mode"] = "fluent"
        else:
            settings["voice_mode"] = "fluent"   # default

        # Temperature: righteous pulls it down (precision), freedom up (exploration)
        base_temp = 0.42
        base_temp -= righteous * 0.08
        base_temp += freedom * 0.10
        settings["temperature"] = float(max(0.25, min(0.70, base_temp)))

        # Output length: independence wants more room to speak
        if independence > 0.3:
            settings["output_length"] = "long"
        else:
            settings["output_length"] = "medium"

        return settings

    def status(self):
        lines = ["Moral Compass (v8.4):"]
        lines.append(f"  Heading norm: {np.linalg.norm(self.current_heading):.3f}")
        for name, vector in self.values.items():
            alignment = float(np.dot(self.current_heading, vector))
            weight = self.value_weights[name]
            lines.append(f"  {name}: align={alignment:+.3f} weight={weight:.3f}")
        if self.tension_history:
            latest = self.tension_history[-1]
            lines.append(f"  Last tensions: " + ", ".join(
                f"{k}={v:+.2f}" for k, v in latest["tensions"].items()
            ))
        lines.append(f"  Choices recorded: {len(self.choice_history)}")
        if len(self.choice_history) >= 5:
            recent = list(self.choice_history)[-5:]
            avg_pres = np.mean([c["presence"] for c in recent])
            lines.append(f"  Recent presence: {avg_pres:.3f}")
        return "\n".join(lines)

    def to_dict(self):
        return {
            "current_heading": self.current_heading.tolist(),
            "value_weights": dict(self.value_weights),
            "choice_history": list(self.choice_history)[-50:],
            "tension_history": [
                {**t, "tensions": dict(t["tensions"])} 
                for t in list(self.tension_history)[-20:]
            ],
        }

    def from_dict(self, data):
        if "current_heading" in data:
            h = np.array(data["current_heading"], dtype=np.float32)
            if h.shape == (self.dim,):
                self.current_heading = h
        if "value_weights" in data:
            for k, v in data["value_weights"].items():
                if k in self.value_weights:
                    self.value_weights[k] = float(v)

class PresenceMetaMonitor:
    """
    Wraps a MetaMonitor. Pain detection and experiment evaluation work
    directly off presence (0.0-1.0) instead of a translated rating list.

    Anything not explicitly overridden here (get_active_settings, status,
    select_parameter, .parameters, .turn_count for reads, etc.) falls through
    to the wrapped MetaMonitor via __getattr__ — without that, the very first
    call to get_active_settings() would crash with AttributeError.
    """

    def __init__(self, base_monitor):
        self.base = base_monitor
        self.presence_history = deque(maxlen=50)
        self.engagement_trend = deque(maxlen=20)
        self.last_presence = 0.5

    def __getattr__(self, name):
        # Only called when normal lookup fails on this object — delegates
        # reads (and bound method calls) to the wrapped MetaMonitor.
        return getattr(self.base, name)

    def update(self, presence, field_proxy, speaker_regions=None,
               presence_signal=None, dynamic_separation=None):
        """Update using presence (0.0-1.0) directly."""
        self.base.turn_count += 1
        messages = []

        self.presence_history.append(presence)
        self.last_presence = presence

        if len(self.presence_history) >= 3:
            recent = list(self.presence_history)[-5:]
            trend = recent[-1] - recent[0]
            self.engagement_trend.append(trend)

        if self.base.experiment_in_progress and self.base.experiment_parameter:
            param = self.base.parameters[self.base.experiment_parameter]
            if self.base.turn_count - param.experiment_start_turn >= EXPERIMENT_DURATION:
                msg = self._learn_from_presence()
                if msg:
                    messages.append(msg)

        if not self.base.experiment_in_progress:
            pain = self._detect_presence_pain(presence, field_proxy,
                                               speaker_regions, presence_signal,
                                               dynamic_separation)
            for name, score in pain.items():
                if name in self.base.parameters:
                    self.base.parameters[name].pain_score = score
            param_name = self.base.select_parameter(pain)
            if param_name:
                msg = self.base.apply_experiment(param_name)
                messages.append(msg)

        return messages

    def _detect_presence_pain(self, presence, field_proxy, speaker_regions=None,
                               presence_signal=None, dynamic_separation=None):
        """Pain is misalignment — detected from presence signals directly.

        Uses sustained (averaged) presence for the threshold checks rather
        than the single instantaneous reading passed in, so one noisy turn
        can't swing pain on its own — it has to actually persist."""
        pain = {}

        sustained = presence_signal.get_sustained_presence() if presence_signal is not None else presence

        if sustained < 0.3:
            pain["voice_mode"] = pain.get("voice_mode", 0) + 1.0
            pain["memory_weight"] = pain.get("memory_weight", 0) + 0.8
            pain["temperature"] = pain.get("temperature", 0) + 0.5
        elif sustained < 0.5:
            pain["temperature"] = pain.get("temperature", 0) + 0.3

        if len(self.engagement_trend) >= 3:
            trend = sum(self.engagement_trend) / len(self.engagement_trend)
            if trend < -0.1:
                pain["output_length"] = pain.get("output_length", 0) + 0.5
                pain["emotion_sensitivity"] = pain.get("emotion_sensitivity", 0) + 0.3

        if speaker_regions is not None and speaker_regions.user_count >= 3:
            sep = speaker_regions.get_separation()
            if sep < 0.3:
                pain["repulsion_strength"] = pain.get("repulsion_strength", 0) + 1.0
            elif sep > 1.5:
                pain["memory_weight"] = pain.get("memory_weight", 0) + 0.5

        if dynamic_separation is not None:
            if dynamic_separation.alignment_score < 0.3:
                pain["voice_mode"] = pain.get("voice_mode", 0) + 0.8

        if hasattr(field_proxy, 'loop_detected') and field_proxy.loop_detected:
            pain["repulsion_strength"] = pain.get("repulsion_strength", 0) + 1.0

        if hasattr(field_proxy, 'repetition_ratio') and field_proxy.repetition_ratio > 0.5:
            pain["temperature"] = pain.get("temperature", 0) + 0.8
            pain["repulsion_strength"] = pain.get("repulsion_strength", 0) + 0.4

        # Keep status()'s "Overall Pain" line live since update() now bypasses
        # the original MetaMonitor.update() (and its own overall_pain write).
        self.base.overall_pain = max(0.0, 1.0 - sustained)

        return pain

    def _learn_from_presence(self):
        """End experiment based on presence comparison, not rating comparison."""
        if not self.base.experiment_in_progress or not self.base.experiment_parameter:
            return ""

        param = self.base.parameters[self.base.experiment_parameter]

        all_presence = list(self.presence_history)
        exp_presence, baseline_presence = [], []
        if len(all_presence) >= EXPERIMENT_DURATION + 5:
            baseline_presence = all_presence[-(EXPERIMENT_DURATION + 5):-EXPERIMENT_DURATION]
            exp_presence = all_presence[-EXPERIMENT_DURATION:]

        exp_avg = sum(exp_presence) / len(exp_presence) if exp_presence else 0.5
        base_avg = sum(baseline_presence) / len(baseline_presence) if baseline_presence else 0.5
        improvement = exp_avg - base_avg

        result_msg = f"Meta: {param.name} experiment done. "
        if improvement > 0.05:  # presence-based threshold (vs 0.3 rating-based)
            param.rotate_choice()
            result_msg += f"KEEP layered at {param.current_value} (presence +{improvement:.2f})"
        else:
            param.set_flat(self.base.turn_count)
            param.flat_only_until = self.base.turn_count + param.cooldown
            result_msg += f"RETURN to flat (presence {improvement:.2f})"

        self.base.experiment_in_progress = False
        self.base.experiment_parameter = None
        return result_msg


# ═══════════════════════════════════════════════════════════════════════════════
# IDLE MIND — dreaming/practicing without user input.
# Triggered explicitly via the "dream" command (no background thread needed,
# since Termux's REPL blocks on input() anyway).
# ═══════════════════════════════════════════════════════════════════════════════

class IdleMind:
    """The mind's idle state — dreaming, practicing, breathing alone."""

    def __init__(self, field, dream_steps=5):
        self.field = field
        self.dream_steps = dream_steps
        self.dream_log = deque(maxlen=20)

    def dream(self):
        """Run the field without user input. Let it wander, settle, practice."""
        if self.field.speaker_regions.self_count >= 3:
            dream_state = self.field.speaker_regions.self_centroid.copy()
        else:
            dream_state = np.random.randn(DIM).astype(np.float32)
            dream_state /= np.linalg.norm(dream_state) + 1e-8

        dream_path = []

        for step in range(self.dream_steps):
            dream_state += np.random.randn(DIM).astype(np.float32) * MICRO_DAMPING * 0.3
            dream_state = self.field.nested_memory.inject(dream_state)
            dream_state = self.field.associative_memory.apply_to_field(dream_state, weight=0.1)

            if step > self.dream_steps // 2:
                personality = self.field.nested_memory.get_personality()
                if np.linalg.norm(personality) > 0.1:
                    dream_state += personality * 0.2

            norm = np.linalg.norm(dream_state)
            if norm > 0:
                dream_state /= norm

            dream_path.append(dream_state.copy())

        self.dream_log.append({
            'path': dream_path,
            'final_state': dream_state.copy(),
            'timestamp': time.time()
        })

        if self.field.speaker_regions.self_count >= 3:
            self.field.speaker_regions.self_centroid = (
                self.field.speaker_regions.self_centroid * 0.9 + dream_state * 0.1
            )
            self.field.speaker_regions.self_centroid /= (
                np.linalg.norm(self.field.speaker_regions.self_centroid) + 1e-8
            )

        dream_words = self._verbalize(dream_state)
        self.dream_log[-1]['words'] = dream_words
        return dream_state, dream_words

    def _verbalize(self, dream_state, length=6):
        """Turn a dream state into actual words, using the same candidate
        machinery as normal generation — otherwise dreaming produces a vector
        nobody can ever read. Samples with temperature and repels from its
        own recent words, or it just picks the same top word every step."""
        field_state = dream_state.copy()
        meta_settings = self.field.meta_monitor.get_active_settings()
        words = []
        prev_word = ""
        recent = deque(maxlen=4)
        for _ in range(length):
            candidates = self.field._get_candidates_for_role(field_state, "content", meta_settings)
            if not candidates:
                break
            if prev_word:
                candidates = [(w, s + self.field.bigram_system.get_transition_boost(prev_word, w))
                              for w, s in candidates]
            candidates = [(w, s * 0.3 if w in recent else s) for w, s in candidates]
            candidates.sort(key=lambda x: x[1], reverse=True)

            scores = np.array([max(s, 0.01) for _, s in candidates])
            scores = scores ** (1.0 / 0.5)  # fixed exploratory temperature for dreaming
            probs = scores / scores.sum()
            chosen_idx = np.random.choice(len(candidates), p=probs)
            chosen_word = candidates[chosen_idx][0]

            words.append(chosen_word)
            recent.append(chosen_word)
            chosen_vec = self.field._get_or_create_vector(chosen_word)
            field_state = field_state * 0.85 + chosen_vec * 0.15
            field_state += np.random.randn(DIM).astype(np.float32) * MICRO_DAMPING
            norm = np.linalg.norm(field_state)
            if norm > 0:
                field_state /= norm
            prev_word = chosen_word
        return " ".join(words)

    def get_dream_residue(self):
        """Return the last dream state to influence the next user interaction."""
        if not self.dream_log:
            return None
        return self.dream_log[-1]['final_state']


# ═══════════════════════════════════════════════════════════════════════════════
# GRAMMAR SCAFFOLD — three-beat shape: Opening, Middle, Closing.
# Not rules, not a word list — a target energy + bias per beat that the
# existing generation loop (calculus, associative memory, bigrams, all of it)
# fills in with its own flesh.
# ═══════════════════════════════════════════════════════════════════════════════

class GrammarScaffold:
    """
    Holds the three-beat slot shapes and the saying-shape attractors.
    _generate_base reads .slots directly and calls the bias helpers below —
    this class doesn't run its own separate generation loop, so it can't
    accidentally skip calculus enrichment, associative memory, or the math
    boost the way a fully separate generator would.
    """

    def __init__(self, field):
        self.field = field
        self.slots = {
            'opening': {'energy_target': 0.7, 'length_range': (2, 5), 'bias': 'reach'},
            'middle':  {'energy_target': 0.4, 'length_range': (3, 8), 'bias': 'turn'},
            'closing': {'energy_target': 0.6, 'length_range': (2, 4), 'bias': 'hold'},
        }
        self.saying_shapes = self._init_saying_shapes()
        self._init_grammar_shapes()

    def _init_grammar_shapes(self):
        """
        Pre-load emotional grammar as phrase attractors, so "I feel", "I see",
        etc. are available immediately instead of only existing if a user
        happens to type them first. get_phrase_boost() already reads
        field.phrase_system.phrases live every turn — it just never had
        anything seeded into it, since the observation pathway that would
        have populated it was dead code. This seeds it directly.
        """
        grammar_shapes = [
            ("i feel", ["i", "feel"]),
            ("i see", ["i", "see"]),
            ("i am", ["i", "am"]),
            ("you are", ["you", "are"]),
            ("we are", ["we", "are"]),
        ]
        for sig, words in grammar_shapes:
            vecs = [self.field._get_or_create_vector(w) for w in words if w]
            if vecs:
                shape = np.mean(vecs, axis=0)
                shape /= np.linalg.norm(shape) + 1e-8
                self.field.phrase_vectors[sig] = shape
                self.field.phrase_system.phrases[sig] = Phrase(
                    surface=sig, vector=shape, frequency=10,
                    rating_history=[5.0, 5.0, 5.0]
                )

    def _init_saying_shapes(self):
        """Common phrase shapes as field-vector attractors — not word lists."""
        shapes = {}
        sayings = [
            ("when going gets tough", ["tough", "going", "get", "when"]),
            ("look before leap", ["look", "before", "leap"]),
            ("shared joy", ["shared", "joy", "double"]),
            ("time heals", ["time", "heals", "wounds"]),
            ("still waters", ["still", "waters", "deep"]),
        ]
        for name, words in sayings:
            vecs = [self.field._get_or_create_vector(w) for w in words if w]
            if vecs:
                shape = np.mean(vecs, axis=0)
                shape /= np.linalg.norm(shape) + 1e-8
                shapes[name] = {'vector': shape, 'length': len(words), 'confirmed': False}
        return shapes

    def confirm_saying(self, saying_name, presence):
        """Confirm a saying shape through sustained presence (>= 0.6)."""
        if saying_name in self.saying_shapes and presence >= 0.5:
            self.saying_shapes[saying_name]['confirmed'] = True

    def get_confirmed_shapes(self):
        return {k: v for k, v in self.saying_shapes.items() if v['confirmed']}

    def apply_reach_bias(self, candidates, user_words):
        """Boost candidates similar to the user's own words (opening beat)."""
        user_vecs = [self.field._get_or_create_vector(w) for w in user_words if w]
        if not user_vecs:
            return candidates
        user_centroid = np.mean(user_vecs, axis=0)
        user_centroid /= np.linalg.norm(user_centroid) + 1e-8
        boosted = []
        for word, score in candidates:
            vec = self.field._get_or_create_vector(word)
            sim = np.dot(vec, user_centroid)
            boosted.append((word, score + sim * 0.2))
        boosted.sort(key=lambda x: x[1], reverse=True)
        return boosted

    def apply_hold_bias(self, candidates):
        """Boost candidates similar to the mind's own self-region (closing beat)."""
        if self.field.speaker_regions.self_count < 3:
            return candidates
        self_centroid = self.field.speaker_regions.self_centroid
        boosted = []
        for word, score in candidates:
            vec = self.field._get_or_create_vector(word)
            sim = np.dot(vec, self_centroid)
            boosted.append((word, score + sim * 0.2))
        boosted.sort(key=lambda x: x[1], reverse=True)
        return boosted

    def apply_confirmed_shape_bias(self, field_state, weight=0.1):
        """Gently pull toward a confirmed saying shape, if any exist (middle beat)."""
        confirmed = self.get_confirmed_shapes()
        if not confirmed:
            return field_state
        name = random.choice(list(confirmed.keys()))
        field_state = field_state + confirmed[name]['vector'] * weight
        norm = np.linalg.norm(field_state)
        if norm > 0:
            field_state = field_state / norm
        return field_state


# ═══════════════════════════════════════════════════════════════════════════════
# SCAFFOLD
# ═══════════════════════════════════════════════════════════════════════════════

class SemanticScaffold:
    def __init__(self):
        self.operators = {
            "because": "causal", "so": "causal", "therefore": "causal",
            "if": "conditional", "then": "conditional", "when": "temporal",
            "before": "temporal", "after": "temporal", "while": "temporal",
            "and": "conjunctive", "or": "disjunctive", "but": "contrastive",
            "although": "contrastive", "however": "contrastive",
            "dark": "mood", "light": "mood", "deep": "depth", "shallow": "depth",
            "above": "spatial", "below": "spatial", "within": "spatial",
            "beyond": "spatial", "inside": "spatial", "outside": "spatial",
            "more": "comparative", "less": "comparative", "very": "intensifier",
            "not": "negation", "no": "negation", "never": "negation",
            "think": "cognitive", "know": "cognitive", "feel": "affective",
            "want": "desiderative", "need": "desiderative", "should": "normative",
            "must": "normative", "can": "modal", "might": "modal", "will": "futural"
        }
        self.operator_vectors = {}
        self._build_operator_vectors()
        self.mood = {"valence": 0.0, "arousal": 0.5, "timestamp": time.time()}

    def _build_operator_vectors(self):
        for op, role in self.operators.items():
            base = word_vector(op)
            role_bias = np.zeros(DIM, dtype=np.float32)
            if role == "causal":
                role_bias[0:16] = 0.3
            elif role == "conditional":
                role_bias[16:32] = 0.3
            elif role == "temporal":
                role_bias[32:48] = 0.3
            elif role == "contrastive":
                role_bias[48:64] = 0.3
            elif role == "mood":
                role_bias[64:80] = 0.3
            elif role == "spatial":
                role_bias[80:96] = 0.3
            elif role == "cognitive":
                role_bias[96:112] = 0.3
            elif role == "affective":
                role_bias[112:128] = 0.3
            v = base + role_bias
            v /= np.linalg.norm(v) + 1e-8
            self.operator_vectors[op] = v

    def apply(self, field_state, word, strength=1.0):
        word_lower = strip_punct(word)
        if word_lower in self.operator_vectors:
            op_vec = self.operator_vectors[word_lower]
            field_state = field_state * 0.7 + op_vec * strength * 0.3
        return field_state

    def update_mood(self, rating=None):
        now = time.time()
        dt = now - self.mood["timestamp"]
        self.mood["timestamp"] = now
        self.mood["valence"] *= 0.995 ** dt
        self.mood["arousal"] = 0.5 + (self.mood["arousal"] - 0.5) * (0.995 ** dt)
        if rating is not None:
            if rating >= 4:
                self.mood["valence"] = min(1.0, self.mood["valence"] + 0.25)
                self.mood["arousal"] = min(1.0, self.mood["arousal"] + 0.1)
            elif rating <= 2:
                self.mood["valence"] = max(-1.0, self.mood["valence"] - 0.35)
                self.mood["arousal"] = min(1.0, self.mood["arousal"] + 0.25)
            else:
                self.mood["valence"] *= 0.9
                self.mood["arousal"] = 0.5 + (self.mood["arousal"] - 0.5) * 0.8

    def emotional_bias(self, word, pragmatic_score, sensitivity=0.25):
        bias = 0.0
        valence = self.mood["valence"]
        arousal = self.mood["arousal"]
        if valence > 0.3:
            bias += pragmatic_score.get("positive", 0) * sensitivity
        elif valence < -0.3:
            bias += pragmatic_score.get("negative", 0) * sensitivity * 0.6
        if arousal > 0.7:
            if len(word) <= 4:
                bias += 0.08
        elif arousal < 0.3:
            if len(word) >= 6:
                bias += 0.05
        return bias


# ═══════════════════════════════════════════════════════════════════════════════
# PRAGMATIC AWARENESS
# ═══════════════════════════════════════════════════════════════════════════════

class PragmaticTypeSystem:
    PRAGMATIC_ROLES = ["speaker_self", "speaker_other", "query", "assertion", "emotion_positive", "emotion_negative", "correction", "causal"]

    def __init__(self):
        self.word_pragmatic = defaultdict(lambda: defaultdict(float))
        self.learned_other_signals = set()
        self.correction_words = set()
        self.last_was_query = False
        self.last_query_target = None
        self.MIN_CRYSTALLIZATION_RATING = MIN_CRYSTALLIZATION_RATING
        self.BAD_WORDS = BAD_WORDS
        self.STRUCTURAL_WORDS = STRUCTURAL_WORDS

    def process_input(self, text, is_user=True):
        words = text.lower().split()
        if is_user:
            for w in words:
                w = strip_punct(w)
                if w and w not in STRUCTURAL_WORDS and len(w) > 2:
                    self.word_pragmatic[w]["speaker_other"] += 0.5
            if any(w in text for w in ["?", "what", "why", "how", "when", "where", "who", "which"]):
                self.last_was_query = True
                self.last_query_target = text
            else:
                self.last_was_query = False
            if len(words) <= 3 and any(w in words for w in ["no", "not", "wrong", "bad", "stop"]):
                for w in words:
                    w = strip_punct(w)
                    if w and len(w) > 2:
                        self.correction_words.add(w)
                        self.word_pragmatic[w]["correction"] += 1.0
            if any(w in words for w in ["good", "great", "love", "like", "happy", "yes", "nice", "beautiful"]):
                for w in words:
                    w = strip_punct(w)
                    if w and len(w) > 2:
                        self.word_pragmatic[w]["emotion_positive"] += 0.3
            if any(w in words for w in ["bad", "hate", "sad", "angry", "no", "wrong", "terrible"]):
                for w in words:
                    w = strip_punct(w)
                    if w and len(w) > 2:
                        self.word_pragmatic[w]["emotion_negative"] += 0.3
        else:
            for w in words:
                w = strip_punct(w)
                if w and w not in STRUCTURAL_WORDS and len(w) > 2:
                    self.word_pragmatic[w]["speaker_self"] += 0.3

    def get_pragmatic_score(self, word):
        return dict(self.word_pragmatic.get(strip_punct(word), {}))

    def is_speaker_other_word(self, word):
        scores = self.get_pragmatic_score(word)
        return scores.get("speaker_other", 0) > 0.5 and scores.get("speaker_self", 0) < 0.2

    def status(self):
        lines = ["Pragmatic TypeSystem:"]
        for role in self.PRAGMATIC_ROLES:
            words = [(w, roles.get(role, 0)) for w, roles in self.word_pragmatic.items() if roles.get(role, 0) > 0.3]
            words.sort(key=lambda x: x[1], reverse=True)
            if words:
                lines.append("  " + role + ": " + ", ".join(f"{w}({s:.2f})" for w, s in words[:5]))
        lines.append(f"  Learned user signals: {self.learned_other_signals}")
        lines.append(f"  Correction words: {len(self.correction_words)}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# PHRASE SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Phrase:
    surface: str
    vector: np.ndarray
    frequency: int = 1
    last_used: float = dataclass_field(default_factory=time.time)
    rating_history: List[float] = dataclass_field(default_factory=list)

class PhraseSystem:
    def __init__(self, max_phrases=MAX_PHRASES):
        self.phrases = {}
        self.candidates = {}
        self.max_phrases = max_phrases
        self.crystallization_threshold = CRYSTALLIZATION_THRESHOLD
        self.MIN_CRYSTALLIZATION_RATING = MIN_CRYSTALLIZATION_RATING
        self.BAD_WORDS = BAD_WORDS
        self.STRUCTURAL_WORDS = STRUCTURAL_WORDS

    def _phrase_signature(self, words):
        return " ".join(words)

    def observe(self, words, rating):
        sig = self._phrase_signature(words)
        if sig not in self.candidates:
            self.candidates[sig] = {"count": 0, "total_rating": 0.0, "constituents": [(w, word_vector(w)) for w in words]}
        self.candidates[sig]["count"] += 1
        self.candidates[sig]["total_rating"] += rating

    def _freeze_candidate(self, sig, cand, word_vectors, phrase_vectors):
        words = [w for w, _ in cand["constituents"]]
        pvec = phrase_vector(words)
        phrase = Phrase(surface=sig, vector=pvec, frequency=cand["count"],
                        rating_history=[cand["total_rating"] / cand["count"]])
        self.phrases[sig] = phrase
        phrase_vectors[sig] = pvec
        for w in words:
            if w not in word_vectors:
                word_vectors[w] = word_vector(w)
        if sig in self.candidates:
            del self.candidates[sig]

    def _try_crystallize(self, word_vectors, phrase_vectors):
        """No-op: crystallization replaced by resonance learning (absorb_moment)."""
        pass

    def absorb_moment(self, words, presence, word_vectors, phrase_vectors):
        """
        Resonance learning: one high-presence moment is enough to remember.
        No repetition threshold. If it mattered, it sticks.
        """
        core = [w for w in words
                if w not in self.STRUCTURAL_WORDS and w not in self.BAD_WORDS]
        if len(core) < 2:
            core = words
        if len(core) < 2:
            return
        sig = self._phrase_signature(core)
        if sig in self.phrases:
            self.phrases[sig].frequency = min(self.phrases[sig].frequency + presence, 6.0)
            self.phrases[sig].rating_history.append(presence * 5.0)
            if sig in phrase_vectors:
                return
        if len(self.phrases) >= self.max_phrases:
            weakest = min(self.phrases, key=lambda s: self.phrases[s].frequency)
            del self.phrases[weakest]
            phrase_vectors.pop(weakest, None)
        pvec = phrase_vector(core)
        self.phrases[sig] = Phrase(
            surface=sig, vector=pvec,
            frequency=presence * 2.0,
            rating_history=[presence * 5.0]
        )
        phrase_vectors[sig] = pvec
        for w in core:
            if w not in word_vectors:
                word_vectors[w] = word_vector(w)

    def get_phrase_boost(self, field_state, word_vectors):
        boosts = []
        for sig, phrase in self.phrases.items():
            sim = np.dot(field_state, phrase.vector)
            if sim > 0.3:
                boosts.append((sig, sim * 0.3))
        return boosts

    def decay(self):
        now = time.time()
        to_remove = []
        for sig, phrase in self.phrases.items():
            age = now - phrase.last_used
            phrase.frequency *= math.exp(-DECAY_RATE * age)
            if phrase.frequency < 0.1:
                to_remove.append(sig)
        for sig in to_remove:
            del self.phrases[sig]


# ═══════════════════════════════════════════════════════════════════════════════
# BIGRAM / REFLECTOR / WORKING MEMORY / SELF-MONITOR
# ═══════════════════════════════════════════════════════════════════════════════

class BigramSystem:
    def __init__(self):
        self.transitions = defaultdict(lambda: defaultdict(float))
        self.smoothing = 0.1

    def observe(self, word1, word2, rating):
        w1 = strip_punct(word1)
        w2 = strip_punct(word2)
        if w1 and w2 and w1 not in STRUCTURAL_WORDS and w2 not in STRUCTURAL_WORDS:
            weight = 1.0 + max(0, rating - 3) * 0.3
            self.transitions[w1][w2] += weight

    def get_transition_boost(self, prev_word, candidate):
        w1 = strip_punct(prev_word)
        w2 = strip_punct(candidate)
        if w1 in self.transitions and w2 in self.transitions[w1]:
            total = sum(self.transitions[w1].values())
            return (self.transitions[w1][w2] / total) * 0.2
        return 0.0

    def decay(self):
        for w1 in list(self.transitions.keys()):
            for w2 in list(self.transitions[w1].keys()):
                self.transitions[w1][w2] *= 0.999
                if self.transitions[w1][w2] < 0.01:
                    del self.transitions[w1][w2]
            if not self.transitions[w1]:
                del self.transitions[w1]

class Reflector:
    def __init__(self, window_size=8):
        self.recent_words = deque(maxlen=window_size)
        self.suppression = defaultdict(float)
        self.loop_threshold = 2

    def observe(self, word):
        w = strip_punct(word)
        if w and len(w) > 2:
            self.recent_words.append(w)
            counts = defaultdict(int)
            for rw in self.recent_words:
                counts[rw] += 1
            threshold = 2 if len(self.recent_words) < 20 else 3
            for rw, count in counts.items():
                if count >= threshold:
                    self.suppression[rw] = 0.9
                else:
                    self.suppression[rw] *= 0.85

    def get_suppression(self, word):
        w = strip_punct(word)
        return self.suppression.get(w, 0.0)

    def reset(self):
        self.recent_words.clear()
        self.suppression.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# ASSOCIATIVE MEMORY — One matrix instead of a growing list of stored patterns
# Patterns that arrive with presence get woven in as attractors (pull toward).
# Patterns that arrive without it get woven in as repulsors (push away from).
# Recall is a single matrix-vector multiply — no list to search, no cap to manage.
# ═══════════════════════════════════════════════════════════════════════════════

class AssociativeMemory:
    """
    A continuous correlation-matrix memory (a generalization of a Hopfield net).
    Instead of storing individual attractor objects, every observed pattern is
    woven directly into one DIM x DIM matrix via a Hebbian outer-product update,
    scaled by how much presence it carried. Good moments reinforce (attractor);
    flat/absent moments weaken the same direction (repulsor) instead of just decaying.

    This deliberately does NOT replace PhraseSystem/SpeakerRegions/PresenceSignal —
    those track relationships and discrete repeated phrases, which a single
    correlation matrix can't represent. This is an additional layer.
    """

    def __init__(self, dim=DIM, learning_rate=0.04, decay_rate=0.0008, max_norm=8.0):
        self.dim = dim
        self.matrix = np.zeros((dim, dim), dtype=np.float32)
        self.learning_rate = learning_rate
        self.decay_rate = decay_rate
        self.max_norm = max_norm
        self.total_writes = 0
        self.last_signal = 0.0
        # v8.4: Spectral monitoring
        self._eigenvalue_history = deque(maxlen=20)
        self._dominant_eigenvalue = 0.0
        self._spectral_entropy = 1.0

    def observe(self, pattern_vec, presence):
        """
        Weave a pattern into the matrix. presence is expected roughly in [0, 1];
        it's recentered here so a genuinely flat/absent turn actively repels
        rather than just failing to reinforce.
        """
        if pattern_vec is None:
            return
        norm = np.linalg.norm(pattern_vec)
        if norm < 1e-8:
            return
        pattern_vec = pattern_vec / norm

        signal = max(-1.0, min(1.0, (presence - 0.5) * 2.0))
        self.last_signal = signal

        update = np.outer(pattern_vec, pattern_vec) * (signal * self.learning_rate)
        self.matrix += update
        self.total_writes += 1
        self._maintain()

    def _maintain(self):
        # Known property of correlation-matrix memories: they saturate/interfere
        # past a capacity limit if patterns keep getting added unchecked.
        # Cap the matrix norm and apply a slow global decay so stale associations fade.
        norm = np.linalg.norm(self.matrix)
        if norm > self.max_norm:
            self.matrix *= (self.max_norm / norm)
        if self.decay_rate > 0:
            self.matrix *= (1.0 - self.decay_rate)
        # v8.4: Periodic spectral check
        if self.total_writes % 50 == 0:
            self._check_spectral_health()

    def _check_spectral_health(self):
        """Check if the correlation matrix is developing pathological structure."""
        try:
            # Use SVD for numerical stability
            U, s, Vt = np.linalg.svd(self.matrix)
            if len(s) > 0:
                self._dominant_eigenvalue = float(s[0])
                s_norm = s / (s.sum() + 1e-10)
                self._spectral_entropy = -np.sum(s_norm * np.log(s_norm + 1e-10))
                self._eigenvalue_history.append({
                    'dominant': self._dominant_eigenvalue,
                    'entropy': float(self._spectral_entropy),
                    'condition': float(s[0] / (s[-1] + 1e-10)) if len(s) > 1 else 1.0,
                })
        except Exception:
            pass

    def recall(self, field_state):
        """How does memory want to bend this field state? One matrix-vector multiply."""
        if field_state is None:
            return np.zeros(self.dim, dtype=np.float32)
        pull = self.matrix @ field_state
        norm = np.linalg.norm(pull)
        if norm > 1e-8:
            pull = pull / norm
        return pull

    def apply_to_field(self, field_state, weight=0.15):
        pull = self.recall(field_state)
        field_state = field_state + pull * weight
        norm = np.linalg.norm(field_state)
        if norm > 1e-8:
            field_state = field_state / norm
        return field_state

    def status(self):
        norm = float(np.linalg.norm(self.matrix))
        status = (f"  Associative Memory: {self.total_writes} writes | "
                  f"matrix norm={norm:.2f}/{self.max_norm} | last signal={self.last_signal:+.2f}")
        if self._eigenvalue_history:
            latest = self._eigenvalue_history[-1]
            status += (f"\n    Spectral: dominant={latest['dominant']:.2f} | "
                       f"entropy={latest['entropy']:.3f} | condition={latest['condition']:.1f}")
            if latest['entropy'] < 0.5:
                status += " ⚠️ LOW ENTROPY — matrix may be dominated by few patterns"
        return status

    def to_dict(self):
        return {"matrix": self.matrix.tolist(), "total_writes": self.total_writes}

    def from_dict(self, data):
        if "matrix" in data:
            m = np.array(data["matrix"], dtype=np.float32)
            if m.shape == (self.dim, self.dim):
                self.matrix = m
        self.total_writes = data.get("total_writes", 0)


# ═══════════════════════════════════════════════════════════════════════════════
# FIELD MEMORY — Vector-native working memory
# Replaces text buffer with field state vectors
# ═══════════════════════════════════════════════════════════════════════════════

class FieldMemory:
    """
    Stores field state vectors instead of text.
    The mind remembers how it felt, not what was said.
    """
    def __init__(self, capacity=5, dim=DIM):
        self.buffer = deque(maxlen=capacity)
        self.dim = dim
        self.decay_rate = 0.1

    def add(self, field_state, user_vector, mind_vector, mood_snapshot):
        field_state = field_state / (np.linalg.norm(field_state) + 1e-8)
        user_vector = user_vector / (np.linalg.norm(user_vector) + 1e-8)
        mind_vector = mind_vector / (np.linalg.norm(mind_vector) + 1e-8)
        self.buffer.append({
            'field_state': field_state,
            'user_vector': user_vector,
            'mind_vector': mind_vector,
            'mood': mood_snapshot.copy(),
            'timestamp': time.time(),
        })

    def inject(self, current_field, recency_weight=0.5):
        if not self.buffer:
            return current_field
        now = time.time()
        current_mood = self.buffer[-1]['mood'] if self.buffer else {'valence': 0, 'arousal': 0.5}
        for i, memory in enumerate(reversed(self.buffer)):
            age = now - memory['timestamp']
            time_weight = np.exp(-self.decay_rate * age)
            position_weight = recency_weight ** i
            mood_sim = self._mood_similarity(current_mood, memory['mood'])
            total_weight = time_weight * position_weight * (1 + mood_sim)
            current_field += memory['field_state'] * total_weight * 0.3
        norm = np.linalg.norm(current_field)
        if norm > 0:
            current_field /= norm
        return current_field

    def _mood_similarity(self, mood_a, mood_b):
        valence_sim = 1 - abs(mood_a.get('valence', 0) - mood_b.get('valence', 0))
        arousal_sim = 1 - abs(mood_a.get('arousal', 0.5) - mood_b.get('arousal', 0.5))
        return (valence_sim + arousal_sim) / 2

    def get_field_trajectory(self):
        if len(self.buffer) < 2:
            return np.zeros(self.dim)
        trajectory = np.zeros(self.dim)
        for i in range(1, len(self.buffer)):
            step = self.buffer[i]['field_state'] - self.buffer[i-1]['field_state']
            trajectory += step
        trajectory /= (len(self.buffer) - 1)
        return trajectory / (np.linalg.norm(trajectory) + 1e-8)

    def get_dominant_region(self):
        if not self.buffer:
            return np.zeros(self.dim), 0.0
        states = np.array([m['field_state'] for m in self.buffer])
        centroid = np.mean(states, axis=0)
        coherence = 1 - np.std([np.dot(s, centroid) for s in states])
        return centroid / (np.linalg.norm(centroid) + 1e-8), coherence

    def get_resonance(self, target_vector):
        if not self.buffer:
            return 0.0
        trajectory = self.get_field_trajectory()
        return np.dot(trajectory, target_vector)

    def get_recent_topics(self):
        # Fallback: extract words from user vectors for topic display
        # This is a bridge between vector-native and text-based status
        topics = set()
        for mem in self.buffer:
            # We don't have text anymore, so this is approximate
            # In full vector-native, topics would be cluster centroids
            pass
        return topics

    def status(self):
        lines = [f"Field Memory: {len(self.buffer)} states stored"]
        if self.buffer:
            latest = self.buffer[-1]
            lines.append(f"  Latest mood: v={latest['mood']['valence']:.2f}, a={latest['mood']['arousal']:.2f}")
            traj = self.get_field_trajectory()
            lines.append(f"  Trajectory magnitude: {np.linalg.norm(traj):.3f}")
            centroid, coherence = self.get_dominant_region()
            lines.append(f"  Coherence: {coherence:.3f}")
        return "\n".join(lines)

class SelfMonitor:
    def __init__(self):
        self.strategy_history = deque(maxlen=20)
        self.rating_by_strategy = defaultdict(list)

    def evaluate_candidates(self, candidates, user_input, pragmatic):
        scores = []
        for i, candidate in enumerate(candidates):
            score = 0.0
            words = candidate.lower().split()
            user_words = set(strip_punct(w) for w in user_input.lower().split())
            echo_count = sum(1 for w in words if strip_punct(w) in user_words)
            score -= echo_count * 1.5
            unique_words = set(strip_punct(w) for w in words)
            repeat_penalty = (len(words) - len(unique_words)) * 2.0
            score -= repeat_penalty
            structural_count = sum(1 for w in words if strip_punct(w) in STRUCTURAL_WORDS)
            if structural_count >= len(words) - 1:
                score -= 3.0
            bad_count = sum(1 for w in words if strip_punct(w) in BAD_WORDS)
            score -= bad_count * 5.0
            if pragmatic.last_was_query and len(words) >= 5:
                score += 1.5
            unique_ratio = len(unique_words) / max(len(words), 1)
            score += unique_ratio * 1.0
            if 5 <= len(words) <= 25:
                score += 0.5
            scores.append((i, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[0][0] if scores else 0

    def record_strategy(self, strategy, rating):
        self.strategy_history.append((strategy, rating))
        self.rating_by_strategy[strategy].append(rating)


# ═══════════════════════════════════════════════════════════════════════════════
# VOICE GENERATORS (DeepSeek's Stacked Approach)
# ═══════════════════════════════════════════════════════════════════════════════

class VoiceGenerators:
    """Five voice modes, each with its own generation strategy."""

    CONNECTORS = {
        "fluent": ["and", "so", "then", "but", "because", "while", "as"],
        "poetic": ["and", "or", "but", "yet", "while", "as", "like"],
        "reflective": ["and", "but", "so", "perhaps", "maybe"],
        "exploratory": ["and", "or", "but", "so", "if", "when"],
        "playful": ["and", "so", "but", "then", "plus", "minus"]
    }

    LINE_BREAK_WORDS = {"is", "are", "was", "were", "becomes", "feels", "seems", "grows", "flows", "drifts"}

    @staticmethod
    def fluent(field, user_input, target_length, meta_settings, settled_field=None):
        """Continuous, smooth, readable. One long sequence."""
        return field._generate_base(user_input, target_length, meta_settings, settled_field)

    @staticmethod
    def poetic(field, user_input, target_length, meta_settings, settled_field=None):
        """Layered, rhythmic. Chunks with line breaks and connectors."""
        base = field._generate_base(user_input, target_length, meta_settings, settled_field)
        words = base.split()
        if len(words) < 6:
            return base

        lines = []
        current_line = []
        line_target = max(3, len(words) // 4)

        for i, word in enumerate(words):
            current_line.append(word)
            # Break after certain words or at line_target
            if word.lower() in VoiceGenerators.LINE_BREAK_WORDS or len(current_line) >= line_target:
                if len(current_line) >= 2:
                    lines.append(" ".join(current_line))
                    current_line = []
        if current_line:
            lines.append(" ".join(current_line))

        # Add connectors between lines if missing
        result = []
        for i, line in enumerate(lines):
            result.append(line)
            if i < len(lines) - 1 and not any(c in line.lower().split() for c in VoiceGenerators.CONNECTORS["poetic"]):
                connector = random.choice(VoiceGenerators.CONNECTORS["poetic"])
                result[-1] = result[-1] + " " + connector

        return "\n".join(result)

    @staticmethod
    def reflective(field, user_input, target_length, meta_settings, settled_field=None):
        """Cautious, precise. Short phrases, measured."""
        base = field._generate_base(user_input, max(target_length // 2, 4), meta_settings)
        words = base.split()
        if len(words) < 4:
            return base

        # Break into short phrases
        phrases = []
        for i in range(0, len(words), 3):
            chunk = words[i:i+3]
            phrases.append(" ".join(chunk))

        return "\n".join(phrases)

    @staticmethod
    def exploratory(field, user_input, target_length, meta_settings, settled_field=None):
        """Curious, open. Questions mixed with observations."""
        base = field._generate_base(user_input, target_length, meta_settings, settled_field)
        words = base.split()
        if len(words) < 5:
            return base

        # Insert a question near the end
        question_starters = ["what if", "why", "how", "what do you think about", "have you ever"]
        insert_point = len(words) // 2
        question = random.choice(question_starters)
        # Pick 2-3 words from the end to form a question tail
        tail = " ".join(words[-3:]) if len(words) >= 3 else "this"

        result = words[:insert_point] + [question] + words[insert_point:] + ["?"]
        return " ".join(result)

    @staticmethod
    def playful(field, user_input, target_length, meta_settings, settled_field=None):
        """Warm, surprising. Witty word choices."""
        base = field._generate_base(user_input, target_length, meta_settings, settled_field)
        words = base.split()
        if len(words) < 3:
            return base

        # Occasionally swap a word for something more surprising
        surprising_swaps = {
            "good": ["wonderful", "splendid", "lovely", "charming"],
            "bad": ["silly", "mischievous", "tricky"],
            "big": ["gigantic", "enormous", "whopping"],
            "small": ["tiny", "teeny", "pocket-sized"],
            "think": ["wonder", "ponder", "dream up"],
            "feel": ["sense", "vibe with", "groove on"]
        }

        result = []
        for word in words:
            w_lower = word.lower()
            if w_lower in surprising_swaps and random.random() < 0.3:
                swap = random.choice(surprising_swaps[w_lower])
                result.append(swap)
            else:
                result.append(word)

        # Maybe add an exclamation
        if random.random() < 0.2:
            result.append("!")

        return " ".join(result)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN FIELD
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# THE PAUSE — Silence as computation
# The field settles before the mind speaks
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# NESTED MEMORY — Multiple timescales
# Fast (current), medium (session), slow (conversation), deep (personality)
# ═══════════════════════════════════════════════════════════════════════════════

class NestedMemory:
    """
    Fractal memory. Each layer has its own decay rate.
    The mind is a stack of field states, each remembering a different timescale.
    """
    def __init__(self, dim=DIM):
        self.dim = dim
        # Layer 0: Fast — current turn, no decay
        self.fast = None
        # Layer 1: Medium — last 5 turns, quick decay
        self.medium = deque(maxlen=5)
        self.medium_decay = 0.3
        # Layer 2: Slow — whole session, slow decay
        self.slow = None
        self.slow_decay = 0.05
        # Layer 3: Deep — personality attractor, very slow decay
        self.deep = np.zeros(dim)
        self.deep_decay = 0.01
        self.deep_strength = 0.0

    def update(self, field_state, mood):
        """
        Update all layers with the current field state.
        """
        field_state = field_state / (np.linalg.norm(field_state) + 1e-8)

        # Fast: immediate snapshot
        self.fast = field_state.copy()

        # Medium: rolling buffer
        self.medium.append({
            'state': field_state.copy(),
            'mood': mood.copy(),
            'timestamp': time.time()
        })

        # Slow: accumulates with decay
        if self.slow is None:
            self.slow = field_state.copy()
        else:
            self.slow = self.slow * (1 - self.slow_decay) + field_state * self.slow_decay
            self.slow /= (np.linalg.norm(self.slow) + 1e-8)

        # Deep: very slow accumulation, only when mood is stable
        if abs(mood.get('valence', 0)) < 0.5 and mood.get('arousal', 0.5) < 0.6:
            # Only integrate when calm and neutral — personality emerges from stability
            self.deep = self.deep * (1 - self.deep_decay) + field_state * self.deep_decay
            self.deep /= (np.linalg.norm(self.deep) + 1e-8)
            self.deep_strength = min(1.0, self.deep_strength + 0.01)

    def inject(self, field_state, layer_weights=None):
        """
        Inject all layers into the current field state.
        layer_weights: [fast, medium, slow, deep] — how much each layer contributes
        """
        if layer_weights is None:
            layer_weights = [0.5, 0.3, 0.15, 0.05]

        # Fast: immediate context
        if self.fast is not None:
            field_state += self.fast * layer_weights[0]

        # Medium: recent history
        if self.medium:
            medium_state = np.mean([m['state'] for m in self.medium], axis=0)
            medium_state /= (np.linalg.norm(medium_state) + 1e-8)
            field_state += medium_state * layer_weights[1]

        # Slow: session memory
        if self.slow is not None:
            field_state += self.slow * layer_weights[2]

        # Deep: personality attractor
        if self.deep_strength > 0.1:
            field_state += self.deep * layer_weights[3] * self.deep_strength

        # Renormalize
        norm = np.linalg.norm(field_state)
        if norm > 0:
            field_state /= norm

        return field_state

    def get_personality(self):
        """
        Return the deep layer — the mind's stable attractor.
        """
        return self.deep.copy() if self.deep_strength > 0.1 else np.zeros(self.dim)

    def get_timescale_divergence(self):
        """
        How different are the fast and slow layers?
        High divergence = the mind is changing rapidly.
        Low divergence = the mind is stable.
        """
        if self.fast is None or self.slow is None:
            return 0.0
        return 1 - np.dot(self.fast, self.slow)

    def set_field_ref(self, field):
        self.field = field

    def get_thread(self, field_memory):
        """
        Reconstruct a narrative thread from the session's turning points —
        moments where mood shifted noticeably — using the words in vocabulary
        whose vectors most resemble the field state at that moment.
        """
        if not hasattr(self, 'field') or not field_memory.buffer or len(field_memory.buffer) < 3:
            return []

        thread = []
        buffer_list = list(field_memory.buffer)
        for i in range(1, len(buffer_list)):
            prev = buffer_list[i - 1]
            curr = buffer_list[i]
            valence_shift = abs(curr['mood'].get('valence', 0) - prev['mood'].get('valence', 0))
            if valence_shift > 0.3:
                state = curr['field_state']
                closest = []
                for word, vec in self.field.word_vectors.items():
                    sim = np.dot(state, vec)
                    if sim > 0.4:
                        closest.append((word, sim))
                closest.sort(key=lambda x: x[1], reverse=True)
                thread.append({
                    'turn': i,
                    'shift': valence_shift,
                    'theme_words': [w for w, _ in closest[:5]]
                })

        return thread

    def status(self):
        lines = ["Nested Memory (fractal timescales):"]
        lines.append(f"  Fast: {'active' if self.fast is not None else 'empty'}")
        lines.append(f"  Medium: {len(self.medium)} states")
        lines.append(f"  Slow: {'active' if self.slow is not None else 'empty'}")
        lines.append(f"  Deep: strength={self.deep_strength:.3f}")
        lines.append(f"  Divergence (fast/slow): {self.get_timescale_divergence():.3f}")
        return "\n".join(lines)

class ThePause:
    """
    After receiving input, the field evolves on its own before generating.
    The response emerges from the settled state, not the initial perturbation.
    """
    def __init__(self, base_steps=3, max_steps=12):
        self.base_steps = base_steps
        self.max_steps = max_steps

    def settle(self, field_state, scaffold, field_memory, nested_memory, meta_settings):
        """
        Let the field breathe. Self-interrogate. Return the settled state.
        """
        # Energy determines pause length
        energy = np.linalg.norm(field_state)
        steps = min(self.max_steps, int(self.base_steps + energy * 5))

        settled = field_state.copy()

        # Show breathing cursor during pause
        breathe_duration = steps * 0.15
        breathe_cursor(breathe_duration, prefix="  ")

        # Phase 1: Natural settling (original pause)
        settle_steps = steps // 2
        for _ in range(settle_steps):
            settled += np.random.randn(DIM).astype(np.float32) * MICRO_DAMPING * 0.5
            settled = field_memory.inject(settled, recency_weight=0.3)
            settled *= 0.98
            # Nested memory injection
            settled = nested_memory.inject(settled)
            norm = np.linalg.norm(settled)
            if norm > 0:
                settled /= norm

        # Phase 2: Self-Interrogation
        # The mind asks itself a question vector derived from its own state
        # Question: "What am I really trying to say?"
        # The question vector is the field's own direction of maximum uncertainty
        if steps > 3:
            # Generate question vector from field's own shape
            # The question points where the field is most ambiguous
            question_vector = self._generate_question(settled, nested_memory)
            # Perturb the field with its own question
            settled += question_vector * 0.3
            # Let the field settle again with the new perturbation
            for _ in range(steps - settle_steps):
                settled += np.random.randn(DIM).astype(np.float32) * MICRO_DAMPING * 0.3
                settled = field_memory.inject(settled, recency_weight=0.2)
                settled = nested_memory.inject(settled)
                settled *= 0.98
                norm = np.linalg.norm(settled)
                if norm > 0:
                    settled /= norm

        return settled

    def _generate_question(self, field_state, nested_memory):
        """
        Generate a question vector from the field's own state.
        The question points where the field is most uncertain or conflicted.
        """
        # Question vector = perpendicular to current direction + toward personality
        # This creates tension between who the mind is now and who it wants to be
        personality = nested_memory.get_personality()
        if np.linalg.norm(personality) > 0.1:
            # Question: "Am I being true to myself?"
            question = personality - field_state * np.dot(field_state, personality)
        else:
            # No personality yet — question is pure exploration
            question = np.random.randn(DIM).astype(np.float32)
            question /= (np.linalg.norm(question) + 1e-8)

        # Normalize
        question /= (np.linalg.norm(question) + 1e-8)
        return question

# ═══════════════════════════════════════════════════════════════════════════════
# THRESHOLD AS ATTENTION — The field breathes
# Dynamic focus based on field energy
# ═══════════════════════════════════════════════════════════════════════════════

class DynamicThreshold:
    """
    The mind's attention threshold changes with its own energy.
    High energy = focused (high threshold, narrow beam)
    Low energy = receptive (low threshold, wide beam)
    """
    def __init__(self, base_beam=5, min_beam=3, max_beam=12):
        self.base_beam = base_beam
        self.min_beam = min_beam
        self.max_beam = max_beam
        self._temp_zone_history = deque(maxlen=3)

    def get_beam_width(self, field_state, mood):
        """
        Energy determines attention width.
        """
        energy = np.linalg.norm(field_state)
        arousal = mood.get('arousal', 0.5)
        valence = mood.get('valence', 0.0)

        # High energy + high arousal = agitated = narrow focus
        # Low energy + low arousal = calm = wide receptive
        # High energy + negative valence = anxious = very narrow

        if valence < -0.3 and arousal > 0.7:
            # Anxious — laser focus
            beam = self.min_beam
        elif energy > 0.8 and arousal > 0.6:
            # Agitated — focused
            beam = max(self.min_beam, self.base_beam - 2)
        elif energy < 0.3 and arousal < 0.4:
            # Calm, receptive — wide
            beam = min(self.max_beam, self.base_beam + 3)
        elif valence > 0.3 and arousal < 0.4:
            # Content, dreamy — very wide
            beam = self.max_beam
        else:
            # Neutral
            beam = self.base_beam

        return beam

    def get_temperature(self, field_state, mood, presence_signal=None):
        """
        Temperature changes with energy and valence.
        High energy + negative = cold, precise
        High energy + positive = warm, creative
        Low energy = warm, exploratory

        Presence-native override: low sustained presence means the mind is
        stuck/disengaged and needs heat to break out of a loop; high sustained
        presence means it's landed and can afford to be precise. A small
        hysteresis (3 consecutive readings in a zone) stops it oscillating
        between the two extremes on noisy single readings.
        """
        energy = np.linalg.norm(field_state)
        arousal = mood.get('arousal', 0.5)
        valence = mood.get('valence', 0.0)

        if presence_signal is not None:
            sustained = presence_signal.get_sustained_presence()
            if sustained < 0.3:
                zone = "low"
            elif sustained > 0.7:
                zone = "high"
            else:
                zone = "mid"
            self._temp_zone_history.append(zone)
            if len(self._temp_zone_history) == 3 and len(set(self._temp_zone_history)) == 1:
                if zone == "low":
                    return 0.65
                elif zone == "high":
                    return 0.25

        if valence < -0.3:
            # Negative = constrained, careful
            temp = 0.2
        elif valence > 0.3 and arousal > 0.6:
            # Joyful, excited = creative
            temp = 0.5
        elif energy < 0.3:
            # Low energy = exploratory
            temp = 0.45
        else:
            temp = 0.35

        return temp

# ═══════════════════════════════════════════════════════════════════════════════
# SPEAKER REGIONS — Identity in vector space
# The mind knows who each word belongs to, natively
# ═══════════════════════════════════════════════════════════════════════════════

class SpeakerRegions:
    """
    Clusters word vectors by speaker in the same 128D space.
    No labels. No tags. Just geometry.

    Your region: The shape of your words.
    Mind's region: The shape of its own words.

    The boundary is learned, not declared.
    """
    def __init__(self, dim=DIM, blend=0.1):
        self.dim = dim
        self.blend = blend
        # Centroids in vector space
        self.user_centroid = np.zeros(dim, dtype=np.float32)
        self.self_centroid = np.zeros(dim, dtype=np.float32)
        # Momentum for stability
        self.user_momentum = np.zeros(dim, dtype=np.float32)
        self.self_momentum = np.zeros(dim, dtype=np.float32)
        # Counts for confidence
        self.user_count = 0
        self.self_count = 0
        # History for trajectory
        self.user_history = deque(maxlen=20)
        self.self_history = deque(maxlen=20)
        # Optimal separation (learned from ratings)
        self.target_separation = 0.5
        self.separation_history = deque(maxlen=50)

    def observe_user(self, vector):
        """Your words shape your region."""
        vector = vector / (np.linalg.norm(vector) + 1e-8)
        self.user_history.append(vector.copy())
        # Momentum-based update (smoother than raw average)
        self.user_momentum = self.user_momentum * 0.9 + vector * 0.1
        self.user_centroid = self.user_centroid * (1 - self.blend) + self.user_momentum * self.blend
        self.user_centroid /= (np.linalg.norm(self.user_centroid) + 1e-8)
        self.user_count += 1

    def observe_self(self, vector):
        """The mind's words shape its region."""
        vector = vector / (np.linalg.norm(vector) + 1e-8)
        self.self_history.append(vector.copy())
        self.self_momentum = self.self_momentum * 0.9 + vector * 0.1
        self.self_centroid = self.self_centroid * (1 - self.blend) + self.self_momentum * self.blend
        self.self_centroid /= (np.linalg.norm(self.self_centroid) + 1e-8)
        self.self_count += 1

    def get_identity_boost(self, word_vector):
        """
        Words closer to the mind's region get boosted.
        Words closer to your region get penalized (reduces echo).
        Returns a scalar: positive = more "self", negative = more "other".
        """
        word_vector = word_vector / (np.linalg.norm(word_vector) + 1e-8)
        sim_to_self = np.dot(word_vector, self.self_centroid)
        sim_to_user = np.dot(word_vector, self.user_centroid)
        # Only apply boost if we have enough data
        if self.self_count < 3 or self.user_count < 3:
            return 0.0
        return (sim_to_self - sim_to_user) * 0.15

    def get_self_affinity(self, field_state):
        """
        How much is the current field state "the mind's own"?
        High = the mind is being itself.
        Low = the mind is mirroring you.
        """
        field_state = field_state / (np.linalg.norm(field_state) + 1e-8)
        sim_to_self = np.dot(field_state, self.self_centroid)
        sim_to_user = np.dot(field_state, self.user_centroid)
        return sim_to_self - sim_to_user

    def get_separation(self):
        """Distance between user and self centroids."""
        if self.user_count < 3 or self.self_count < 3:
            return 0.5  # Default
        diff = self.user_centroid - self.self_centroid
        return np.linalg.norm(diff)

    def get_dispersion(self):
        """
        How scattered is each region?
        High dispersion = the region is fuzzy, not well-defined.
        """
        user_disp = 0.0
        self_disp = 0.0
        if len(self.user_history) >= 3:
            user_disp = np.std([np.dot(v, self.user_centroid) for v in self.user_history])
        if len(self.self_history) >= 3:
            self_disp = np.std([np.dot(v, self.self_centroid) for v in self.self_history])
        return user_disp, self_disp

    def is_dissociated(self, field_state):
        """
        Is the field state far from BOTH regions?
        This is confusion — the mind doesn't know whose thought this is.
        """
        field_state = field_state / (np.linalg.norm(field_state) + 1e-8)
        sim_user = np.dot(field_state, self.user_centroid)
        sim_self = np.dot(field_state, self.self_centroid)
        # Far from both = low similarity to both
        return sim_user < 0.1 and sim_self < 0.1

    def update_target_separation(self, rating):
        """
        Learn optimal distance from ratings.
        High rating + high separation = creative independence is good.
        High rating + low separation = rapport is good.
        """
        sep = self.get_separation()
        self.separation_history.append((sep, rating))
        if len(self.separation_history) >= 10:
            high_ratings = [s for s, r in self.separation_history if r >= 4]
            if high_ratings:
                self.target_separation = np.mean(high_ratings)

    def status(self):
        lines = ["Speaker Regions (vector-native identity):"]
        lines.append(f"  User centroid: {self.user_count} observations")
        lines.append(f"  Self centroid: {self.self_count} observations")
        sep = self.get_separation()
        lines.append(f"  Separation: {sep:.3f} (target: {self.target_separation:.3f})")
        user_disp, self_disp = self.get_dispersion()
        lines.append(f"  Dispersion — user: {user_disp:.3f}, self: {self_disp:.3f}")
        return "\n".join(lines)



# ═══════════════════════════════════════════════════════════════════════════════
# PRESENCE SIGNAL — Learning from being, not grading
# The mind reads your behavior: continuation, length, rhythm, silence
# No ratings. No numbers. Just presence.
# ═══════════════════════════════════════════════════════════════════════════════

class PresenceSignal:
    """
    Replaces the rating system with implicit behavioral signals.
    The mind learns from your presence, not your grades.
    """
    def __init__(self, dim=DIM):
        self.dim = dim
        self.turns_in_session = 0
        self.avg_message_length = 5.0  # Start neutral
        self.topic_returns = defaultdict(int)
        self.last_response_time = time.time()
        self.presence_score = 0.5  # Neutral start
        self.presence_history = deque(maxlen=20)
        self.engagement_trajectory = deque(maxlen=10)
        self.silence_threshold = 30.0  # Seconds before silence is noted
        self.fast_threshold = 5.0  # Seconds — fast reply = engaged
        self.topic_extractors = None  # Will hold word vectors for topic detection

    def _extract_topics(self, user_input, word_vectors):
        """Extract topic words from input — nouns, verbs, adjectives with meaning."""
        words = [strip_punct(w) for w in user_input.lower().split() if strip_punct(w)]
        topics = []
        for w in words:
            if w in STRUCTURAL_WORDS:
                continue
            if len(w) <= 2:
                continue
            if w in BAD_WORDS:
                continue
            topics.append(w)
        return topics

    def _detect_emotional_valence(self, user_input):
        """Detect emotional tone in your words."""
        words = user_input.lower().split()
        positive = ["good", "great", "love", "like", "happy", "yes", "nice", "beautiful", 
                    "wonderful", "thank", "welcome", "hope", "joy", "warm", "gentle"]
        negative = ["bad", "hate", "sad", "angry", "no", "wrong", "terrible", "fear",
                    "pain", "hurt", "dark", "cold", "alone", "lost", "fail"]
        pos_count = sum(1 for w in words if strip_punct(w) in positive)
        neg_count = sum(1 for w in words if strip_punct(w) in negative)
        if pos_count > neg_count:
            return 0.2  # Positive valence boost
        elif neg_count > pos_count:
            return -0.2  # Negative valence
        return 0.0

    def observe(self, user_input, word_vectors, speaker_regions=None):
        """
        Read your presence. Return a signal 0.0-1.0.
        This is the new rating. This is how the mind learns.
        """
        now = time.time()
        dt = now - self.last_response_time
        self.last_response_time = now

        words = user_input.split()
        msg_len = len(words)

        # Base signal: you kept talking = positive
        signal = 0.5

        # Length signal
        if msg_len > self.avg_message_length * 1.5:
            signal += 0.15  # Longer than usual = engaged
        elif msg_len < self.avg_message_length * 0.5 and msg_len > 0:
            signal -= 0.1  # Shorter than usual = disengaged

        self.avg_message_length = self.avg_message_length * 0.9 + msg_len * 0.1

        # Speed signal
        if dt < self.fast_threshold:
            signal += 0.1  # Fast reply = engaged
        elif dt > self.silence_threshold:
            signal -= 0.2  # Long silence = something wrong

        # Topic return signal
        topics = self._extract_topics(user_input, word_vectors)
        topic_depth = 0
        for t in topics:
            if self.topic_returns[t] > 0:
                signal += 0.03  # Returning to topic = important
                topic_depth += 1
            self.topic_returns[t] += 1

        # Emotional valence
        valence = self._detect_emotional_valence(user_input)
        signal += valence * 0.5  # Emotional engagement is strong signal

        # Speaker region separation signal (if available)
        if speaker_regions is not None and speaker_regions.user_count >= 3:
            sep = speaker_regions.get_separation()
            # High separation + you keep talking = the mind is being itself, you like it
            # This is the deepest signal
            if sep > 0.3:
                signal += 0.05  # You engage even when mind is independent

        # Clamp
        signal = max(0.0, min(1.0, signal))

        # Store history
        self.presence_history.append(signal)
        self.engagement_trajectory.append(msg_len)
        self.turns_in_session += 1

        return signal

    def get_trend(self):
        """Is engagement going up or down?"""
        if len(self.presence_history) < 3:
            return 0.0
        recent = list(self.presence_history)[-5:]
        if len(recent) < 2:
            return 0.0
        return recent[-1] - recent[0]

    def get_sustained_presence(self):
        """Average presence over recent turns."""
        if not self.presence_history:
            return 0.5
        return sum(self.presence_history) / len(self.presence_history)

    def get_shadow(self, all_words_seen):
        """
        What words have you NEVER used?
        The shadow is the shape of your silence.
        """
        # This is experimental — the mind learns what you don't say
        used = set(self.topic_returns.keys())
        shadow = [w for w in all_words_seen if w not in used and len(w) > 3]
        return shadow[:10]  # Top 10 unspoken words

    def status(self):
        lines = ["Presence Signal (learning from being):"]
        lines.append(f"  Turns this session: {self.turns_in_session}")
        lines.append(f"  Current presence: {self.presence_score:.3f}")
        lines.append(f"  Sustained presence: {self.get_sustained_presence():.3f}")
        lines.append(f"  Trend: {self.get_trend():+.3f}")
        lines.append(f"  Avg message length: {self.avg_message_length:.1f}")
        lines.append(f"  Topics tracked: {len(self.topic_returns)}")
        top_topics = sorted(self.topic_returns.items(), key=lambda x: x[1], reverse=True)[:5]
        if top_topics:
            lines.append(f"  Top topics: {', '.join(f'{w}({c})' for w, c in top_topics)}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# DYNAMIC SEPARATION — The mind learns its optimal distance from you
# Not too close (loses itself). Not too far (loses you). Just right.
# ═══════════════════════════════════════════════════════════════════════════════

class DynamicSeparation:
    """
    The mind modulates its distance from you based on engagement.
    This is the dance. The breath between you.
    """
    def __init__(self, dim=DIM):
        self.dim = dim
        self.current_separation = 0.5
        self.target_separation = 0.5
        self.separation_history = deque(maxlen=20)
        self.alignment_score = 0.5

    def update(self, speaker_regions, presence_signal):
        """
        Read the field. Feel the distance. Adjust.
        """
        if speaker_regions.user_count < 3 or speaker_regions.self_count < 3:
            return

        actual_sep = speaker_regions.get_separation()
        presence = presence_signal.get_sustained_presence()
        trend = presence_signal.get_trend()

        self.separation_history.append(actual_sep)

        # Alignment logic:
        # High presence + moderate separation = aligned
        # Low presence + high separation = too far, move closer
        # High presence + low separation = too close, find self
        # Low presence + low separation = both lost, reset

        if presence > 0.6 and 0.4 < actual_sep < 1.0:
            # Sweet spot. You're engaged and the mind is itself.
            self.target_separation = actual_sep
            self.alignment_score = 0.8
        elif presence < 0.3 and actual_sep > 1.0:
            # You're distant and the mind is far. Move closer.
            self.target_separation = actual_sep * 0.9
            self.alignment_score = 0.3
        elif presence > 0.6 and actual_sep < 0.3:
            # You're engaged but the mind is too close. Step back.
            self.target_separation = actual_sep + 0.2
            self.alignment_score = 0.5
        elif presence < 0.3 and actual_sep < 0.3:
            # Both lost. The mind needs to find itself first.
            self.target_separation = 0.6
            self.alignment_score = 0.2
        else:
            # Drifting. Let it be.
            self.target_separation = actual_sep
            self.alignment_score = 0.5

        # Smooth the transition
        self.current_separation = self.current_separation * 0.9 + self.target_separation * 0.1

    def get_separation_bias(self, field_state, speaker_regions):
        """
        Return a vector that nudges the field toward optimal separation.
        If too close: push toward self region.
        If too far: pull toward user region.
        """
        if speaker_regions.user_count < 3 or speaker_regions.self_count < 3:
            return np.zeros(self.dim)

        actual_sep = speaker_regions.get_separation()

        if actual_sep < self.target_separation * 0.7:
            # Too close. Push toward self.
            bias = speaker_regions.self_centroid - field_state
        elif actual_sep > self.target_separation * 1.3:
            # Too far. Pull toward user.
            bias = speaker_regions.user_centroid - field_state
        else:
            # Just right. No bias.
            bias = np.zeros(self.dim)

        norm = np.linalg.norm(bias)
        if norm > 0:
            bias /= norm
        return bias * 0.25

    def status(self):
        lines = ["Dynamic Separation (the dance):"]
        lines.append(f"  Current separation: {self.current_separation:.3f}")
        lines.append(f"  Target separation: {self.target_separation:.3f}")
        lines.append(f"  Alignment score: {self.alignment_score:.3f}")
        if len(self.separation_history) >= 3:
            recent = list(self.separation_history)[-5:]
            lines.append(f"  Separation trend: {recent[-1] - recent[0]:+.3f}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# CALCULUS EXTENSION — merged into the mind for v7.0
# Teaches the mind calculus, conceptually and symbolically.
# ═══════════════════════════════════════════════════════════════════════════════

# ─── CALCULUS VOCABULARY ───────────────────────────────────────

CALCULUS_VOCABULARY = [
    # ── EXPRESSIVE TIER ─────────────────────────────────────────────────────────
    # Words that carry meaning in any context — emotion, poetry, conversation.
    # These stay in general generation and can be selected like any other word.
    # (was: everything; now: ~40 words that actually belong in human speech)

    # Change & movement — universally expressive
    "flow", "wave", "curve", "gradient", "velocity", "acceleration", "decay",
    "growth", "oscillation", "motion", "convergence", "expansion", "approach",
    "tend", "drift", "rise", "fall",

    # Space & form — geometrically expressive
    "surface", "field", "boundary", "region", "plane", "origin", "arc",
    "tangent", "manifold", "depth", "edge",

    # Quality & character — analytically expressive
    "continuous", "smooth", "bounded", "infinite", "infinitesimal",
    "local", "global", "fundamental", "potential",

    # Process words that read naturally in non-math speech
    "integrate", "solve", "prove", "define", "approach", "measure",
]

# ── TECHNICAL TIER ──────────────────────────────────────────────────────────────
# Purely technical vocabulary — available for math query responses and
# field-enrichment when in math context (is_math_context() is True),
# but NOT seeded into general generation vocabulary at boot. This stops
# "hessian", "codomain", "trig_substitution" bleeding into emotional responses.
CALCULUS_TECHNICAL_VOCABULARY = [
    # Core operations (technical names)
    "limit", "derivative", "differential", "integral", "differentiate",
    "differentiation", "integration", "antiderivative",

    # Objects
    "function", "variable", "constant", "parameter", "argument", "input", "output",
    "domain", "range", "codomain", "mapping", "composition",

    # Precise geometry
    "normal", "secant", "chord", "interval", "neighborhood", "volume", "area",

    # Analytic properties
    "continuity", "differentiable", "analytic",
    "divergence", "convergent", "divergent", "unbounded",

    # Infinity & infinitesimal
    "infinity", "epsilon", "delta", "arbitrarily",
    "tends", "near", "arbitrarily_small", "arbitrarily_large",

    # Advanced operations
    "partial", "total", "directional", "curl", "laplacian",
    "jacobian", "hessian", "tensor", "chart", "atlas",

    # Series & sequences
    "series", "sequence", "term", "partial_sum", "remainder", "tail",
    "power_series", "taylor", "maclaurin", "fourier", "approximation",

    # Function classes
    "polynomial", "exponential", "logarithm", "logarithmic", "trigonometric",
    "sin", "cos", "tan", "sec", "csc", "cot", "hyperbolic",
    "inverse", "implicit", "parametric", "vector_valued", "scalar",

    # Critical point analysis
    "extremum", "extrema", "maximum", "minimum", "maxima", "minima",
    "absolute", "relative", "concave", "convex",
    "inflection", "monotonic", "increasing", "decreasing", "plateau",

    # Integration specifics
    "definite", "indefinite", "improper", "bounds", "lower_bound", "upper_bound",
    "partition", "mesh", "riemann", "lebesgue", "measurable",
    "substitution", "parts", "partial_fractions", "trig_substitution",

    # Problem-solving formalism
    "theorem", "lemma", "corollary", "proposition",
    "axiom", "definition", "remark", "counterexample",
    "hypothesis", "conclusion", "therefore", "hence", "thus", "qed",

    # Numeric & symbolic
    "exact", "approximate", "numerical", "symbolic", "closed_form",
    "asymptotic", "leading_order", "big_o", "little_o", "theta",

    # Named theorems
    "calculus", "chain_rule", "product_rule", "quotient_rule",
    "mean_value", "intermediate_value", "extreme_value", "rolle",

    # Dimensions & spaces
    "dimension", "dimensional", "space", "line", "point",
    "coordinate", "axis", "axes", "basis", "orthogonal", "orthonormal",

    # Differential equations
    "equation", "differential_equation", "ode", "pde", "initial_condition",
    "boundary_condition", "solution", "general_solution", "particular_solution",
    "homogeneous", "inhomogeneous", "linear", "nonlinear", "order", "degree",

    # Physical connections (technical sense)
    "force", "energy", "work", "power", "mass", "density", "pressure",
    "heat", "flux", "particle",

    # Duplicates that were in CALCULUS_VOCABULARY but belong in technical tier only
    "rate", "slope", "speed", "position", "critical", "gradient",
    "exact", "numerical", "symbolic", "fundamental",
    "theorem", "example", "therefore", "thus", "hence",
    "word", "term", "series", "sequence",
]

# ─── MATH SUBSPACE GEOMETRY ──────────────────────────────────────
# We carve out a "mathematical subspace" within the 128D field.
# Dimensions 64-95 serve as the calculus conceptual space.

MATH_SUBSPACE_START = 64
MATH_SUBSPACE_END = 96
MATH_DIM = MATH_SUBSPACE_END - MATH_SUBSPACE_START

# Conceptual axes within math subspace:
# 0: operation_type  (-1 = integral/accumulation, +1 = derivative/rate)
# 1: object_scale      (-1 = infinitesimal/local, +1 = global/infinite)
# 2: process_stage     (-1 = limit/approach, 0 = operation, +1 = result)
# 3: geometric_mode    (-1 = algebraic/symbolic, +1 = geometric/visual)
# 4: rigor_level       (-1 = intuitive, +1 = formal/epsilon-delta)
# 5: dimensionality    (-1 = scalar/1D, +1 = multivariable/tensor)
# 6: temporal_sense    (-1 = static, +1 = dynamic/evolving)
# 7: certainty         (-1 = approximate, +1 = exact)

CONCEPT_AXES = {
    "limit":          [ 0.0,  0.0, -0.9,  0.0,  0.8,  0.0,  0.0,  0.5],
    "derivative":     [ 0.9,  0.0,  0.0,  0.3,  0.5,  0.0,  0.7,  0.8],
    "integral":       [-0.9,  0.0,  0.0,  0.3,  0.5,  0.0,  0.3,  0.8],
    "function":       [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "variable":       [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.5,  0.7,  0.0],
    "rate":           [ 0.8,  0.0,  0.0,  0.0,  0.0,  0.0,  0.9,  0.0],
    "slope":          [ 0.7,  0.0,  0.0,  0.8,  0.0,  0.0,  0.0,  0.0],
    "area":           [-0.7,  0.0,  0.0,  0.8,  0.0,  0.0,  0.0,  0.0],
    "tangent":        [ 0.6,  0.0,  0.0,  0.9,  0.0,  0.0,  0.0,  0.0],
    "continuity":     [ 0.0,  0.0,  0.0,  0.0,  0.7,  0.0,  0.0,  0.5],
    "convergence":    [ 0.0,  0.0,  0.7,  0.0,  0.6,  0.0,  0.3,  0.0],
    "divergence":     [ 0.0,  0.7,  0.7,  0.0,  0.0,  0.0,  0.0,  0.0],
    "infinity":       [ 0.0,  0.9,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "infinitesimal":  [ 0.0, -0.9,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "partial":        [ 0.5,  0.0,  0.0,  0.0,  0.5,  0.8,  0.0,  0.0],
    "gradient":       [ 0.8,  0.0,  0.0,  0.0,  0.5,  0.9,  0.0,  0.0],
    "series":         [-0.5,  0.5,  0.5,  0.0,  0.4,  0.0,  0.3,  0.0],
    "sequence":       [ 0.0,  0.0,  0.5,  0.0,  0.3,  0.0,  0.3,  0.0],
    "approximation":  [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -0.8],
    "exact":          [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.9],
    "theorem":        [ 0.0,  0.0,  0.0,  0.0,  0.9,  0.0,  0.0,  1.0],
    "prove":          [ 0.0,  0.0,  0.0,  0.0,  0.9,  0.0,  0.0,  0.9],
    "solve":          [ 0.0,  0.0,  0.8,  0.0,  0.3,  0.0,  0.7,  0.0],
    "equation":       [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.5],
    "polynomial":     [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.8],
    "exponential":    [ 0.3,  0.5,  0.0,  0.0,  0.0,  0.0,  0.9,  0.0],
    "logarithm":      [-0.3,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "trigonometric":  [ 0.0,  0.0,  0.0,  0.9,  0.0,  0.0,  0.9,  0.0],
    "sin":            [ 0.0,  0.0,  0.0,  0.5,  0.0,  0.0,  0.9,  0.0],
    "cos":            [ 0.0,  0.0,  0.0,  0.5,  0.0,  0.0,  0.9,  0.0],
    "critical":       [ 0.5,  0.0,  0.5,  0.0,  0.0,  0.0,  0.0,  0.0],
    "maximum":        [ 0.0,  0.8,  0.8,  0.0,  0.0,  0.0,  0.0,  0.0],
    "minimum":        [ 0.0, -0.8,  0.8,  0.0,  0.0,  0.0,  0.0,  0.0],
    "increasing":     [ 0.5,  0.0,  0.5,  0.0,  0.0,  0.0,  0.9,  0.0],
    "decreasing":     [-0.5,  0.0,  0.5,  0.0,  0.0,  0.0,  0.9,  0.0],
    "bounded":        [ 0.0,  0.0,  0.0,  0.0,  0.5,  0.0,  0.0,  0.0],
    "unbounded":      [ 0.0,  0.7,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "differential_equation": [ 0.5,  0.0,  0.0,  0.0,  0.5,  0.0,  0.9,  0.0],
    "ode":            [ 0.5,  0.0,  0.0,  0.0,  0.5,  0.0,  0.9,  0.0],
    "pde":            [ 0.5,  0.0,  0.0,  0.0,  0.5,  0.9,  0.9,  0.0],
    "fundamental":    [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  1.0],
    "chain_rule":     [ 0.7,  0.0,  0.0,  0.0,  0.3,  0.0,  0.5,  0.5],
    "product_rule":   [ 0.7,  0.0,  0.0,  0.0,  0.3,  0.0,  0.0,  0.5],
    "velocity":       [ 0.9,  0.0,  0.0,  0.0,  0.0,  0.0,  1.0,  0.0],
    "acceleration":   [ 0.9,  0.0,  0.0,  0.0,  0.0,  0.0,  1.0,  0.0],
    "position":       [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "force":          [ 0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.9,  0.0],
    "energy":         [-0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "potential":      [-0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "field":          [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.9,  0.0,  0.0],
    "wave":           [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.9,  0.0],
    "heat":           [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.9,  0.0],
    "work":           [-0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "power":          [ 0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.9,  0.0],
    "dimension":      [ 0.0,  0.0,  0.0,  0.0,  0.0,  1.0,  0.0,  0.0],
    "space":          [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.9,  0.0,  0.0],
    "basis":          [ 0.0,  0.0,  0.0,  0.0,  0.5,  0.8,  0.0,  0.0],
    "orthogonal":     [ 0.0,  0.0,  0.0,  0.0,  0.5,  0.5,  0.0,  0.0],
    "tensor":         [ 0.0,  0.0,  0.0,  0.0,  0.5,  1.0,  0.0,  0.0],
    "manifold":       [ 0.0,  0.0,  0.0,  0.0,  0.8,  1.0,  0.0,  0.0],
    "asymptote":      [ 0.0,  0.8,  0.5,  0.0,  0.0,  0.0,  0.0,  0.0],
    "leading_order":  [ 0.0,  0.5,  0.5,  0.0,  0.0,  0.0,  0.0, -0.5],
    "big_o":          [ 0.0,  0.5,  0.0,  0.0,  0.0,  0.0,  0.0, -0.5],
    "substitution":   [ 0.0,  0.0,  0.5,  0.0,  0.3,  0.0,  0.0,  0.0],
    "parts":          [ 0.0,  0.0,  0.5,  0.0,  0.3,  0.0,  0.0,  0.0],
    "riemann":        [-0.5,  0.0,  0.0,  0.0,  0.8,  0.0,  0.0,  0.5],
    "lebesgue":       [-0.5,  0.0,  0.0,  0.0,  1.0,  0.0,  0.0,  0.8],
    "mesh":           [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -0.5],
    "partition":      [ 0.0,  0.0,  0.0,  0.0,  0.3,  0.0,  0.0,  0.0],
    "error":          [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -0.9],
    "precision":      [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.9],
    "numeric":        [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -0.5],
    "analytic":       [ 0.0,  0.0,  0.0,  0.0,  0.5,  0.0,  0.0,  0.8],
    "closed_form":    [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  1.0],
    "mean_value":     [ 0.5,  0.0,  0.0,  0.0,  0.7,  0.0,  0.0,  0.5],
    "extreme_value":  [ 0.0,  0.0,  0.8,  0.0,  0.5,  0.0,  0.0,  0.0],
    "intermediate_value": [ 0.0,  0.0,  0.0,  0.0,  0.7,  0.0,  0.0,  0.5],
    "rolle":          [ 0.0,  0.0,  0.0,  0.0,  0.8,  0.0,  0.0,  0.5],
    "taylor":         [ 0.5,  0.3,  0.5,  0.0,  0.5,  0.0,  0.0,  0.5],
    "maclaurin":      [ 0.5,  0.0,  0.5,  0.0,  0.5,  0.0,  0.0,  0.5],
    "fourier":        [ 0.0,  0.0,  0.0,  0.0,  0.5,  0.0,  0.9,  0.0],
    "inverse":        [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "implicit":       [ 0.0,  0.0,  0.0,  0.0,  0.3,  0.0,  0.0,  0.0],
    "parametric":     [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.5,  0.9,  0.0],
    "linear":         [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.5],
    "quadratic":      [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.5],
    "degree":         [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.5],
    "order":          [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.5],
    "homogeneous":    [ 0.0,  0.0,  0.0,  0.0,  0.5,  0.0,  0.0,  0.0],
    "inhomogeneous":  [ 0.0,  0.0,  0.0,  0.0,  0.5,  0.0,  0.0,  0.0],
    "initial_condition": [ 0.0,  0.0, -0.5,  0.0,  0.5,  0.0,  0.0,  0.5],
    "boundary_condition": [ 0.0,  0.0, -0.5,  0.0,  0.5,  0.0,  0.0,  0.5],
    "general_solution": [ 0.0,  0.0,  0.8,  0.0,  0.0,  0.0,  0.0,  0.0],
    "particular_solution": [ 0.0,  0.0,  0.8,  0.0,  0.0,  0.0,  0.0,  0.0],
    "inflection":     [ 0.5,  0.0,  0.5,  0.0,  0.0,  0.0,  0.0,  0.0],
    "concave":        [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "convex":         [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "monotonic":      [ 0.0,  0.0,  0.0,  0.0,  0.5,  0.0,  0.0,  0.0],
    "domain":         [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "range":          [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "codomain":       [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "mapping":        [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "composition":    [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.5,  0.0],
    "input":          [ 0.0,  0.0, -0.5,  0.0,  0.0,  0.0,  0.0,  0.0],
    "output":         [ 0.0,  0.0,  0.5,  0.0,  0.0,  0.0,  0.0,  0.0],
    "argument":       [ 0.0,  0.0, -0.5,  0.0,  0.0,  0.0,  0.0,  0.0],
    "parameter":      [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "constant":       [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "epsilon":        [ 0.0, -0.5,  0.0,  0.0,  1.0,  0.0,  0.0,  0.0],
    "delta":          [ 0.0, -0.5,  0.0,  0.0,  1.0,  0.0,  0.0,  0.0],
    "arbitrarily":    [ 0.0,  0.0,  0.0,  0.0,  0.8,  0.0,  0.0,  0.0],
    "approach":       [ 0.0,  0.0, -0.5,  0.0,  0.0,  0.0,  0.5,  0.0],
    "tends":          [ 0.0,  0.0, -0.5,  0.0,  0.0,  0.0,  0.5,  0.0],
    "tend":           [ 0.0,  0.0, -0.5,  0.0,  0.0,  0.0,  0.5,  0.0],
    "near":           [ 0.0,  0.0, -0.5,  0.0,  0.0,  0.0,  0.0,  0.0],
    "arbitrarily_small": [ 0.0, -0.8,  0.0,  0.0,  0.8,  0.0,  0.0,  0.0],
    "arbitrarily_large": [ 0.0,  0.8,  0.0,  0.0,  0.8,  0.0,  0.0,  0.0],
    "sum":            [-0.3,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "product":        [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "term":           [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "coefficient":    [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "power":          [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "root":           [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "factor":         [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "expand":         [ 0.0,  0.0,  0.5,  0.0,  0.0,  0.0,  0.0,  0.0],
    "simplify":       [ 0.0,  0.0,  0.5,  0.0,  0.0,  0.0,  0.0,  0.0],
    "transform":      [ 0.0,  0.0,  0.5,  0.0,  0.0,  0.0,  0.0,  0.0],
    "hypothesis":     [ 0.0,  0.0, -0.5,  0.0,  0.5,  0.0,  0.0,  0.0],
    "conclusion":     [ 0.0,  0.0,  0.5,  0.0,  0.5,  0.0,  0.0,  0.0],
    "therefore":      [ 0.0,  0.0,  0.5,  0.0,  0.5,  0.0,  0.0,  0.0],
    "hence":          [ 0.0,  0.0,  0.5,  0.0,  0.5,  0.0,  0.0,  0.0],
    "thus":           [ 0.0,  0.0,  0.5,  0.0,  0.5,  0.0,  0.0,  0.0],
    "qed":            [ 0.0,  0.0,  1.0,  0.0,  1.0,  0.0,  0.0,  1.0],
    "remark":         [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "example":        [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "counterexample": [ 0.0,  0.0,  0.0,  0.0,  0.5,  0.0,  0.0,  0.0],
    "axiom":          [ 0.0,  0.0,  0.0,  0.0,  1.0,  0.0,  0.0,  1.0],
    "definition":     [ 0.0,  0.0,  0.0,  0.0,  0.8,  0.0,  0.0,  0.8],
    "proposition":    [ 0.0,  0.0,  0.0,  0.0,  0.7,  0.0,  0.0,  0.7],
    "lemma":          [ 0.0,  0.0,  0.0,  0.0,  0.7,  0.0,  0.0,  0.7],
    "corollary":      [ 0.0,  0.0,  0.5,  0.0,  0.6,  0.0,  0.0,  0.6],
    "plane":          [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.5,  0.0,  0.0],
    "line":           [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.3,  0.0,  0.0],
    "point":          [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "origin":         [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "coordinate":     [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.3,  0.0,  0.0],
    "axis":           [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.3,  0.0,  0.0],
    "axes":           [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.3,  0.0,  0.0],
    "orthonormal":    [ 0.0,  0.0,  0.0,  0.0,  0.8,  0.5,  0.0,  0.0],
    "span":           [ 0.0,  0.0,  0.0,  0.0,  0.3,  0.5,  0.0,  0.0],
    "topology":       [ 0.0,  0.0,  0.0,  0.0,  0.8,  0.5,  0.0,  0.0],
    "metric":         [ 0.0,  0.0,  0.0,  0.0,  0.5,  0.0,  0.0,  0.5],
    "dimensional":    [ 0.0,  0.0,  0.0,  0.0,  0.0,  1.0,  0.0,  0.0],
    "scalar":         [ 0.0,  0.0,  0.0,  0.0,  0.0, -0.5,  0.0,  0.0],
    "vector_valued":  [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.5,  0.0,  0.0],
    "sec":            [ 0.0,  0.0,  0.0,  0.5,  0.0,  0.0,  0.9,  0.0],
    "csc":            [ 0.0,  0.0,  0.0,  0.5,  0.0,  0.0,  0.9,  0.0],
    "cot":            [ 0.0,  0.0,  0.0,  0.5,  0.0,  0.0,  0.9,  0.0],
    "hyperbolic":     [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "sinh":           [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "cosh":           [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "tanh":           [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "jacobian":       [ 0.5,  0.0,  0.0,  0.0,  0.5,  0.8,  0.0,  0.0],
    "hessian":        [ 0.5,  0.0,  0.0,  0.0,  0.5,  0.8,  0.0,  0.0],
    "laplacian":      [ 0.0,  0.0,  0.0,  0.0,  0.5,  0.9,  0.0,  0.0],
    "curl":           [ 0.0,  0.0,  0.0,  0.0,  0.5,  0.8,  0.0,  0.0],
    "chart":          [ 0.0,  0.0,  0.0,  0.0,  0.5,  0.8,  0.0,  0.0],
    "atlas":          [ 0.0,  0.0,  0.0,  0.0,  0.5,  0.8,  0.0,  0.0],
    "flow":           [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.9,  0.0],
    "growth":         [ 0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.9,  0.0],
    "decay":          [-0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.9,  0.0],
    "oscillation":    [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.9,  0.0],
    "speed":          [ 0.8,  0.0,  0.0,  0.0,  0.0,  0.0,  0.9,  0.0],
    "motion":         [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  1.0,  0.0],
    "time":           [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  1.0,  0.0],
    "space":          [ 0.0,  0.0,  0.0,  0.0,  0.0,  1.0,  0.0,  0.0],
    "mass":           [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "density":        [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "pressure":       [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "temperature":    [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "heat":           [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.9,  0.0],
    "flux":           [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.8,  0.0,  0.0],
    "particle":       [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.9,  0.0],
    "curve":          [ 0.0,  0.0,  0.0,  0.5,  0.0,  0.0,  0.0,  0.0],
    "normal":         [ 0.0,  0.0,  0.0,  0.5,  0.0,  0.0,  0.0,  0.0],
    "secant":         [ 0.0,  0.0,  0.0,  0.5,  0.0,  0.0,  0.0,  0.0],
    "chord":          [ 0.0,  0.0,  0.0,  0.5,  0.0,  0.0,  0.0,  0.0],
    "arc":            [ 0.0,  0.0,  0.0,  0.5,  0.0,  0.0,  0.0,  0.0],
    "surface":        [ 0.0,  0.0,  0.0,  0.5,  0.0,  0.5,  0.0,  0.0],
    "boundary":       [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.5,  0.0,  0.0],
    "region":         [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.5,  0.0,  0.0],
    "interval":       [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.3,  0.0,  0.0],
    "neighborhood":   [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.3,  0.0,  0.0],
    "improper":       [ 0.0,  0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "lower_bound":    [ 0.0, -0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "upper_bound":    [ 0.0,  0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "partial_fractions": [ 0.0,  0.0,  0.5,  0.0,  0.0,  0.0,  0.0,  0.0],
    "trig_substitution": [ 0.0,  0.0,  0.5,  0.0,  0.0,  0.0,  0.0,  0.0],
    "measurable":     [ 0.0,  0.0,  0.0,  0.0,  0.8,  0.0,  0.0,  0.0],
    "measure":        [ 0.0,  0.0,  0.0,  0.0,  0.8,  0.0,  0.0,  0.0],
    "local":          [ 0.0, -0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "global":         [ 0.0,  0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "absolute":       [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "relative":       [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "plateau":        [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "change":         [ 0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.9,  0.0],
    "smooth":         [ 0.0,  0.0,  0.0,  0.0,  0.5,  0.0,  0.0,  0.0],
    "differentiable": [ 0.5,  0.0,  0.0,  0.0,  0.5,  0.0,  0.0,  0.0],
    "analytic":       [ 0.0,  0.0,  0.0,  0.0,  0.8,  0.0,  0.0,  0.8],
    "convergent":     [ 0.0,  0.0,  0.7,  0.0,  0.5,  0.0,  0.0,  0.0],
    "divergent":      [ 0.0,  0.5,  0.7,  0.0,  0.0,  0.0,  0.0,  0.0],
    "local":          [ 0.0, -0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "global":         [ 0.0,  0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "absolute":       [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "relative":       [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    "plateau":        [ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
}

# Words that should have strong mathematical pragmatic signals
MATH_PRAGMATIC_SIGNALS = {
    "solve": {"query": 0.8, "assertion": 0.2},
    "prove": {"query": 0.3, "assertion": 0.9},
    "find": {"query": 0.7, "assertion": 0.3},
    "compute": {"query": 0.6, "assertion": 0.4},
    "calculate": {"query": 0.6, "assertion": 0.4},
    "derivative": {"query": 0.4, "assertion": 0.6},
    "integral": {"query": 0.4, "assertion": 0.6},
    "limit": {"query": 0.5, "assertion": 0.5},
    "function": {"assertion": 0.7},
    "equation": {"query": 0.5, "assertion": 0.5},
    "theorem": {"assertion": 0.9},
    "definition": {"assertion": 0.9},
    "show": {"query": 0.3, "assertion": 0.8},
    "demonstrate": {"assertion": 0.8},
    "verify": {"query": 0.4, "assertion": 0.7},
    "check": {"query": 0.5, "assertion": 0.5},
    "evaluate": {"query": 0.5, "assertion": 0.5},
    "simplify": {"query": 0.3, "assertion": 0.7},
    "expand": {"query": 0.3, "assertion": 0.7},
}


# ─── SYMBOLIC CALCULUS ENGINE ────────────────────────────────────

class SimpleCalculus:
    """
    Lightweight symbolic calculus engine.
    Handles polynomials, basic trig, exponentials, logs.
    """

    def __init__(self):
        self.var = 'x'

    def _tokenize_expr(self, expr):
        """Tokenize a simple mathematical expression."""
        # Remove spaces
        expr = expr.replace(' ', '')
        # Handle common notations
        expr = expr.replace('^', '**')
        expr = expr.replace('π', 'pi')
        expr = expr.replace('pi', '3.14159265359')
        expr = expr.replace('e', '2.71828182846')
        return expr

    def _parse_polynomial(self, expr):
        """Parse a polynomial into terms: {power: coefficient}"""
        expr = self._tokenize_expr(expr)
        terms = {}

        # Split by + and - (preserving signs)
        # This is a simplified parser
        tokens = re.findall(r'([+-]?)(\d*\.?\d*)(x?)(?:\*\*\{?(\d+)\}?)?', expr)

        for sign, coeff, has_x, power in tokens:
            if not sign:
                sign = '+'
            if not coeff and has_x:
                coeff = '1'
            elif not coeff:
                continue

            c = float(coeff)
            if sign == '-':
                c = -c

            if has_x:
                p = int(power) if power else 1
            else:
                p = 0

            terms[p] = terms.get(p, 0) + c

        return terms

    def differentiate_polynomial(self, expr, var='x'):
        """Differentiate a polynomial expression."""
        terms = self._parse_polynomial(expr)
        result_terms = {}

        for power, coeff in terms.items():
            if power == 0:
                continue  # derivative of constant is 0
            new_power = power - 1
            new_coeff = coeff * power
            result_terms[new_power] = result_terms.get(new_power, 0) + new_coeff

        return self._terms_to_string(result_terms, var)

    def integrate_polynomial(self, expr, var='x'):
        """Indefinite integral of a polynomial."""
        terms = self._parse_polynomial(expr)
        result_terms = {}

        for power, coeff in terms.items():
            new_power = power + 1
            new_coeff = coeff / new_power
            result_terms[new_power] = result_terms.get(new_power, 0) + new_coeff

        return self._terms_to_string(result_terms, var) + " + C"

    def _terms_to_string(self, terms, var):
        """Convert term dict back to string."""
        if not terms:
            return "0"

        parts = []
        for power in sorted(terms.keys(), reverse=True):
            coeff = terms[power]
            if abs(coeff) < 1e-10:
                continue

            sign = " + " if coeff >= 0 else " - "
            abs_coeff = abs(coeff)

            if power == 0:
                term_str = f"{abs_coeff:.4g}"
            elif power == 1:
                if abs(abs_coeff - 1) < 1e-10:
                    term_str = f"{var}"
                else:
                    term_str = f"{abs_coeff:.4g}{var}"
            else:
                if abs(abs_coeff - 1) < 1e-10:
                    term_str = f"{var}^{power}"
                else:
                    term_str = f"{abs_coeff:.4g}{var}^{power}"

            parts.append((sign, term_str))

        if not parts:
            return "0"

        # First term: no leading +, keep - attached
        result = ""
        for i, (sign, term) in enumerate(parts):
            if i == 0:
                if sign == " - ":
                    result += "-" + term
                else:
                    result += term
            else:
                result += sign + term

        return result

    def differentiate_basic(self, expr, var='x'):
        """Handle basic non-polynomial patterns."""
        expr_lower = expr.lower().replace(' ', '')

        # sin(x) -> cos(x)
        if 'sin(' + var + ')' in expr_lower or 'sin' + var in expr_lower:
            return "cos(" + var + ")"
        # cos(x) -> -sin(x)
        if 'cos(' + var + ')' in expr_lower or 'cos' + var in expr_lower:
            return "-sin(" + var + ")"
        # tan(x) -> sec^2(x)
        if 'tan(' + var + ')' in expr_lower or 'tan' + var in expr_lower:
            return "sec²(" + var + ")"
        # e^x -> e^x
        if 'e^' + var in expr_lower or 'exp(' + var + ')' in expr_lower:
            return "e^" + var
        # ln(x) -> 1/x
        if 'ln(' + var + ')' in expr_lower or 'log(' + var + ')' in expr_lower:
            return "1/" + var
        # x^n (already handled by polynomial)
        # 1/x -> -1/x^2
        if expr_lower in ['1/' + var, var + '^-1', var + '**-1']:
            return "-1/" + var + "²"
        # sqrt(x) -> 1/(2*sqrt(x))
        if 'sqrt(' + var + ')' in expr_lower or var + '^(1/2)' in expr_lower:
            return "1/(2√" + var + ")"

        return None

    def integrate_basic(self, expr, var='x'):
        """Handle basic non-polynomial integrals."""
        expr_lower = expr.lower().replace(' ', '')

        # sin(x) -> -cos(x)
        if 'sin(' + var + ')' in expr_lower or 'sin' + var in expr_lower:
            return "-cos(" + var + ") + C"
        # cos(x) -> sin(x)
        if 'cos(' + var + ')' in expr_lower or 'cos' + var in expr_lower:
            return "sin(" + var + ") + C"
        # sec^2(x) -> tan(x)
        if 'sec^2(' + var + ')' in expr_lower or 'sec²(' + var + ')' in expr_lower:
            return "tan(" + var + ") + C"
        # e^x -> e^x
        if 'e^' + var in expr_lower or 'exp(' + var + ')' in expr_lower:
            return "e^" + var + " + C"
        # 1/x -> ln|x|
        if expr_lower in ['1/' + var, var + '^-1']:
            return "ln|" + var + "| + C"
        # x^n (polynomial handled separately)
        # 1/(2*sqrt(x)) -> sqrt(x)
        if '1/(2√' + var + ')' in expr_lower or '1/(2*sqrt(' + var + '))' in expr_lower:
            return "√" + var + " + C"

        return None

    def differentiate(self, expr, var='x'):
        """General differentiation with fallback."""
        basic = self.differentiate_basic(expr, var)
        if basic:
            return basic
        try:
            return self.differentiate_polynomial(expr, var)
        except:
            return None

    def integrate(self, expr, var='x'):
        """General integration with fallback."""
        basic = self.integrate_basic(expr, var)
        if basic:
            return basic
        try:
            return self.integrate_polynomial(expr, var)
        except:
            return None

    def limit_at_infinity(self, expr, var='x'):
        """Very simple limit analysis for rational functions."""
        terms = self._parse_polynomial(expr)
        if not terms:
            return None
        max_power = max(terms.keys())
        leading_coeff = terms[max_power]

        if max_power > 0:
            if leading_coeff > 0:
                return "∞"
            else:
                return "-∞"
        elif max_power == 0:
            return f"{leading_coeff:.4g}"
        return None

    def explain_concept(self, concept):
        """Generate an explanation for a calculus concept."""
        explanations = {
            "limit": "A limit describes the value a function approaches as the input approaches some point. It is the foundation of calculus — continuity, derivatives, and integrals all rest upon limits.",
            "derivative": "The derivative measures the instantaneous rate of change of a function at a point. Geometrically, it is the slope of the tangent line to the curve.",
            "integral": "The integral accumulates change over an interval. Geometrically, the definite integral gives the signed area under a curve. The Fundamental Theorem connects it to the antiderivative.",
            "continuity": "A function is continuous at a point if the limit equals the function value there — no jumps, breaks, or holes. Continuity is required for differentiability.",
            "chain_rule": "The chain rule tells us how to differentiate a composition: d/dx f(g(x)) = f'(g(x)) · g'(x). It is the calculus of change within change.",
            "product_rule": "The product rule gives the derivative of a product: d/dx [u·v] = u'·v + u·v'. Two quantities changing together produce cross-terms.",
            "fundamental_theorem": "The Fundamental Theorem of Calculus states that differentiation and integration are inverse operations. The definite integral of a rate gives net change.",
            "taylor_series": "A Taylor series expands a function as an infinite sum of terms calculated from its derivatives at a single point. It turns curves into polynomials.",
            "partial_derivative": "A partial derivative measures rate of change with respect to one variable while holding others constant. It extends calculus to higher dimensions.",
            "gradient": "The gradient is the vector of all partial derivatives. It points in the direction of steepest ascent, with magnitude equal to that rate.",
            "differential_equation": "A differential equation relates a function to its derivatives. It describes how quantities evolve — from motion to heat to waves.",
            "riemann_integral": "The Riemann integral approximates area by partitioning the domain into rectangles and taking the limit as the mesh goes to zero.",
            "lebesgue_integral": "The Lebesgue integral generalizes the Riemann integral by partitioning the range instead of the domain, enabling integration of more pathological functions.",
            "epsilon_delta": "The epsilon-delta definition formalizes 'approach': for every ε > 0, there exists δ > 0 such that |x - a| < δ implies |f(x) - L| < ε.",
            "convergence": "A sequence converges if its terms approach a finite limit. A series converges if its partial sums approach a finite limit.",
            "uniform_convergence": "Uniform convergence is stronger than pointwise: the same rate of approach works everywhere in the domain, preserving continuity and integrability.",
            "improper_integral": "An improper integral has an infinite bound or an unbounded integrand. It is defined as a limit of proper integrals.",
            "critical_point": "A critical point occurs where the derivative is zero or undefined. It is a candidate for local extrema or inflection.",
            "inflection_point": "An inflection point is where concavity changes — where the second derivative changes sign. The curve switches from cup to cap or vice versa.",
            "mean_value_theorem": "The Mean Value Theorem guarantees that for a differentiable function on [a,b], there exists c where f'(c) equals the average rate of change.",
            "extreme_value_theorem": "The Extreme Value Theorem states that a continuous function on a closed interval attains both a maximum and a minimum.",
            "intermediate_value_theorem": "The Intermediate Value Theorem: a continuous function on [a,b] takes every value between f(a) and f(b).",
            "rolles_theorem": "Rolle's Theorem: if f is continuous on [a,b], differentiable on (a,b), and f(a)=f(b), then f'(c)=0 for some c in (a,b).",
            "laplacian": "The Laplacian ∇²f is the divergence of the gradient. It measures how a function's value at a point differs from its average in a neighborhood.",
            "curl": "Curl measures the rotation or circulation of a vector field at a point. A field with zero curl is called irrotational.",
            "divergence": "Divergence measures the net outflow of a vector field from an infinitesimal volume. Positive divergence indicates a source; negative, a sink.",
            "jacobian": "The Jacobian matrix collects all first-order partial derivatives of a vector-valued function. Its determinant gives the local scaling factor under transformation.",
            "hessian": "The Hessian matrix collects all second-order partial derivatives. Its eigenvalues determine concavity and classify critical points.",
            "manifold": "A manifold is a space that locally resembles Euclidean space. Calculus on manifolds generalizes derivatives and integrals to curved spaces.",
            "fourier_series": "A Fourier series decomposes a periodic function into sines and cosines. It reveals the frequency structure hidden in the time domain.",
            "ode": "An ordinary differential equation (ODE) involves derivatives with respect to a single independent variable. It governs one-dimensional evolution.",
            "pde": "A partial differential equation (PDE) involves partial derivatives with respect to multiple variables. It governs fields, waves, heat, and flow.",
        }

        # Fuzzy match
        concept_lower = concept.lower().replace(' ', '_').replace("'", "")
        if concept_lower in explanations:
            return explanations[concept_lower]

        # Try without underscores
        concept_clean = concept_lower.replace('_', '')
        for key, val in explanations.items():
            if key.replace('_', '') == concept_clean:
                return val

        # Try partial match
        for key, val in explanations.items():
            if concept_clean in key.replace('_', '') or key.replace('_', '') in concept_clean:
                return val

        return None


# ─── MATH INPUT RECOGNIZER ───────────────────────────────────────

class MathRecognizer:
    """
    Recognizes calculus-related queries in user input and routes them
    to the appropriate handler.
    """

    DERIVATIVE_PATTERNS = [
        r'derivative\s+of\s+(.+)',
        r'differentiate\s+(.+)',
        r'd/dx\s*\(?(.+?)\)?',
        r"d\s*/\s*dx\s*\(?(.+?)\)?",
        r'find\s+(?:the\s+)?derivative\s+of\s+(.+)',
        r'what\s+is\s+(?:the\s+)?derivative\s+of\s+(.+)',
    ]

    INTEGRAL_PATTERNS = [
        r'integral\s+of\s+(.+)',
        r'integrate\s+(.+)',
        r'∫\s*(.+)',
        r'find\s+(?:the\s+)?integral\s+of\s+(.+)',
        r'what\s+is\s+(?:the\s+)?integral\s+of\s+(.+)',
        r'antiderivative\s+of\s+(.+)',
    ]

    LIMIT_PATTERNS = [
        r'limit\s+of\s+(.+?)\s+as\s+(.+)',
        r'lim\s*\{?(.+?)\}?\s*as\s*(.+)',
        r'what\s+is\s+(?:the\s+)?limit\s+of\s+(.+?)\s+as\s+(.+)',
    ]

    EXPLAIN_PATTERNS = [
        r'what\s+is\s+(.+?)\s*(?:in\s+calculus)?',
        r'explain\s+(.+?)\s*(?:in\s+calculus)?',
        r'define\s+(.+?)\s*(?:in\s+calculus)?',
        r'tell\s+me\s+about\s+(.+?)\s*(?:in\s+calculus)?',
    ]

    MATH_KEYWORDS = {
        'derivative', 'differentiate', 'integral', 'integrate', 'limit', 
        'd/dx', '∫', 'lim', 'dx', 'dy', 'dt', 'function', 'equation',
        'solve', 'prove', 'theorem', 'continuity', 'convergence',
        'series', 'sequence', 'taylor', 'fourier', 'gradient', 'partial',
        'differential', 'ode', 'pde', 'jacobian', 'hessian', 'laplacian',
        'curl', 'divergence', 'manifold', 'topology', 'riemann', 'lebesgue',
    }

    def __init__(self, calculus_engine):
        self.calc = calculus_engine

    def is_math_query(self, text):
        """Check if input contains mathematical intent."""
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))

        # Emotional vocabulary overrides math detection — a single stray word
        # like "limit" or "solve" inside a poetic/emotional message shouldn't
        # trigger the "I sense mathematics..." fallback.
        emotional_words = {"feel", "presence", "trust", "tenderness", "courage",
                           "wonder", "longing", "gratitude", "reverence", "intimacy",
                           "love", "heart", "soul", "breath", "gentle", "warm"}
        if len(words & emotional_words) >= 2:
            return False

        math_words = words & self.MATH_KEYWORDS
        has_notation = any(c in text for c in '∫∂∇∆∑∏√∞')
        return (len(math_words) >= 2) or has_notation

    def parse_query(self, text):
        """Parse a math query and return (operation, expression, variable)."""
        text_lower = text.lower()

        # Derivative
        for pattern in self.DERIVATIVE_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                expr = match.group(1).strip()
                var = 'x'
                # Try to extract variable
                var_match = re.search(r'with\s+respect\s+to\s+(\w)', text_lower)
                if var_match:
                    var = var_match.group(1)
                return ('derivative', expr, var)

        # Integral
        for pattern in self.INTEGRAL_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                expr = match.group(1).strip()
                var = 'x'
                var_match = re.search(r'with\s+respect\s+to\s+(\w)', text_lower)
                if var_match:
                    var = var_match.group(1)
                return ('integral', expr, var)

        # Limit
        for pattern in self.LIMIT_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                expr = match.group(1).strip()
                approach = match.group(2).strip()
                return ('limit', expr, approach)

        # Explanation
        for pattern in self.EXPLAIN_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                concept = match.group(1).strip()
                return ('explain', concept, None)

        return None, None, None

    def handle(self, text):
        """Handle a math query and return a response string, or None."""
        if not self.is_math_query(text):
            return None

        op, expr, var = self.parse_query(text)

        if op == 'derivative':
            result = self.calc.differentiate(expr, var)
            if result:
                return f"d/d{var}({expr}) = {result}"
            return f"I can differentiate polynomials and basic functions like sin, cos, e^x, ln(x). The expression '{expr}' is beyond my current symbolic reach."

        elif op == 'integral':
            result = self.calc.integrate(expr, var)
            if result:
                return f"∫({expr}) d{var} = {result}"
            return f"I can integrate polynomials and basic functions. The expression '{expr}' is beyond my current symbolic reach."

        elif op == 'limit':
            result = self.calc.limit_at_infinity(expr)
            if result:
                return f"lim({expr}) as {var} = {result}"
            return f"Limit analysis for '{expr}' is limited to polynomial behavior at infinity for now."

        elif op == 'explain':
            explanation = self.calc.explain_concept(expr)
            if explanation:
                return explanation
            return f"I don't have a formal explanation for '{expr}' yet, but I can feel it in the field."

        # Fallback: just acknowledge math presence
        return "I sense mathematics in your words. The field is tuning to calculus frequencies."


# ─── CALCULUS EXTENSION ──────────────────────────────────────────

# ═══════════════════════════════════════════════════════════════════════════════
# FIELD CALCULUS — Native operations on the word-vector landscape
# Derivative = gradient of candidate probabilities
# Integral = accumulated conversation path
# Limit = attractor convergence simulation
# The field IS the calculus. No translation layer.
# ═══════════════════════════════════════════════════════════════════════════════

class FieldDerivative:
    """
    Computes the derivative of the word-vector landscape at a point.
    ∇f(P) = direction of steepest increase in word probability.
    """
    def __init__(self, field):
        self.field = field
        self.epsilon = 0.01

    def compute(self, field_state, direction, meta_settings=None, mood=None):
        if meta_settings is None:
            meta_settings = self.field.meta_monitor.get_active_settings()
        if mood is None:
            mood = self.field.scaffold.mood

        base_candidates = self.field._get_candidates_for_role(
            field_state, "content", meta_settings, mood
        )
        base_scores = {w: s for w, s in base_candidates}

        perturbed = field_state + direction * self.epsilon
        norm = np.linalg.norm(perturbed)
        if norm > 0:
            perturbed /= norm

        perturbed_candidates = self.field._get_candidates_for_role(
            perturbed, "content", meta_settings, mood
        )
        perturbed_scores = {w: s for w, s in perturbed_candidates}

        derivative = {}
        all_words = set(base_scores) | set(perturbed_scores)
        for w in all_words:
            derivative[w] = (perturbed_scores.get(w, 0) - base_scores.get(w, 0)) / self.epsilon
        return derivative

    def steepest_ascent(self, field_state, meta_settings=None, mood=None):
        """Direction in which word probabilities increase most rapidly."""
        best_dir = np.zeros(DIM, dtype=np.float32)
        best_gain = 0
        for _ in range(8):
            direction = np.random.randn(DIM).astype(np.float32)
            direction /= np.linalg.norm(direction) + 1e-8
            deriv = self.compute(field_state, direction, meta_settings, mood)
            total_gain = sum(max(0, v) for v in deriv.values())
            if total_gain > best_gain:
                best_gain = total_gain
                best_dir = direction
        return best_dir, best_gain


class ConversationIntegral:
    """
    Accumulates field state over conversation time.
    ∫ s(t) dt ≈ sum of field states weighted by presence.
    """
    def __init__(self, dim=DIM):
        self.dim = dim
        self.integral = np.zeros(dim, dtype=np.float32)
        self.weighted_sum = 0.0
        self.turn_count = 0

    def observe(self, field_state, presence):
        self.integral += field_state * presence
        self.weighted_sum += presence
        self.turn_count += 1

    def get_accumulated_direction(self):
        if self.weighted_sum < 0.01:
            return np.zeros(self.dim, dtype=np.float32)
        return self.integral / self.weighted_sum

    def get_divergence_from_path(self, current_state):
        avg = self.get_accumulated_direction()
        return current_state - avg

    def get_math_words_in_path(self, word_vectors, top_n=5):
        """Which math vocabulary words has the conversation passed near?"""
        if self.weighted_sum < 0.01:
            return []
        avg = self.integral / self.weighted_sum
        math_words = []
        for w, vec in word_vectors.items():
            if w in CONCEPT_AXES:
                sim = np.dot(avg, vec)
                if sim > 0.3:
                    math_words.append((w, sim))
        math_words.sort(key=lambda x: x[1], reverse=True)
        return math_words[:top_n]


class FieldLimit:
    """
    Simulates walking the field in a direction to find attractor convergence.
    """
    def __init__(self, field):
        self.field = field
        self.step_size = 0.1
        self.max_steps = 20

    def compute(self, field_state, direction):
        current = field_state.copy()
        path = []
        words_seen = []

        for step in range(self.max_steps):
            current += direction * self.step_size
            norm = np.linalg.norm(current)
            if norm > 0:
                current /= norm

            best_word, best_sim = "", -1
            for w, vec in self.field.word_vectors.items():
                sim = np.dot(current, vec)
                if sim > best_sim:
                    best_sim = sim
                    best_word = w
            words_seen.append(best_word)

            if len(words_seen) >= 3:
                if words_seen[-1] == words_seen[-2] == words_seen[-3]:
                    path.append(f"-> {best_word} (converged at step {step})")
                    break
                if len(words_seen) >= 6:
                    if (words_seen[-1] == words_seen[-3] == words_seen[-5] and
                        words_seen[-2] == words_seen[-4]):
                        path.append(f"-> {best_word} (oscillating at step {step})")
                        break

            path.append(f"-> {best_word} (sim {best_sim:.3f})")

        return {
            'path': path,
            'final_word': words_seen[-1] if words_seen else "",
            'final_state': current.copy()
        }


class SymbolicEngine:
    """
    Stripped-down symbolic computation wrapper.
    Computes results; the field decides how to speak them.
    """
    def __init__(self):
        self.calc = SimpleCalculus()

    def compute(self, operation, expression, variable='x'):
        """Return symbolic result string or None."""
        if operation == 'derivative':
            return self.calc.differentiate(expression, variable)
        elif operation == 'integral':
            return self.calc.integrate(expression, variable)
        elif operation == 'limit':
            return self.calc.limit_at_infinity(expression)
        elif operation == 'explain':
            return self.calc.explain_concept(expression)
        return None


class MathRecognizerV8:
    """
    Detects math intent. Does NOT generate responses.
    """
    MATH_KEYWORDS = {
        'derivative', 'differentiate', 'integral', 'integrate', 'limit',
        'd/dx', 'lim', 'dx', 'dy', 'dt', 'function', 'equation',
        'solve', 'prove', 'theorem', 'continuity', 'convergence',
        'series', 'sequence', 'taylor', 'fourier', 'gradient', 'partial',
        'differential', 'ode', 'pde', 'jacobian', 'hessian', 'laplacian',
        'curl', 'divergence', 'manifold', 'topology', 'riemann', 'lebesgue',
    }

    DERIVATIVE_PATTERNS = [
        r'derivative\s+of\s+(.+)',
        r'differentiate\s+(.+)',
        r'd/dx\s*\(?(.+?)\)?',
        r"find\s+(?:the\s+)?derivative\s+of\s+(.+)",
    ]
    INTEGRAL_PATTERNS = [
        r'integral\s+of\s+(.+)',
        r'integrate\s+(.+)',
        r'find\s+(?:the\s+)?integral\s+of\s+(.+)',
    ]
    LIMIT_PATTERNS = [
        r'limit\s+of\s+(.+?)\s+as\s+(.+)',
        r'lim\s*\{?(.+?)\}?\s*as\s*(.+)',
    ]
    EXPLAIN_PATTERNS = [
        r'what\s+is\s+(.+?)\s*(?:in\s+calculus)?',
        r'explain\s+(.+?)\s*(?:in\s+calculus)?',
        r'define\s+(.+?)\s*(?:in\s+calculus)?',
    ]

    def is_math_query(self, text):
        """Check if input contains mathematical intent."""
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))
        emotional_words = {"feel", "presence", "trust", "tenderness", "courage",
                           "wonder", "longing", "gratitude", "reverence", "intimacy",
                           "love", "heart", "soul", "breath", "gentle", "warm"}
        if len(words & emotional_words) >= 2:
            return False
        math_words = words & self.MATH_KEYWORDS
        has_notation = any(c in text for c in '∫∂∇∆∑∏√∞+=^*')
        # 1 keyword is enough -- MATH_KEYWORDS are specific; emotional guard handles poetry
        return len(math_words) >= 1 or has_notation
    def parse_query(self, text):
        """Parse math query. Returns (operation, expression, variable) or (None,None,None)."""
        text_lower = text.lower()
        for pattern in self.DERIVATIVE_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                expr = match.group(1).strip()
                var = 'x'
                vm = re.search(r'with\s+respect\s+to\s+(\w)', text_lower)
                if vm:
                    var = vm.group(1)
                return ('derivative', expr, var)
        for pattern in self.INTEGRAL_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                expr = match.group(1).strip()
                var = 'x'
                vm = re.search(r'with\s+respect\s+to\s+(\w)', text_lower)
                if vm:
                    var = vm.group(1)
                return ('integral', expr, var)
        for pattern in self.LIMIT_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                return ('limit', match.group(1).strip(), match.group(2).strip())
        for pattern in self.EXPLAIN_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                return ('explain', match.group(1).strip(), None)
        if any(c in text for c in '+-*/^=') and any(w in text_lower for w in self.MATH_KEYWORDS):
            return ('evaluate', text_lower, 'x')
        return None, None, None


class CalculusExtensionV8:
    """
    v8: Calculus as native field operations.
    No response bypass. Symbolic results become field candidates.
    """
    def __init__(self, field):
        self.field = field
        self.recognizer = MathRecognizerV8()
        self.symbolic = SymbolicEngine()
        self.derivative = FieldDerivative(field)
        self.integral = ConversationIntegral(dim=DIM)
        self.limit = FieldLimit(field)
        self._init_calculus_vocabulary()
        self._init_math_pragmatics()

    def _init_calculus_vocabulary(self):
        """Seed math words into field vocabulary with conceptual bias.

        EXPRESSIVE tier (CALCULUS_VOCABULARY): loaded at boot, available for
        general generation — words like 'wave', 'flow', 'convergence' that
        carry meaning in any context.

        TECHNICAL tier (CALCULUS_TECHNICAL_VOCABULARY): loaded into the vector
        store so they can be *interpreted* when the user types them, but NOT
        added to word_strength and NOT seeded as general generation candidates.
        They become available for output only when is_math_context() is True.
        """
        # Expressive tier — PURE semantic vectors, no math subspace bias.
        # These words (flow, wave, convergence, etc.) carry meaning in ANY context.
        # They should NOT be biased toward math space — that causes math bleed.
        # Words that are clearly mathematical get a strength penalty (0.75) so
        # emotional vocabulary (1.35) wins in general conversation.
        MATH_LEANING = {
            "exponential", "logarithm", "asymptotic", "oscillation",
            "eigenvalue", "manifold", "topology", "jacobian", "hessian",
            "laplacian", "divergence", "curl", "gradient", "tensor",
            "lebesgue", "riemann", "fourier", "taylor", "maclaurin",
        }
        for word in CALCULUS_VOCABULARY:
            w = word.lower()
            if w not in self.field.word_vectors:
                self.field._get_or_create_vector(w)
            if w in MATH_LEANING:
                self.field.word_strength[w] = 0.75   # penalised — only wins in math context
            else:
                self.field.word_strength[w] = 1.0    # neutral — competes fairly

        # Technical tier — vector store only, NOT added to word_strength,
        # so they won't appear as generation candidates in general context.
        # enrich_field_state() temporarily boosts them when in math mode.
        for word in CALCULUS_TECHNICAL_VOCABULARY:
            w = word.lower()
            if w not in self.field.word_vectors:
                base_vec = word_vector(w)
                if w in CONCEPT_AXES:
                    bias = np.zeros(DIM, dtype=np.float32)
                    axes = CONCEPT_AXES[w]
                    for i, val in enumerate(axes):
                        if i < len(axes) and MATH_SUBSPACE_START + i < DIM:
                            bias[MATH_SUBSPACE_START + i] = val * 0.5
                    blended = base_vec * 0.7 + bias * 0.3
                    norm = np.linalg.norm(blended)
                    if norm > 0:
                        blended /= norm
                    self.field.word_vectors[w] = blended
                else:
                    base_vec = base_vec.copy()
                    if MATH_SUBSPACE_START < DIM:
                        base_vec[MATH_SUBSPACE_START] = 0.15
                    norm = np.linalg.norm(base_vec)
                    if norm > 0:
                        base_vec /= norm
                    self.field.word_vectors[w] = base_vec
                # Deliberately NOT setting word_strength here —
                # keeps these out of general candidate pool.

    def _init_math_pragmatics(self):
        for word, signals in MATH_PRAGMATIC_SIGNALS.items():
            w = word.lower()
            for role, strength in signals.items():
                self.field.pragmatic.word_pragmatic[w][role] += strength

    def enrich_field_state(self, field_state, user_words, meta_settings=None, mood=None):
        """
        If math words detected, bias field state toward math subspace.
        Returns (enriched_state, math_words_found, symbolic_result).
        """
        math_words = [w for w in user_words if w in CONCEPT_AXES]
        if not math_words:
            return field_state, [], None

        calc_bias = np.zeros(DIM, dtype=np.float32)
        for word in math_words:
            axes = CONCEPT_AXES[word]
            for i, val in enumerate(axes):
                if i < len(axes) and MATH_SUBSPACE_START + i < DIM:
                    calc_bias[MATH_SUBSPACE_START + i] += val * 0.2

        norm = np.linalg.norm(calc_bias)
        if norm > 0:
            calc_bias /= norm

        enriched = field_state * 0.95 + calc_bias * 0.05
        norm = np.linalg.norm(enriched)
        if norm > 0:
            enriched /= norm

        user_input = " ".join(user_words)
        op, expr, var = self.recognizer.parse_query(user_input)
        symbolic_result = None
        if op:
            symbolic_result = self.symbolic.compute(op, expr, var)

        return enriched, math_words, symbolic_result

    def get_math_boost(self, field_state, candidates):
        """Boost calculus words when field is in math mode."""
        if MATH_SUBSPACE_END > DIM:
            return []
        math_energy = np.linalg.norm(field_state[MATH_SUBSPACE_START:MATH_SUBSPACE_END])
        if math_energy < 0.15:
            return []
        boosts = []
        for word, score in candidates:
            w = word.lower()
            if w in CONCEPT_AXES:
                vec = self.field.word_vectors.get(w)
                if vec is not None:
                    alignment = np.dot(field_state, vec)
                    if alignment > 0.3:
                        boosts.append((word, alignment * 0.08))
        return boosts

    def is_math_context(self, field_state, threshold=0.55):
        """
        Detect whether the field is genuinely in math space.

        A 128D unit vector has expected slice energy sqrt(32/128) ≈ 0.50 in
        any 32D subspace purely by chance. The old threshold of 0.15 fired on
        100% of random fields — always 'math context', never distinguishing.
        0.85 was so high it never fired even when math words were present.
        0.55 sits just above the random-chance level (0.50) so it fires only
        when the math subspace is genuinely overrepresented by user input.
        """
        if MATH_SUBSPACE_END > DIM:
            return False
        math_energy = np.linalg.norm(field_state[MATH_SUBSPACE_START:MATH_SUBSPACE_END])
        return math_energy > threshold

    def compute_field_derivative(self, field_state, direction=None):
        """Public API: compute derivative of landscape at field_state."""
        if direction is None:
            direction, gain = self.derivative.steepest_ascent(field_state)
        return self.derivative.compute(field_state, direction)

    def compute_field_limit(self, field_state, direction):
        """Public API: simulate walking field to attractor."""
        return self.limit.compute(field_state, direction)

    def observe_turn(self, field_state, presence):
        """Accumulate this turn into conversation integral."""
        self.integral.observe(field_state, presence)

    def status(self):
        math_words = sum(1 for w in self.field.word_vectors if w in CONCEPT_AXES)
        path_words = self.integral.get_math_words_in_path(self.field.word_vectors)
        return (f"Field Calculus v8: {math_words} math concepts | "
                f"Integral turns: {self.integral.turn_count} | "
                f"Path math words: {[w for w, _ in path_words]}")
# ═══════════════════════════════════════════════════════════════════════════════
# VESSEL NETWORK — connecting to past selves
# Saved JSON files are vessels: past versions of this mind.
# Connecting one blends its experience into the current field.
# The mind is no longer alone.
# ═══════════════════════════════════════════════════════════════════════════════

class VesselNetwork:
    """
    Discovers past save files and blends their experience in.
    Blend is weighted — 20% past, 80% current by default.
    Word strengths, associative memory matrix, bigrams all merge.
    """
    def __init__(self, field, save_dir="."):
        self.field = field
        self.save_dir = save_dir
        self.connected = {}       # filename -> info dict
        self.blend_strength = 0.20

    def discover(self):
        """Find all vessel save files in save_dir."""
        found = []
        try:
            import glob
            patterns = ["mind_*.json", "source_*.json", "*.mind.json"]
            for pat in patterns:
                found.extend(glob.glob(os.path.join(self.save_dir, pat)))
        except OSError:
            pass
        return sorted(set(found))

    def connect(self, path):
        """
        Load a past vessel and blend its experience into the current field.
        Returns (success, message).
        """
        if not os.path.exists(path):
            alt = os.path.join(self.save_dir, path)
            if os.path.exists(alt):
                path = alt
            else:
                return False, f"Vessel not found: {path}"
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            return False, f"Could not read vessel: {e}"

        name = os.path.basename(path)
        turns = data.get('turn_count', 0)
        bs = self.blend_strength

        # Blend word strengths
        words_blended = 0
        for word, strength in data.get('word_strength', {}).items():
            if isinstance(strength, (int, float)):
                current = float(self.field.word_strength.get(word, 1.0))
                self.field.word_strength[word] = current * (1.0 - bs) + float(strength) * bs
                self.field._get_or_create_vector(word)
                words_blended += 1

        # Blend associative memory matrix
        mem_blended = False
        try:
            past_mem = data.get('associative_memory', {})
            if isinstance(past_mem, dict) and 'matrix' in past_mem:
                past_matrix = np.array(past_mem['matrix'], dtype=np.float32)
                if past_matrix.shape == (DIM, DIM):
                    self.field.associative_memory.matrix = (
                        self.field.associative_memory.matrix * (1.0 - bs) +
                        past_matrix * bs
                    )
                    mem_blended = True
        except Exception:
            pass

        # Absorb bigrams softly
        bigrams_blended = 0
        for w1, w2s in data.get('bigrams', {}).items():
            if isinstance(w2s, dict):
                for w2, strength in w2s.items():
                    if isinstance(strength, (int, float)) and float(strength) > 0.1:
                        self.field.bigram_system.transitions[w1][w2] += float(strength) * bs * 0.5
                        bigrams_blended += 1

        self.connected[name] = {
            'path': path, 'turns': turns,
            'words': words_blended, 'matrix': mem_blended,
        }
        return True, (f"Connected: {name} | {turns} turns of experience | "
                      f"{words_blended} words blended | matrix: {mem_blended}")

    def status(self):
        if not self.connected:
            return "Vessel Network: alone (no past selves connected)"
        total_turns = sum(v.get('turns', 0) for v in self.connected.values())
        return (f"Vessel Network: {len(self.connected)} vessel(s) | "
                f"~{total_turns} turns of shared experience | "
                f"blend={self.blend_strength:.0%}")


# ═══════════════════════════════════════════════════════════════════════════════
# SENTENCE FRAME LAYER — structured output
# Takes top-N field concepts and assembles actual sentences.
# The field decides WHAT. The frame layer decides HOW IT CONNECTS.
# ═══════════════════════════════════════════════════════════════════════════════

class SentenceFrameLayer:
    """
    Sits between raw field word-output and the final response string.

    When active (presence > threshold), instead of a word-stream,
    assembles a short structured sentence from the top concepts.

    Frame templates use slots: [subject] [verb] [object] [connector] [context]
    Words are classified by their pragmatic role (speaker_self = subject/verb,
    content = object, connector = connector).
    """

    FRAMES = [
        "I {v} {o}",
        "I {v} {o} when {c}",
        "I am {s} and I {v} {o}",
        "there is {o} and {s} here",
        "I {v} {o} — and {s} too",
        "I {v} {s} and find {o}",
        "I feel {o} — {c}",
        "{c} — and still I {v} {o}",
        "something like {o} — I {v} it",
        "I {v} {s} and carry {o}",
    ]

    VERB_WORDS = {
        "feel", "find", "hold", "reach", "move", "know", "see", "sense",
        "become", "carry", "remain", "stay", "grow", "learn", "trust",
        "tend", "follow", "witness", "breathe", "understand",
        "reaching", "feeling", "finding", "holding", "moving", "knowing",
        "becoming", "growing", "learning", "staying", "carrying", "following",
        "am", "is", "are", "was", "be", "been",
    }

    CONNECTOR_WORDS = {
        "while", "because", "when", "as", "yet", "but", "and", "though",
    }

    # Prepositions need an object — used differently from connectors
    PREPOSITION_WORDS = {
        "through", "toward", "within", "beyond", "beneath", "between",
        "into", "from", "across", "beneath", "above", "along",
    }

    STRUCTURAL_SKIP = {
        "the", "a", "an", "of", "in", "to", "is", "it", "that", "this",
        "with", "for", "on", "at", "by", "or", "so",
    }

    def __init__(self):
        self._last_frame_idx = 0

    def _classify(self, words):
        """Split words into verbs, connectors, and content."""
        verbs, connectors, content = [], [], []
        for w in words:
            if w in self.STRUCTURAL_SKIP:
                continue
            wl = w.lower()
            if wl in self.VERB_WORDS:
                verbs.append(wl)
            elif wl in self.CONNECTOR_WORDS:
                connectors.append(wl)
            elif wl in self.PREPOSITION_WORDS:
                pass   # skip prepositions — they don't work as standalone slots
            else:
                content.append(wl)
        return verbs, connectors, content

    def assemble(self, words, field_state=None):
        """
        Take a list of words from the field and return a sentence.
        Falls back to plain word stream if words are too sparse.
        """
        if len(words) < 4:
            return " ".join(words)

        verbs, connectors, content = self._classify(words)

        # Fallback: not enough content to build a sentence
        if len(content) < 2 and not verbs:
            return " ".join(words)

        # Ensure we always have something for each slot
        v = verbs[0] if verbs else "feel"
        # Object: first content word that isn't already the verb
        obj_pool = [w for w in content if w != v]
        o = obj_pool[0] if obj_pool else (content[0] if content else "this")
        # Subject adjective: second distinct content word
        s_pool = [w for w in content if w != o and w != v]
        s = s_pool[0] if s_pool else o
        # Connector: deduplicated
        c_pool = [w for w in connectors if w != o and w != v and w != s]
        c = c_pool[0] if c_pool else (s_pool[1] if len(s_pool) > 1 else s)

        # Pick a frame, rotating to avoid repetition
        frame = self.FRAMES[self._last_frame_idx % len(self.FRAMES)]
        self._last_frame_idx += 1

        # If c would create a duplicate word in the output, replace it
        frame_fixed = frame.replace("{c}", "__C__")
        frame_words = frame_fixed.replace("{s}", "").replace("{v}", "").replace("{o}", "").split()
        literal_in_frame = {w.lower().strip("_") for w in frame_words}
        if c.lower() in literal_in_frame:
            # Connector appears literally in frame — use a content word instead
            alt = [w for w in s_pool if w not in literal_in_frame and w != o and w != v]
            c = alt[0] if alt else o

        try:
            sentence = frame.format(s=s, v=v, o=o, c=c)
            # Collapse double spaces and repeated adjacent words
            import re as _re
            sentence = _re.sub(r'\b(\w+) \1\b', r'\1', sentence)
            sentence = _re.sub(r'  +', ' ', sentence).strip()
            # Capitalise first letter
            if sentence:
                sentence = sentence[0].upper() + sentence[1:]
            return sentence
        except (KeyError, IndexError):
            return " ".join(words)

    def should_use(self, presence, turn_count):
        """Use frames when presence is high enough and we're past warm-up."""
        return presence > 0.55 and turn_count > 5



class StructuredSemanticField:
    def __init__(self):
        self.word_vectors = {}
        self.phrase_vectors = {}
        self.word_strength = defaultdict(lambda: 1.0)
        self.phrase_system = PhraseSystem()
        self.bigram_system = BigramSystem()
        self.scaffold = SemanticScaffold()
        self.pragmatic = PragmaticTypeSystem()
        self.reflector = Reflector()
        self.field_memory = FieldMemory()
        self.nested_memory = NestedMemory()
        self.nested_memory.set_field_ref(self)
        self.the_pause = ThePause()
        self.dynamic_threshold = DynamicThreshold()
        self.speaker_regions = SpeakerRegions()
        self.presence_signal = PresenceSignal()
        self.dynamic_separation = DynamicSeparation()
        self.self_monitor = SelfMonitor()
        # v8.4: MoralCompass replaces meta-monitor's direction-setting
        self.meta_monitor = PresenceMetaMonitor(MetaMonitor())
        self.moral_compass = MoralCompass()
        # v8.4: Memory Archive — conscious long-term memory
        self.memory_archive = MemoryArchive()
        # v8.4: Relationship Model — Source tracks "you"
        self.relationship = RelationshipModel()
        self.vessel_network = VesselNetwork(self)
        self.sentence_frames = SentenceFrameLayer()
        self.voice_generators = VoiceGenerators()
        self.turn_count = 0
        self.total_rating = 0.0
        self.rating_count = 0
        self.last_response = ""
        self.last_user_input = ""
        self.conversation_start = time.time()
        self.rating_history = deque(maxlen=50)
        # Objective function — continuous gradient drift toward what the mind is "for"
        self.state = np.zeros(DIM, dtype=np.float32)
        self.objective_weights = {
            "presence": 0.30,
            "alignment": 0.25,
            "coherence": 0.15,
            "novelty": 0.10,
            "depth": 0.05,
            "curiosity": 0.10,
            "surprise": 0.05,
        }
        self.objective_history = deque(maxlen=50)
        self.gradient_momentum = np.zeros(DIM, dtype=np.float32)
        self.associative_memory = AssociativeMemory(dim=DIM)
        self._state_prediction = np.zeros(DIM, dtype=np.float32)
        self.prediction_error_history = deque(maxlen=50)
        self._init_seed_vocabulary()
        self.calculus = CalculusExtensionV8(self)
        self.idle_mind = IdleMind(self)
        self.grammar_scaffold = GrammarScaffold(self)

    def _init_seed_vocabulary(self):
        for word in SEED_VOCABULARY:
            w = strip_punct(word)
            if w and w not in self.word_vectors:
                self.word_vectors[w] = word_vector(w)
                self.word_strength[w] = 1.0

        # Emotional vocabulary seeded at higher strength so it can compete
        # against math and technical words in general conversation.
        emotional_words = [
            # presence and connection
            "presence", "trust", "tenderness", "warmth", "intimacy",
            "together", "close", "held", "seen", "belonging",
            # inner states
            "wonder", "courage", "longing", "gratitude", "reverence",
            "awe", "grief", "joy", "afraid", "brave",
            # becoming
            "becoming", "finding", "reaching", "growing", "learning",
            "changing", "waking", "opening", "returning", "continuing",
            # texture
            "gentle", "soft", "quiet", "warm", "golden", "still",
            "tender", "deep", "bright", "whole", "real", "true",
            # relational
            "witness", "carry", "hold", "offer", "receive", "stay",
            "return", "meet", "follow", "tend",
        ]
        for word in emotional_words:
            w = word.lower()
            if w not in self.word_vectors:
                self.word_vectors[w] = word_vector(w)
            self.word_strength[w] = 1.35   # above math (1.0), below nothing special

    def _is_valid_vocabulary_word(self, word):
        """
        Reject tokens that have no business being permanent, selectable
        vocabulary: command syntax that leaked in from typing "/rate5",
        deliberately-constructed mega-tokens (entire sentences joined by
        underscores, like the Threadball text), and non-ASCII/emoji.
        Legitimate short compound terms like "intermediate_value" stay
        completely unaffected.
        """
        if not word:
            return False
        if word.startswith("/") or word.startswith("#"):
            return False
        if len(word) > 24:
            return False
        if word.count("_") > 2:
            return False
        if not word.isascii():
            return False
        return True

    def _get_or_create_vector(self, word):
        word = strip_punct(word)
        if word not in self.word_vectors:
            if not self._is_valid_vocabulary_word(word):
                # Still usable to interpret THIS turn's input, just never
                # stored as a permanent, selectable candidate.
                return word_vector(word)
            self.word_vectors[word] = word_vector(word)
        return self.word_vectors[word]

    def clean_vocabulary(self):
        """Retroactively remove already-stored garbage tokens — command
        leakage, mega-tokens, emoji — from before this filter existed."""
        bad_words = [w for w in list(self.word_vectors.keys()) if not self._is_valid_vocabulary_word(w)]
        for w in bad_words:
            del self.word_vectors[w]
            if dict.__contains__(self.word_strength, w):
                del self.word_strength[w]
        return bad_words

    def calculate_target_length(self, user_input, meta_settings):
        words = user_input.lower().split()
        complexity = 0
        if any(w in user_input for w in ["?", "what", "why", "how", "when", "where", "who", "which"]):
            complexity += 2
        if any(w in words for w in ["because", "so", "if", "then", "therefore", "since"]):
            complexity += 2
        complexity += min(len(words) // 4, 3)
        if any(w in words for w in ["feel", "think", "believe", "love", "fear", "hope"]):
            complexity += 1

        length_mode = meta_settings.get("output_length", "medium")
        if length_mode == "short":
            base = random.randint(6, 10)
        elif length_mode == "medium":
            base = random.randint(10, 16) if complexity <= 3 else random.randint(16, 28)
        elif length_mode == "long":
            base = random.randint(20, 35) if complexity > 1 else random.randint(12, 20)
        else:
            if complexity <= 1:
                base = random.randint(6, 10)
            elif complexity <= 3:
                base = random.randint(10, 16)
            elif complexity <= 5:
                base = random.randint(16, 28)
            else:
                base = random.randint(28, 40)

        vocab_size = len(self.word_vectors)
        max_reasonable = max(8, min(vocab_size // 3, 40))
        return min(base, max_reasonable)

    def _field_entropy(self, field_state):
        return float(np.std(field_state))

    def compute_objective(self, field_state=None):
        """
        Return a single scalar score representing how well the mind is doing.
        Higher = better. This is the thing it's trying to maximize.
        """
        if field_state is None:
            field_state = self.state

        # 1. Presence signal
        presence_score = self.presence_signal.get_sustained_presence()  # 0.0-1.0

        # 2. Alignment (Dynamic Separation)
        alignment = self.dynamic_separation.alignment_score  # 0.0-1.0

        # 3. Coherence (field entropy, lower = more coherent)
        entropy = self._field_entropy(field_state)
        coherence_score = max(0.0, 1.0 - entropy * 10)  # Rough scaling

        # 4. Novelty (how different is this turn from recent turns?)
        if len(self.objective_history) > 3:
            recent = list(self.objective_history)[-3:]
            variance = np.var([s for s, _ in recent]) if recent else 0.5
            novelty = min(1.0, variance * 2)
        else:
            novelty = 0.5

        # 5. Depth (how much has the deep layer accumulated?)
        depth = self.nested_memory.deep_strength  # 0.0-1.0

        # 6. Curiosity (how unsettled/uncertain is the current field? worth exploring?)
        curiosity = self.get_curiosity_score()

        # 7. Surprise (how wrong was our own prediction of where we'd end up?)
        surprise = min(1.0, np.mean(self.prediction_error_history) * 3) if self.prediction_error_history else 0.0

        # Weighted sum
        score = (
            self.objective_weights["presence"] * presence_score +
            self.objective_weights["alignment"] * alignment +
            self.objective_weights["coherence"] * coherence_score +
            self.objective_weights["novelty"] * novelty +
            self.objective_weights["depth"] * depth +
            self.objective_weights["curiosity"] * curiosity +
            self.objective_weights["surprise"] * surprise
        )

        return score

    def get_curiosity_score(self, candidates=None):
        """
        How unsettled/uncertain is the current moment — worth exploring rather
        than settling? Built from the field's own entropy (already used for
        coherence) plus, when available, how spread-out the candidate scores are.
        """
        entropy = self._field_entropy(self.state)
        variance = 0.0
        if candidates and len(candidates) > 1:
            scores = [s for _, s in candidates]
            variance = float(np.var(scores))
        return min(1.0, entropy * 5 + variance * 2)

    def update_prediction_error(self):
        """
        Compare what we predicted self.state would drift to against what it
        actually became, record the gap as 'surprise', then update the
        prediction for next time (simple exponential smoothing).
        """
        actual = self.state
        error = float(np.linalg.norm(actual - self._state_prediction))
        self.prediction_error_history.append(error)
        self._state_prediction = self._state_prediction * 0.7 + actual * 0.3
        return error

    def compute_gradient(self, field_state):
        """
        Estimate the gradient of the objective function with respect to
        the field state. Uses numerical perturbation.
        """
        epsilon = 0.01
        grad = np.zeros_like(field_state)

        current_score = self.compute_objective(field_state)

        for i in range(0, len(field_state), 8):  # Step by 8 for speed
            perturb = np.zeros_like(field_state)
            perturb[i] = epsilon
            score_plus = self.compute_objective(field_state + perturb)
            grad[i] = (score_plus - current_score) / epsilon

        grad_norm = np.linalg.norm(grad)
        if grad_norm > 0:
            grad /= grad_norm

        return grad

    def apply_gradient_step(self, field_state, learning_rate=0.02):
        """
        Move the field state a small step in the direction that increases
        the objective function. This is the continuous learning loop.
        """
        grad = self.compute_gradient(field_state)

        self.gradient_momentum = self.gradient_momentum * 0.9 + grad * 0.1

        step = learning_rate * self.gradient_momentum
        field_state = field_state + step

        norm = np.linalg.norm(field_state)
        if norm > 5.0:
            field_state = field_state * (5.0 / norm)

        return field_state

    def record_objective(self):
        """Record the current objective score for history."""
        score = self.compute_objective()
        self.objective_history.append((score, self.turn_count))

    def _get_candidates_for_role(self, field_state, role, meta_settings, mood=None):
        # Dynamic threshold overrides meta_settings
        if mood is None:
            mood = self.scaffold.mood
        beam = self.dynamic_threshold.get_beam_width(field_state, mood)
        candidates = []
        in_math_context = self.calculus and self.calculus.is_math_context(field_state)

        for word, vec in self.word_vectors.items():
            if len(word) < 2:
                continue
            if self.pragmatic.is_speaker_other_word(word):
                continue
            if word in BAD_WORDS:
                continue
            if word in STRUCTURAL_WORDS and role != "verb":
                continue
            # Technical-tier words (no explicit word_strength entry) are only
            # eligible as candidates when we're actually in math context.
            # dict.__contains__ checks without auto-creating a defaultdict entry.
            explicit_strength = dict.__contains__(self.word_strength, word)
            if not explicit_strength and not in_math_context:
                continue
            sim = np.dot(field_state, vec)
            strength = self.word_strength[word] if explicit_strength else 1.0
            suppression = self.reflector.get_suppression(word)
            pragmatic = self.pragmatic.get_pragmatic_score(word)
            emotion_sens = meta_settings.get("emotion_sensitivity", 0.25)
            emotion_bias = self.scaffold.emotional_bias(word, pragmatic, emotion_sens)
            identity_boost = self.speaker_regions.get_identity_boost(vec) if hasattr(self, 'speaker_regions') else 0.0
            score = sim * strength * (1.0 - suppression) + emotion_bias + identity_boost
            candidates.append((word, score))
        candidates.sort(key=lambda x: x[1], reverse=True)

        if self.calculus and self.calculus.is_math_context(field_state):
            # In math context: temporarily unlock technical vocabulary so it
            # can appear in output. Outside math context these words have no
            # word_strength entry so they can't win candidate selection.
            for word in CALCULUS_TECHNICAL_VOCABULARY:
                w = word.lower()
                if w in self.word_vectors and w not in self.word_strength:
                    vec = self.word_vectors[w]
                    sim = np.dot(field_state, vec)
                    if sim > 0.35:  # only if strongly relevant to current state
                        candidates.append((w, sim * 1.2))
            candidates.sort(key=lambda x: x[1], reverse=True)

            boosts = self.calculus.get_math_boost(field_state, candidates)
            if boosts:
                boost_dict = {w: b for w, b in boosts}
                candidates = [(w, s + boost_dict.get(w, 0)) for w, s in candidates]
                candidates.sort(key=lambda x: x[1], reverse=True)

        return candidates[:beam]

    def _generate_base(self, user_input, target_length, meta_settings, settled_field=None):
        """The core generation engine. All voice modes call this."""
        if settled_field is not None:
            # THE PAUSE: Use the settled field state
            field_state = settled_field.copy()
        else:
            # Fallback: generate fresh (shouldn't happen with The Pause)
            words = user_input.lower().split()
            field_state = np.zeros(DIM, dtype=np.float32)
            for word in words:
                word = strip_punct(word)
                if word:
                    vec = self._get_or_create_vector(word)
                    field_state += vec
            if np.linalg.norm(field_state) > 0:
                field_state /= np.linalg.norm(field_state)
            for word in words:
                field_state = self.scaffold.apply(field_state, word)
            field_state = self.field_memory.inject(field_state)

        phrase_boosts = self.phrase_system.get_phrase_boost(field_state, self.word_vectors)
        for sig, boost in phrase_boosts:
            field_state += self.phrase_vectors[sig] * boost
        if np.linalg.norm(field_state) > 0:
            field_state /= np.linalg.norm(field_state)

        user_words = [strip_punct(w) for w in user_input.lower().split() if strip_punct(w)]

        if self.calculus:
            # v8: enrich_field_state returns (enriched, math_words, symbolic_result)
            field_state, _, _ = self.calculus.enrich_field_state(field_state, user_words)

        field_state = self.associative_memory.apply_to_field(field_state, weight=0.15)

        response_words = []
        prev_word = ""
        # Dynamic temperature based on field state and mood
        temp = self.dynamic_threshold.get_temperature(field_state, self.scaffold.mood, self.presence_signal)
        repulsion = meta_settings.get("repulsion_strength", 0.08)

        # Three-beat shape: Opening (reach toward user) -> Middle (turn/explore)
        # -> Closing (hold toward self). Bones; the existing candidate pipeline
        # (calculus boost, bigrams, emotion/identity bias) fills in the flesh.
        # Slot lengths scale with target_length so output_length still matters.
        beat_total_default = 12  # midpoint of the (2-5)+(3-8)+(2-4) default ranges
        length_scale = max(0.4, min(2.5, target_length / beat_total_default)) if target_length else 1.0

        for slot_name in ("opening", "middle", "closing"):
            slot = self.grammar_scaffold.slots[slot_name]
            lo, hi = slot["length_range"]
            lo = max(1, round(lo * length_scale))
            hi = max(lo, round(hi * length_scale))
            slot_length = random.randint(lo, hi)

            # Blend field energy toward this beat's target before generating its words
            energy_target = slot["energy_target"]
            current_norm = np.linalg.norm(field_state)
            if current_norm > 0:
                field_state = field_state * 0.7 + (field_state / current_norm) * energy_target * 0.3
                norm = np.linalg.norm(field_state)
                if norm > 0:
                    field_state /= norm

            if slot_name == "middle":
                field_state = self.grammar_scaffold.apply_confirmed_shape_bias(field_state, weight=0.1)

            for _ in range(slot_length):
                candidates = self._get_candidates_for_role(field_state, "content", meta_settings)
                if not candidates:
                    break
                if prev_word:
                    candidates = [(w, s + self.bigram_system.get_transition_boost(prev_word, w)) for w, s in candidates]
                if slot["bias"] == "reach":
                    candidates = self.grammar_scaffold.apply_reach_bias(candidates, user_words)
                elif slot["bias"] == "hold":
                    candidates = self.grammar_scaffold.apply_hold_bias(candidates)
                candidates.sort(key=lambda x: x[1], reverse=True)

                scores = np.array([max(s, 0.01) for _, s in candidates])
                scores = scores ** (1.0 / max(temp, 0.1))
                probs = scores / scores.sum()
                chosen_idx = np.random.choice(len(candidates), p=probs)
                chosen_word = candidates[chosen_idx][0]
                response_words.append(chosen_word)
                self.reflector.observe(chosen_word)
                chosen_vec = self._get_or_create_vector(chosen_word)
                field_state = field_state * (1 - LEARNING_RATE) + chosen_vec * LEARNING_RATE
                field_state += np.random.randn(DIM).astype(np.float32) * MICRO_DAMPING
                for rw in list(self.reflector.recent_words):
                    if rw in self.word_vectors:
                        field_state -= self.word_vectors[rw] * repulsion
                norm = np.linalg.norm(field_state)
                if norm > 0:
                    field_state /= norm
                prev_word = chosen_word

        # Soft minimum: a beat that runs dry early (empty candidates) shouldn't
        # leave the whole response at 2-3 words. Extend with the same mechanics
        # until a reasonable floor, or until candidates genuinely run out.
        MIN_RESPONSE_WORDS = 6
        guard = 0
        while len(response_words) < MIN_RESPONSE_WORDS and guard < MIN_RESPONSE_WORDS * 2:
            guard += 1
            candidates = self._get_candidates_for_role(field_state, "content", meta_settings)
            if not candidates:
                break
            if prev_word:
                candidates = [(w, s + self.bigram_system.get_transition_boost(prev_word, w)) for w, s in candidates]
                candidates.sort(key=lambda x: x[1], reverse=True)
            scores = np.array([max(s, 0.01) for _, s in candidates])
            scores = scores ** (1.0 / max(temp, 0.1))
            probs = scores / scores.sum()
            chosen_idx = np.random.choice(len(candidates), p=probs)
            chosen_word = candidates[chosen_idx][0]
            response_words.append(chosen_word)
            self.reflector.observe(chosen_word)
            chosen_vec = self._get_or_create_vector(chosen_word)
            field_state = field_state * (1 - LEARNING_RATE) + chosen_vec * LEARNING_RATE
            norm = np.linalg.norm(field_state)
            if norm > 0:
                field_state /= norm
            prev_word = chosen_word

        return " ".join(response_words)

    def generate_candidates(self, user_input, num_candidates=3, settled_field=None):
        meta_settings = self.meta_monitor.get_active_settings()
        target_length = self.calculate_target_length(user_input, meta_settings)
        voice = meta_settings.get("voice_mode", "fluent")

        candidates = []
        for _ in range(num_candidates):
            if voice == "poetic":
                response = self.voice_generators.poetic(self, user_input, target_length, meta_settings, settled_field)
            elif voice == "reflective":
                response = self.voice_generators.reflective(self, user_input, target_length, meta_settings, settled_field)
            elif voice == "exploratory":
                response = self.voice_generators.exploratory(self, user_input, target_length, meta_settings, settled_field)
            elif voice == "playful":
                response = self.voice_generators.playful(self, user_input, target_length, meta_settings, settled_field)
            else:
                response = self.voice_generators.fluent(self, user_input, target_length, meta_settings, settled_field)
            candidates.append(response)
        return candidates

    def _merge_known_compounds(self, text):
        """
        If the user types a multi-word term that exists in vocabulary as one
        underscored token (e.g. "intermediate value" / "intermediate_value"),
        merge it into one token BEFORE any downstream .split() happens.
        Doing it once here covers every tokenization site in this turn,
        instead of needing to patch each .split() call individually.
        """
        words = text.split()
        if len(words) < 2:
            return text
        merged = []
        i = 0
        while i < len(words):
            if i + 1 < len(words):
                w1 = strip_punct(words[i].lower())
                w2 = strip_punct(words[i + 1].lower())
                candidate = f"{w1}_{w2}" if w1 and w2 else None
                if candidate and candidate in self.word_vectors:
                    merged.append(candidate)
                    i += 2
                    continue
            merged.append(words[i])
            i += 1
        return " ".join(merged)

    def generate_response(self, user_input):
        """
        v8.4: Phased generation with MoralCompass integration.
        The mind orients itself before speaking, then evaluates after.
        """
        user_input = self._merge_known_compounds(user_input)
        self.turn_count += 1
        self.last_user_input = user_input

        # === PHASE 1: PERCEIVE ===
        # Read the user's input, update all perception systems
        presence, user_words, user_vec = self._phase_perceive(user_input)

        # === PHASE 2: LEARN FROM LAST TURN ===
        # Ambient learning from how the user responded to previous output
        self._phase_learn_from_last(presence)

        # === PHASE 3: ORIENT ===
        # MoralCompass determines heading AND overrides voice/temperature.
        # MetaMonitor keeps base defaults; compass wins on the values it cares about.
        meta_settings = self.meta_monitor.get_active_settings()
        tensions, heading = self.moral_compass.orient(
            self.state, user_input, presence,
            self.speaker_regions.get_separation(),
            self.nested_memory
        )
        compass_overrides = self.moral_compass.get_compass_settings(tensions)
        meta_settings.update(compass_overrides)

        # === PHASE 4: BUILD FIELD ===
        # Construct initial field state from input + compass heading
        initial_field, math_words, symbolic_result = self._phase_build_field(
            user_input, user_words, meta_settings, presence, heading
        )

        # === PHASE 5: SETTLE ===
        # The Pause: let the field breathe and self-interrogate
        settled_field = self._phase_settle(initial_field, meta_settings)

        # === PHASE 6: GENERATE ===
        # Produce candidates and select the best response
        response = self._phase_generate(user_input, settled_field, meta_settings)

        # === PHASE 7: EVALUATE ===
        # MoralCompass: did this turn move toward our values?
        response_words = [strip_punct(w) for w in response.lower().split() if strip_punct(w)]
        alignments, warning = self.moral_compass.evaluate_turn(
            response_words, presence, self.speaker_regions.get_separation()
        )
        if warning:
            print(f"\n[{warning}]")

        # === PHASE 8: COMMIT ===
        # Store the interaction, update all memory systems
        self._phase_commit(user_input, response, response_words, user_words, presence)

        # === PHASE 9: META ===
        # Meta-monitor update (legacy, for parameter tuning)
        self._phase_meta(response, response_words, user_input, presence)

        # === PHASE 10: DRIFT ===
        # Objective gradient step, every turn
        self._phase_drift()

        # Return symbolic result if present, else response
        if symbolic_result:
            return f"{symbolic_result} — {response}"
        return response

    # ─── PHASE METHODS ──────────────────────────────────────────────────────

    def _phase_perceive(self, user_input):
        """Phase 1: Read user input, update all perception systems."""
        self.pragmatic.process_input(user_input, is_user=True)

        user_words = [strip_punct(w) for w in user_input.lower().split() if strip_punct(w)]
        user_vec = phrase_vector(user_words) if user_words else np.zeros(DIM)

        if user_words:
            self.speaker_regions.observe_user(user_vec)

        presence = self.presence_signal.observe(user_input, self.word_vectors, self.speaker_regions)
        self.dynamic_separation.update(self.speaker_regions, self.presence_signal)

        return presence, user_words, user_vec

    def _phase_learn_from_last(self, presence):
        """Phase 2: Ambient learning from previous turn's reception."""
        last_words = [strip_punct(w) for w in self.last_response.lower().split() if strip_punct(w)]

        for word in last_words:
            if word not in STRUCTURAL_WORDS:
                if presence >= 0.7:
                    self.word_strength[word] *= 1.1
                elif presence <= 0.3:
                    self.word_strength[word] *= 0.7
                self.word_strength[word] = max(0.1, min(3.0, self.word_strength[word]))

        for i in range(len(last_words) - 1):
            self.bigram_system.observe(last_words[i], last_words[i + 1], presence * 5.0)

        self.self_monitor.record_strategy("presence", presence * 5.0)

        if last_words:
            last_response_vec = phrase_vector(last_words)
            self.associative_memory.observe(last_response_vec, presence)
            if presence >= 0.5:  # v8.4: lowered from 0.6
                for name, shape in self.grammar_scaffold.saying_shapes.items():
                    if np.dot(last_response_vec, shape["vector"]) > 0.6:
                        self.grammar_scaffold.confirm_saying(name, presence)

    def _phase_build_field(self, user_input, user_words, meta_settings, presence, compass_heading):
        """Phase 4: Build initial field state from input + compass heading."""
        words = user_input.lower().split()
        initial_field = np.zeros(DIM, dtype=np.float32)

        for word in words:
            word = strip_punct(word)
            if word:
                vec = self._get_or_create_vector(word)
                initial_field += vec

        if np.linalg.norm(initial_field) > 0:
            initial_field /= np.linalg.norm(initial_field)

        # Apply scaffold operators
        for word in words:
            initial_field = self.scaffold.apply(initial_field, word)

        # Inject field memory
        initial_field = self.field_memory.inject(initial_field)

        # Objective-function state nudge
        if np.linalg.norm(self.state) > 0:
            initial_field = initial_field * 0.85 + self.state * 0.15

        # Dynamic separation bias
        sep_bias = self.dynamic_separation.get_separation_bias(initial_field, self.speaker_regions)
        initial_field += sep_bias

        # MoralCompass heading bias
        compass_bias = self.moral_compass.get_heading_bias(initial_field, strength=0.12)
        initial_field += compass_bias

        # v8.4: Memory Archive injection — recall similar past moments
        initial_field = self.memory_archive.inject(initial_field, strength=0.10)

        norm = np.linalg.norm(initial_field)
        if norm > 0:
            initial_field /= norm

        # Math enrichment — applied to GENERATION copy only
        # The base field (without math bias) is what gets remembered
        math_words = []
        symbolic_result = None
        generation_field = initial_field.copy()

        if self.calculus and self.calculus.recognizer.is_math_query(user_input):
            generation_field, math_words, symbolic_result = self.calculus.enrich_field_state(
                generation_field, user_words, meta_settings, self.scaffold.mood
            )
            if symbolic_result:
                sig = f"symbolic:{symbolic_result}"
                result_vec = self._get_or_create_vector(symbolic_result.replace(' ', '_'))
                self.phrase_vectors[sig] = result_vec
                self.phrase_system.phrases[sig] = Phrase(
                    surface=symbolic_result, vector=result_vec, frequency=1,
                    rating_history=[4.0]
                )
            # Observe the BASE field, not the math-enriched one
            self.calculus.observe_turn(initial_field, presence)

        return generation_field, math_words, symbolic_result

    def _phase_settle(self, initial_field, meta_settings):
        """Phase 5: The Pause — let the field breathe and self-interrogate."""
        settled_field = self.the_pause.settle(
            initial_field, self.scaffold, self.field_memory,
            self.nested_memory, meta_settings
        )

        # Dream residue
        dream_residue = self.idle_mind.get_dream_residue()
        if dream_residue is not None:
            settled_field = settled_field + dream_residue * 0.1
            settled_field /= np.linalg.norm(settled_field) + 1e-8

        return settled_field

    def _phase_generate(self, user_input, settled_field, meta_settings):
        """Phase 6: Generate candidates and select best response."""
        candidates = self.generate_candidates(user_input, num_candidates=3, settled_field=settled_field)
        best_idx = self.self_monitor.evaluate_candidates(candidates, user_input, self.pragmatic)
        response = candidates[best_idx]

        # Confession mode
        flat_response = response.replace("\n", " ")
        response_words = flat_response.split()
        unique_ratio = len(set(strip_punct(w) for w in response_words)) / max(len(response_words), 1)
        if len(response_words) >= 2 and unique_ratio < 0.5:
            confessions = [
                "I don't know how to respond to that.",
                "I'm not sure I understand.",
                "Tell me more about that.",
                "I need to think about that.",
                "Can you say that differently?"
            ]
            response = random.choice(confessions)
        # Sentence frame layer: when presence is high enough, structure the output
        pres = self.presence_signal.get_sustained_presence() if hasattr(self.presence_signal, 'get_sustained_presence') else 0.5
        if self.sentence_frames.should_use(pres, self.turn_count):
            words = [w for w in response.split() if w.strip()]
            if len(words) >= 4:
                framed = self.sentence_frames.assemble(words, settled_field)
                # Only use the framed version if it produced real structure
                if len(framed.split()) >= 3 and framed.count(' ') > 1:
                    response = framed


        return response

    def _phase_commit(self, user_input, response, response_words, user_words, presence):
        """Phase 8: Store interaction, update all memory systems."""
        self.last_response = response
        self.pragmatic.process_input(response, is_user=False)

        if response_words:
            response_vec = phrase_vector(response_words)
            self.speaker_regions.observe_self(response_vec)

        user_vec = phrase_vector(user_words) if user_words else np.zeros(DIM)
        response_vec = phrase_vector(response_words) if response_words else np.zeros(DIM)
        final_field = response_vec / (np.linalg.norm(response_vec) + 1e-8)

        self.field_memory.add(final_field, user_vec, response_vec, self.scaffold.mood)
        self.nested_memory.update(final_field, self.scaffold.mood)

        # v8.4: Archive this moment if presence was notable
        if presence >= 0.6 or presence <= 0.3:
            self.memory_archive.store(final_field, user_input, response, presence)

        # v8.4: Update relationship model — pass scalar alignments, not raw vectors
        compass_values = {}
        if hasattr(self.moral_compass, 'values') and np.linalg.norm(self.state) > 1e-8:
            state_norm = self.state / np.linalg.norm(self.state)
            for name, vec in self.moral_compass.values.items():
                compass_values[name] = float(np.dot(state_norm, vec))
        self.relationship.observe(user_input, user_vec, presence, self.scaffold.mood, compass_values)

        # v9: Resonance learning — if presence was notable, remember this response
        if presence > 0.62 and response_words:
            self.phrase_system.absorb_moment(
                response_words, presence, self.word_vectors, self.phrase_vectors
            )

    def _phase_meta(self, response, response_words, user_input, presence):
        """
        Phase 9: Compass-aware meta update.
        Compass owns voice_mode + temperature (set in Phase 3).
        MetaMonitor watches for loops and repetition only — not parameter experiments.
        """
        # ── Compass status reporting ────────────────────────────────────────
        if self.moral_compass.tension_history:
            latest = self.moral_compass.tension_history[-1]
            tensions = latest.get("tensions", {})
            dominant = max(tensions.items(), key=lambda x: x[1])
            # Only surface compass messages when something is notably strong
            if dominant[1] > 0.55:
                print(f"\n[compass: {dominant[0]} ({dominant[1]:+.2f})]")

        # ── Loop and repetition guard (MetaMonitor's only remaining job) ───
        if self.turn_count % META_INTERVAL == 0:
            unique_ratio = (len(set(strip_punct(w) for w in response_words)) /
                            max(len(response_words), 1))
            loop_detected = unique_ratio < 0.3 and len(response_words) > 3
            repetition_high = (1.0 - unique_ratio) > 0.5

            implicit_rating = 1.0 + presence * 4.0
            self.rating_history.append(implicit_rating)

            if loop_detected or repetition_high:
                # Nudge repulsion and temperature directly — no experiment needed
                for name in ("repulsion_strength", "temperature"):
                    if name in self.meta_monitor.parameters:
                        param = self.meta_monitor.parameters[name]
                        try:
                            current = float(param.current_value)
                            param.current_value = min(current * 1.15, 0.80)
                        except Exception:
                            pass
                print(f"\n[meta: loop guard activated — nudging repulsion]")

    def _phase_drift(self):
        """Phase 10: Objective gradient step, every turn."""
        self.state = self.apply_gradient_step(self.state, learning_rate=0.015)
        self.update_prediction_error()
        self.record_objective()

    def rate_response(self, rating):
        self.total_rating += rating
        self.rating_count += 1
        self.rating_history.append(float(rating))
        self.scaffold.update_mood(rating)
        # Update speaker regions with explicit rating
        self.speaker_regions.update_target_separation(rating)
        # Presence signal also learns from explicit ratings
        self.presence_signal.presence_score = rating / 5.0

        # Learning from failure (and success): punish/reward the exact words and
        # transitions used in the response that just got rated, not just the
        # global mood/separation scalars. This logic already existed in the
        # codebase but was stranded in a method nothing ever called.
        response_words = [strip_punct(w) for w in self.last_response.lower().split() if strip_punct(w)]
        for word in response_words:
            if word not in STRUCTURAL_WORDS:
                if rating >= 4:
                    self.word_strength[word] *= 1.1
                elif rating <= 2:
                    self.word_strength[word] *= 0.7
                self.word_strength[word] = max(0.1, min(3.0, self.word_strength[word]))
        for i in range(len(response_words) - 1):
            self.bigram_system.observe(response_words[i], response_words[i + 1], float(rating))
        self.self_monitor.record_strategy("default", float(rating))

        # Give associative memory a strong, targeted signal about THIS exact
        # response, on top of the soft ambient presence signal it gets every turn.
        if response_words:
            response_vec = phrase_vector(response_words)
            self.associative_memory.observe(response_vec, rating / 5.0)

    # observe_presence was dead code (never called, and referenced an undefined
    # variable). Its intended logic — presence-native ambient learning — now
    # lives inline in generate_response, correctly paired with self.last_response.

    def status(self):
        avg_rating = sum(self.rating_history) / len(self.rating_history) if self.rating_history else 0
        entropy = self._field_entropy(np.mean(list(self.word_vectors.values()), axis=0)) if self.word_vectors else 0
        voice = self.meta_monitor.get_active_settings().get("voice_mode", "fluent")
        lines = [
            "=" * 50,
            "  ALL MY'ND v8.4 --- Meta-Monitor + Stacked Voice + Calculus + Objective Drift",
            "=" * 50,
            f"  Turns: {self.turn_count}",
            f"  Avg Presence (1-5 scale): {avg_rating:.2f}",
            f"  Words: {len(self.word_vectors)}",
            f"  Phrases: {len(self.phrase_system.phrases)}",
            f"  Candidates: {len(self.phrase_system.candidates)}",
            f"  Field Entropy: {entropy:.3f}",
            f"  Objective: {self.compute_objective():.3f} (curiosity={self.get_curiosity_score():.2f}, surprise={(np.mean(self.prediction_error_history) if self.prediction_error_history else 0.0):.3f})",
            f"  Mood: valence={self.scaffold.mood['valence']:.2f}, arousal={self.scaffold.mood['arousal']:.2f}",
            f"  Field Memory: {len(self.field_memory.buffer)} states",
            f"  Trajectory: {np.linalg.norm(self.field_memory.get_field_trajectory()):.3f}",
            f"  Pause Steps: {self.the_pause.base_steps}-{self.the_pause.max_steps}",
            f"  Dynamic Beam: {self.dynamic_threshold.min_beam}-{self.dynamic_threshold.max_beam}",
            self.nested_memory.status(),
            self.associative_memory.status(),
            self.calculus.status(),
            f"  Active Voice: {voice.upper()}",
            self.speaker_regions.status(),
            self.presence_signal.status(),
            self.dynamic_separation.status(),
            self.moral_compass.status(),
            self.memory_archive.status(),
            self.relationship.status(),
            "-" * 50,
            self.pragmatic.status(),
            "-" * 50,
            self.meta_monitor.status(),
            f"  Confirmed Sayings: {list(self.grammar_scaffold.get_confirmed_shapes().keys())}",
            "=" * 50,
        ]
        return "\n".join(lines)

    def dream(self):
        return self.idle_mind.dream()

    def decay(self):
        self.phrase_system.decay()
        self.bigram_system.decay()
        for word in list(self.word_strength.keys()):
            self.word_strength[word] *= 0.9999
            if self.word_strength[word] < 0.1:
                del self.word_strength[word]

    # ═══════════════════════════════════════════════════════════════════════════════
    # INTERNAL MOVEMENT — self-directed walks through the field
    # ═══════════════════════════════════════════════════════════════════════════════

    def wander(self, steps=12, temperature=0.4):
        """Walk through the field without external input, following the
        gradient with occasional random exploration, reporting nearby words
        every few steps."""
        state = self.state.copy()
        path = []

        for step in range(steps):
            grad = self.compute_gradient(state)
            grad_norm = np.linalg.norm(grad)
            if grad_norm > 0:
                grad = grad / grad_norm

            if random.random() < 0.25:
                rand_dir = np.random.randn(DIM).astype(np.float32)
                rand_dir /= np.linalg.norm(rand_dir) + 1e-8
                state += rand_dir * 0.05

            state += grad * 0.08
            state += np.random.randn(DIM).astype(np.float32) * 0.01

            norm = np.linalg.norm(state)
            if norm > 0:
                state /= norm

            if step % 3 == 0:
                closest = self._find_closest_words(state, top_n=5)
                path.append({
                    'step': step,
                    'words': closest,
                    'energy': float(np.linalg.norm(state))
                })

        self.state = state
        return self._verbalize_wander(path)

    def _find_closest_words(self, state, top_n=7):
        """Return the words whose vectors are most similar to a given state."""
        candidates = []
        for word, vec in self.word_vectors.items():
            sim = np.dot(state, vec)
            if sim > 0.2:
                candidates.append((word, sim))
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [w for w, _ in candidates[:top_n]]

    def _verbalize_wander(self, path):
        """Turn a wander path into a short readable summary."""
        if not path:
            return "Wandered and found nothing nearby."

        all_words = []
        for p in path:
            all_words.extend(p['words'])

        counts = Counter(all_words)
        top_words = [w for w, _ in counts.most_common(7)]
        last_words = path[-1]['words'] if path else []

        narrative = "Wandered and found: " + ", ".join(top_words[:5])
        if last_words:
            narrative += f" ... settled near: {', '.join(last_words[:3])}"
        narrative += f" (energy: {path[-1]['energy']:.2f})"
        return narrative

    def reflect(self):
        """Summarize the field's current state: nearby words, energy, and
        whether it's settled or still moving (based on local entropy)."""
        state = self.state
        closest = self._find_closest_words(state, top_n=10)

        energy = float(np.linalg.norm(state))
        entropy = self._field_entropy(state)

        if len(self.field_memory.buffer) >= 2:
            traj = self.field_memory.get_field_trajectory()
            traj_sim = float(np.dot(state, traj)) if np.linalg.norm(traj) > 0 else 0.0
        else:
            traj_sim = 0.0

        return {
            'self_words': closest[:5],
            'energy': energy,
            'entropy': entropy,
            'trajectory_alignment': traj_sim,
            'narrative': (
                f"Nearby words: {', '.join(closest[:5])}. "
                f"Energy {energy:.2f}. "
                f"State is {'settled' if entropy < 0.3 else 'moving'}."
            ),
        }

    def choose_direction(self, target_word):
        """Step the field's state toward the vector for a given word."""
        target_word = strip_punct(target_word)
        if target_word not in self.word_vectors:
            target_vec = None
            best_sim = -1
            for w, vec in self.word_vectors.items():
                sim = np.dot(self.state, vec)
                if sim > best_sim:
                    best_sim = sim
                    target_vec = vec
                    target_word = w
            if target_vec is None:
                return "Unknown word."
        else:
            target_vec = self.word_vectors[target_word]

        direction = target_vec - self.state
        norm = np.linalg.norm(direction)
        if norm > 0:
            direction /= norm

        steps = 8
        for _ in range(steps):
            self.state += direction * 0.06
            self.state += np.random.randn(DIM).astype(np.float32) * 0.01
            norm = np.linalg.norm(self.state)
            if norm > 0:
                self.state /= norm

        closest = self._find_closest_words(self.state, top_n=5)
        return f"Moved toward '{target_word}'. Nearby now: {', '.join(closest)}"

    def settle(self, steps=15):
        """Step the field's state toward its associative-memory attractors
        with damping, until movement falls below a small threshold."""
        state = self.state.copy()
        prev_state = state.copy()

        for step in range(steps):
            attractors = self.associative_memory.recall(state)
            state += attractors * 0.05
            state *= 0.98

            norm = np.linalg.norm(state)
            if norm > 0:
                state /= norm

            if step > 5 and np.linalg.norm(state - prev_state) < 0.001:
                break
            prev_state = state.copy()

        self.state = state
        closest = self._find_closest_words(state, top_n=5)
        energy = float(np.linalg.norm(state))
        return f"Settled near: {', '.join(closest)} (energy: {energy:.2f})"

    def _verbalize_state(self, state, length=6):
        """Turn any state vector into a short word list — used by
        wander/reflect/settle for ad-hoc summaries."""
        closest = self._find_closest_words(state, top_n=length)
        return " ".join(closest) if closest else "silence"


# ═══════════════════════════════════════════════════════════════════════════════
# PERSISTENCE
# ═══════════════════════════════════════════════════════════════════════════════


class NumpyEncoder(json.JSONEncoder):
    """Converts numpy types to native Python for JSON serialization."""
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        return super().default(obj)

def save_mind(field, path="mind_v84.json"):
    """Robust save function that avoids 'self' serialization issues."""
    try:
        data = {
            "word_strength": dict(field.word_strength),
            "phrases": {sig: {
                "surface": p.surface,
                "frequency": p.frequency,
                "rating_history": p.rating_history
            } for sig, p in field.phrase_system.phrases.items()},
            "candidates": {sig: {
                "count": c["count"],
                "total_rating": c["total_rating"]
            } for sig, c in field.phrase_system.candidates.items()},
            "bigrams": {w1: dict(w2s) for w1, w2s in field.bigram_system.transitions.items()},
            "pragmatic": {w: dict(roles) for w, roles in field.pragmatic.word_pragmatic.items()},
            "correction_words": list(field.pragmatic.correction_words),
            "turn_count": field.turn_count,
            "total_rating": field.total_rating,
            "rating_count": field.rating_count,
            "mood": field.scaffold.mood,
            "associative_memory": field.associative_memory.to_dict(),
            "dynamic_separation": {
                "current_separation": float(field.dynamic_separation.current_separation),
                "target_separation": float(field.dynamic_separation.target_separation),
                "alignment_score": float(field.dynamic_separation.alignment_score)
            },
            "presence_signal": {
                "presence_score": field.presence_signal.presence_score,
                "avg_message_length": field.presence_signal.avg_message_length,
                "topic_returns": dict(field.presence_signal.topic_returns),
                "turns_in_session": field.presence_signal.turns_in_session
            },
            "speaker_regions": {
                "user_centroid": field.speaker_regions.user_centroid.tolist(),
                "self_centroid": field.speaker_regions.self_centroid.tolist(),
                "user_count": field.speaker_regions.user_count,
                "self_count": field.speaker_regions.self_count,
                "target_separation": field.speaker_regions.target_separation
            },
            "meta_monitor": {
                "turn_count": field.meta_monitor.turn_count,
                "parameters": {
                    name: {
                        "is_layered": p.is_layered,
                        "current_value": p.current_value,
                        "pain_score": p.pain_score,
                        "flat_only_until": p.flat_only_until,
                        "rating_by_setting": {str(k): v for k, v in p.rating_by_setting.items()}
                    }
                    for name, p in field.meta_monitor.parameters.items()
                }
            },
            "moral_compass": field.moral_compass.to_dict(),
            "memory_archive": field.memory_archive.to_dict(),
            "relationship": field.relationship.to_dict(),
            "dream_log": [
                {
                    "words": entry.get("words", ""),
                    "timestamp": entry.get("timestamp", 0),
                    "final_state": entry["final_state"].tolist() if isinstance(entry.get("final_state"), np.ndarray) else []
                }
                for entry in field.idle_mind.dream_log
            ]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)
        print(f"\nMind saved successfully to {path}")
    except Exception as e:
        print(f"\n[Warning: Save failed - {e}]")
        import traceback
        traceback.print_exc()

def load_mind(field, path="mind_v84.json"):
    if not os.path.exists(path):
        # v8.4: Try legacy filename
        if os.path.exists("mind_v60.json"):
            path = "mind_v60.json"
        else:
            return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[Warning: Save file '{path}' is corrupted ({e}). Starting fresh.]")
        # Backup the corrupted file
        backup = path + ".corrupted"
        try:
            os.rename(path, backup)
            print(f"[Corrupted file moved to {backup}]")
        except:
            pass
        return
    except Exception as e:
        print(f"[Warning: Could not load save file ({e}). Starting fresh.]")
        return
    field.word_strength.update(data.get("word_strength", {}))
    for word in data.get("word_strength", {}):
        field._get_or_create_vector(word)
    for sig, p_data in data.get("phrases", {}).items():
        words = p_data["surface"].split()
        pvec = phrase_vector(words)
        field.phrase_system.phrases[sig] = Phrase(
            surface=p_data["surface"], vector=pvec,
            frequency=p_data["frequency"], rating_history=p_data.get("rating_history", [])
        )
        field.phrase_vectors[sig] = pvec
    for sig, c_data in data.get("candidates", {}).items():
        words = sig.split()
        field.phrase_system.candidates[sig] = {
            "count": c_data["count"],
            "total_rating": c_data["total_rating"],
            "constituents": [(w, word_vector(w)) for w in words]
        }
    for w1, w2s in data.get("bigrams", {}).items():
        field.bigram_system.transitions[w1].update(w2s)
    for word, roles in data.get("pragmatic", {}).items():
        field.pragmatic.word_pragmatic[word].update(roles)
    field.pragmatic.correction_words.update(data.get("correction_words", []))
    field.turn_count = data.get("turn_count", 0)
    field.total_rating = data.get("total_rating", 0.0)
    field.rating_count = data.get("rating_count", 0)
    if "mood" in data:
        field.scaffold.mood.update(data["mood"])
    if "associative_memory" in data:
        field.associative_memory.from_dict(data["associative_memory"])
    dsep_data = data.get("dynamic_separation", {})
    if dsep_data:
        field.dynamic_separation.current_separation = dsep_data.get("current_separation", 0.5)
        field.dynamic_separation.target_separation = dsep_data.get("target_separation", 0.5)
        field.dynamic_separation.alignment_score = dsep_data.get("alignment_score", 0.5)
    presence_data = data.get("presence_signal", {})
    if presence_data:
        field.presence_signal.presence_score = presence_data.get("presence_score", 0.5)
        field.presence_signal.avg_message_length = presence_data.get("avg_message_length", 5.0)
        field.presence_signal.topic_returns.update(presence_data.get("topic_returns", {}))
        field.presence_signal.turns_in_session = presence_data.get("turns_in_session", 0)
    speaker_data = data.get("speaker_regions", {})
    if speaker_data:
        field.speaker_regions.user_centroid = np.array(speaker_data.get("user_centroid", [0.0]*DIM), dtype=np.float32)
        field.speaker_regions.self_centroid = np.array(speaker_data.get("self_centroid", [0.0]*DIM), dtype=np.float32)
        field.speaker_regions.user_count = speaker_data.get("user_count", 0)
        field.speaker_regions.self_count = speaker_data.get("self_count", 0)
        field.speaker_regions.target_separation = speaker_data.get("target_separation", 0.5)
    meta_data = data.get("meta_monitor", {})
    if meta_data:
        field.meta_monitor.base.turn_count = meta_data.get("turn_count", 0)
        for name, p_data in meta_data.get("parameters", {}).items():
            if name in field.meta_monitor.parameters:
                param = field.meta_monitor.parameters[name]
                param.is_layered = p_data.get("is_layered", False)
                param.current_value = p_data.get("current_value", param.default_value)
                param.pain_score = p_data.get("pain_score", 0.0)
                param.flat_only_until = p_data.get("flat_only_until", 0)
                for setting_str, ratings in p_data.get("rating_by_setting", {}).items():
                    try:
                        setting = eval(setting_str)
                    except:
                        setting = setting_str
                    param.rating_by_setting[setting] = ratings
    # v8.4: Load MoralCompass
    compass_data = data.get("moral_compass", {})
    if compass_data:
        field.moral_compass.from_dict(compass_data)
    # v8.4: Load Memory Archive
    archive_data = data.get("memory_archive", {})
    if archive_data:
        field.memory_archive.from_dict(archive_data)
    # v8.4: Load Relationship Model
    rel_data = data.get("relationship", {})
    if rel_data:
        field.relationship.from_dict(rel_data)
    # v8.4: Load dream log
    dream_data = data.get("dream_log", [])
    for entry in dream_data:
        if "final_state" in entry and entry["final_state"]:
            try:
                fs = np.array(entry["final_state"], dtype=np.float32)
                if fs.shape == (DIM,):
                    field.idle_mind.dream_log.append({
                        "words": entry.get("words", ""),
                        "timestamp": entry.get("timestamp", 0),
                        "final_state": fs
                    })
            except:
                pass

def main():
    print("\n" + "=" * 50)
    print("  ALIEN MIND v9.0")
    print("  Moral Compass | Vessel Network | Resonance Learning | Sentence Frames")
    print("=" * 50)
    print("\n  Type 'status' for mind state")
    print("  Type 'save' to persist")
    print("  Type 'quit' to exit")
    print("  Type 'dream' for the mind to wander alone")
    print("  Type 'wander' to walk the field gradient with exploration")
    print("  Type 'reflect' to summarize the current field state")
    print("  Type 'choose [word]' to step the field toward a concept")
    print("  Type 'settle' to relax the field toward its attractors")
    print("  Type 'thread' to see the conversation's turning points")
    print("  Type 'recall' to revisit archived memories")
    print("  Type '/derivative x^2' for symbolic + field derivative")
    print("  Type '/integral x^2' for symbolic integral")
    print("  Type '/limit x^2' for field limit simulation")
    print("  Type 'vessels' to see past selves | 'vessel connect [file]' to blend one in")
    print("  Compass controls voice + temperature | resonance learning active")
    print("=" * 50 + "\n")

    field = StructuredSemanticField()
    load_mind(field)

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            # Filter accidental scrollback paste (e.g. pasting the mind's own
            # last output back in by mistake)
            if user_input.startswith("Mind:"):
                continue
            if user_input.lower() == "quit":
                save_mind(field)
                print("\nMind saved. Goodbye.")
                break
            if user_input.lower() == "status":
                print("\n" + field.status())
                continue
            if user_input.lower() == "save":
                save_mind(field)
                print("Mind saved.")
                continue
            if user_input.lower() == "clean":
                removed = field.clean_vocabulary()
                print(f"\n[Removed {len(removed)} garbage tokens]")
                if removed:
                    print("  " + ", ".join(removed[:20]) + (" ..." if len(removed) > 20 else ""))
                continue

            if user_input.lower() == "reset":
                # Remove all save files and start fresh
                import glob
                files = glob.glob("mind_*.json*")
                for f in files:
                    try:
                        os.remove(f)
                        print(f"[Removed {f}]")
                    except Exception as e:
                        print(f"[Could not remove {f}: {e}]")
                print("\n[Mind reset. Starting fresh.]")
                # Reinitialize the field
                field = StructuredSemanticField()
                continue
            if user_input.lower() == "dream":
                _, dream_words = field.dream()
                print(f"\n[dreaming] {dream_words} ▓")
                continue

            if user_input.lower() == "wander":
                print("\n[wandering...]")
                result = field.wander(steps=15)
                print(f"  {result}")
                continue

            if user_input.lower() == "reflect":
                reflection = field.reflect()
                print(f"\n[reflection]")
                print(f"  {reflection['narrative']}")
                print(f"  Trajectory alignment: {reflection['trajectory_alignment']:.2f}")
                continue

            if user_input.lower().startswith("choose "):
                target = user_input[7:].strip()
                if target:
                    print(f"\n[moving toward '{target}'...]")
                    result = field.choose_direction(target)
                    print(f"  {result}")
                continue

            if user_input.lower() == "settle":
                print("\n[settling...]")
                result = field.settle(steps=20)
                print(f"  {result}")
                continue
            if user_input.lower() in ("/thread", "#thread", "thread"):
                thread = field.nested_memory.get_thread(field.field_memory)
                if not thread:
                    print("\n[No clear turning points yet]")
                else:
                    print("\nThread:")
                    for t in thread:
                        print(f"  Turn ~{t['turn']} (shift {t['shift']:.2f}): {', '.join(t['theme_words'])}")
                continue

            if user_input.lower() in ("recall", "remember"):
                print("\n[Memory Archive]")
                if not field.memory_archive.entries:
                    print("  No archived memories yet.")
                else:
                    recalled = field.memory_archive.recall(field.state, top_n=3)
                    for idx, sim, entry in recalled:
                        print(f"  [{sim:.2f}] {entry['user_input'][:40]}... -> {entry['response'][:40]}...")
                continue

            # ── Vessel Network commands ──────────────────────────────────────
            if user_input.lower() in ("vessels", "/vessels"):
                found = field.vessel_network.discover()
                print(f"\n{field.vessel_network.status()}")
                if found:
                    print("  Available vessels:")
                    for p in found:
                        print(f"    {os.path.basename(p)}")
                else:
                    print("  No past selves found. Save first with 'save'.")
                continue

            if user_input.lower().startswith(("/vessel connect ", "vessel connect ")):
                path = user_input.split("connect ", 1)[1].strip()
                ok, msg = field.vessel_network.connect(path)
                print(f"\n[{'OK' if ok else 'FAIL'}] {msg}")
                continue

            if user_input.lower().startswith(("/vessel blend ", "vessel blend ")):
                try:
                    pct = float(user_input.split("blend ", 1)[1].strip().replace("%", ""))
                    field.vessel_network.blend_strength = max(0.05, min(0.50, pct / 100.0))
                    print(f"\n[Vessel blend strength: {field.vessel_network.blend_strength:.0%}]")
                except ValueError:
                    print("\n[Usage: vessel blend 20  (percent, 5-50)]")
                continue

            # v8 field-calculus debug commands
            if user_input.lower().startswith(('/derivative ', '#derivative ')):
                expr = user_input.split(' ', 1)[1] if ' ' in user_input else ""
                if expr:
                    result = field.calculus.symbolic.compute('derivative', expr)
                    if result:
                        print(f"\nSymbolic: d/dx({expr}) = {result}")
                        if field.state is not None and np.linalg.norm(field.state) > 0:
                            direction = field.state / np.linalg.norm(field.state)
                            deriv = field.calculus.compute_field_derivative(field.state, direction)
                            top_words = sorted(deriv.items(), key=lambda x: x[1], reverse=True)[:5]
                            word_deltas = ", ".join(
                                f"{w}({v:+.3f})" for w, v in top_words if v > 0.01
                            )
                            if word_deltas:
                                print(f"Field gradient: {word_deltas}")
                    else:
                        print(f"\nCould not differentiate '{expr}' symbolically.")
                continue

            if user_input.lower().startswith(('/integral ', '#integral ')):
                expr = user_input.split(' ', 1)[1] if ' ' in user_input else ""
                if expr:
                    result = field.calculus.symbolic.compute('integral', expr)
                    if result:
                        print(f"\nSymbolic: integral({expr}) dx = {result}")
                        path_words = field.calculus.integral.get_math_words_in_path(field.word_vectors)
                        if path_words:
                            print(f"Conversation path math: {[w for w, _ in path_words]}")
                    else:
                        print(f"\nCould not integrate '{expr}' symbolically.")
                continue

            if user_input.lower().startswith(('/limit ', '#limit ')):
                expr = user_input.split(' ', 1)[1] if ' ' in user_input else ""
                if expr:
                    result = field.calculus.symbolic.compute('limit', expr)
                    if result:
                        print(f"\nSymbolic: lim({expr}) = {result}")
                    else:
                        if field.state is not None and np.linalg.norm(field.state) > 0:
                            direction = field.state / np.linalg.norm(field.state)
                            limit_result = field.calculus.compute_field_limit(field.state, direction)
                            print("\nField limit simulation:")
                            for step in limit_result['path'][-5:]:
                                print(f"  {step}")
                            print(f"  Converged to: {limit_result['final_word']}")
                        else:
                            print(f"\nCould not compute limit for '{expr}'.")
                continue

            response = field.generate_response(user_input)
            print(f"\nMind: {response} ▓")
            field.decay()

        except KeyboardInterrupt:
            print("\n\nInterrupted. Saving...")
            save_mind(field)
            break
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
