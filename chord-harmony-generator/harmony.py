from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Sequence, Dict, Optional

# Chord-tone roles for omission priority (when voices < chord tones).
# Inclusion order: root, 3rd, 7th, 9th, 5th, 6th, 11th, 13th → 5th omitted first (e.g. G9 in 4 voices).
ROOT, THIRD, FIFTH, SEVENTH, NINTH, ELEVENTH, THIRTEENTH, SIXTH = 0, 1, 2, 3, 4, 5, 6, 7
INCLUSION_ORDER = (ROOT, THIRD, SEVENTH, NINTH, FIFTH, SIXTH, ELEVENTH, THIRTEENTH)


PITCH_CLASS_MAP: Dict[str, int] = {
    "C": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
}


VOICE_RANGES: Dict[int, Tuple[int, int]] = {
    # Default MIDI range (low, high) per voice count. More voices use a looser (wider) range.
    4: (48, 79),   # C3–G5 (typical SATB)
    5: (43, 83),   # G2–B5 (wider for 5 voices)
    6: (40, 86),   # E2–D6 (wider for 6 voices)
}


@dataclass(frozen=True)
class HarmonyWeights:
    """
    Tunable weights for voice-leading cost. Used by the web UI so users can
    adjust style without editing code. All costs are additive; higher = stronger penalty.
    """
    # Motion
    cost_static: float = 0.5           # voice doesn't move
    cost_stepwise: float = 0.2        # move 1–2 semitones (preferred)
    cost_medium_step: float = 0.5     # move 3–5 semitones
    cost_large_leap_base: float = 1.5  # large leap penalty base
    cost_large_leap_per: float = 0.1   # per semitone above 5
    # Parallels and motion
    cost_parallel_5_8: float = 4.0     # parallel 5ths or octaves
    cost_direct_5_8: float = 3.0      # direct (hidden) 5ths/8ves
    cost_voice_crossing: float = 2.5  # voices swap order
    bonus_contrary: float = 0.25      # subtracted when outer voices move contrary
    # Spacing
    cost_wide_gap_base: float = 1.0   # adjacent voices > octave apart
    cost_wide_gap_per: float = 0.1    # per semitone above octave
    spacing_octave: int = 12
    # Chord span (internal): "span" = distance in semitones from lowest to highest note in the chord
    cost_span_tight: float = 0.75     # penalty when span < span_tight_threshold
    cost_span_wide: float = 1.0      # penalty when span > span_wide_threshold
    span_tight_threshold: int = 8     # below this many semitones, chord is "too tight"
    span_wide_threshold: int = 24     # above this many semitones, chord is "too wide"
    # Voicing generator (optional overrides)
    range_low: Optional[int] = None   # if set, override default low bound (MIDI)
    range_high: Optional[int] = None  # if set, override default high bound (MIDI)
    max_spread: int = 31              # max semitones between lowest and highest note in a chord


def default_weights() -> HarmonyWeights:
    return HarmonyWeights()


def weights_from_form(form: Dict[str, str]) -> HarmonyWeights:
    """Build HarmonyWeights from form data (e.g. request.form). Missing keys use defaults."""
    def f(key: str, default: float) -> float:
        v = form.get(key)
        if v is None or v.strip() == "":
            return default
        try:
            return float(v)
        except ValueError:
            return default

    def i(key: str, default: int) -> int:
        v = form.get(key)
        if v is None or v.strip() == "":
            return default
        try:
            return int(v)
        except ValueError:
            return default

    def oi(key: str) -> Optional[int]:
        v = form.get(key)
        if v is None or v.strip() == "":
            return None
        try:
            return int(v)
        except ValueError:
            return None

    d = default_weights()
    return HarmonyWeights(
        cost_static=f("cost_static", d.cost_static),
        cost_stepwise=f("cost_stepwise", d.cost_stepwise),
        cost_medium_step=f("cost_medium_step", d.cost_medium_step),
        cost_large_leap_base=f("cost_large_leap_base", d.cost_large_leap_base),
        cost_large_leap_per=f("cost_large_leap_per", d.cost_large_leap_per),
        cost_parallel_5_8=f("cost_parallel_5_8", d.cost_parallel_5_8),
        cost_direct_5_8=f("cost_direct_5_8", d.cost_direct_5_8),
        cost_voice_crossing=f("cost_voice_crossing", d.cost_voice_crossing),
        bonus_contrary=f("bonus_contrary", d.bonus_contrary),
        cost_wide_gap_base=f("cost_wide_gap_base", d.cost_wide_gap_base),
        cost_wide_gap_per=f("cost_wide_gap_per", d.cost_wide_gap_per),
        spacing_octave=i("spacing_octave", d.spacing_octave),
        cost_span_tight=f("cost_span_tight", d.cost_span_tight),
        cost_span_wide=f("cost_span_wide", d.cost_span_wide),
        span_tight_threshold=i("span_tight_threshold", d.span_tight_threshold),
        span_wide_threshold=i("span_wide_threshold", d.span_wide_threshold),
        range_low=oi("range_low"),
        range_high=oi("range_high"),
        max_spread=i("max_spread", d.max_spread),
    )


@dataclass(frozen=True)
class Chord:
    symbol: str
    pitches: List[int]  # pitch classes 0–11 (unique, unordered)
    root_pc: int        # pitch class of the harmonic root
    bass_pc: Optional[int] = None  # explicit bass (for slash chords), else None
    # (pc, role) for omission: when voices < len(pitches), drop 5th first, then 9th, 11th, 13th.
    tone_roles: Optional[Tuple[Tuple[int, int], ...]] = None  # ((pc, role), ...); role in INCLUSION_ORDER


@dataclass
class HarmonyResult:
    chords: List[Chord]
    voices: List[List[int]]  # voices[v][t] = MIDI pitch number at time t

    def as_note_names(self) -> List[List[str]]:
        return [[midi_to_name(p) for p in voice] for voice in self.voices]


def midi_to_name(m: int) -> str:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    pc = m % 12
    octave = m // 12 - 1
    return f"{names[pc]}{octave}"


def parse_chord_symbol(symbol: str) -> Chord:
    s = symbol.strip()
    if not s:
        raise ValueError("Empty chord symbol")

    # Handle inversions / slash chords, e.g. C/E, Am/G
    bass_pc: Optional[int] = None
    if "/" in s:
        main, bass = s.split("/", 1)
        s_main = main.strip()
        s_bass = bass.strip()
    else:
        s_main = s
        s_bass = ""

    # Parse bass, if given
    if s_bass:
        # Bass can be like E, Eb, F#
        bass_root = s_bass[0].upper()
        bass_rest = s_bass[1:]
        if bass_rest and bass_rest[0] in ("b", "#"):
            bass_root += bass_rest[0].upper()
        if bass_root not in PITCH_CLASS_MAP:
            raise ValueError(f"Unknown bass in chord symbol: {symbol}")
        bass_pc = PITCH_CLASS_MAP[bass_root]

    # Root (with possible accidental)
    root = s_main[0].upper()
    rest = s_main[1:]
    if rest and rest[0] in ("b", "#"):
        root += rest[0].upper()
        rest = rest[1:]

    if root not in PITCH_CLASS_MAP:
        raise ValueError(f"Unknown root in chord symbol: {symbol}")

    pc = PITCH_CLASS_MAP[root]
    quality = rest

    structure = _build_chord_structure(pc, quality)
    pcs = sorted(set(pc for pc, _ in structure))
    roles = tuple(structure) if structure else None

    return Chord(symbol=symbol, pitches=pcs, root_pc=pc, bass_pc=bass_pc, tone_roles=roles)


def _build_chord_structure(root_pc: int, quality: str) -> List[Tuple[int, int]]:
    """
    Build chord as list of (pitch_class, role) for omission priority.
    When voices < chord tones, we drop tones by role: 5th first, then 9th, 11th, 13th.
    """
    q = quality.strip()
    q_lower = q.lower()

    def pc_of(semitones: int) -> int:
        return (root_pc + semitones) % 12

    out: List[Tuple[int, int]] = []
    third = 4
    fifth = 7

    # Triad base
    if "sus2" in q_lower:
        out = [(pc_of(0), ROOT), (pc_of(2), THIRD), (pc_of(fifth), FIFTH)]
    elif "sus4" in q_lower or ("sus" in q_lower and "sus2" not in q_lower):
        out = [(pc_of(0), ROOT), (pc_of(5), THIRD), (pc_of(fifth), FIFTH)]
    elif any(q_lower.startswith(x) for x in ("m7b5", "ø7", "ø")):
        return [(pc_of(0), ROOT), (pc_of(3), THIRD), (pc_of(6), FIFTH), (pc_of(10), SEVENTH)]
    elif any(q_lower.startswith(x) for x in ("dim7", "o7")):
        return [(pc_of(0), ROOT), (pc_of(3), THIRD), (pc_of(6), FIFTH), (pc_of(9), SEVENTH)]
    elif q_lower.startswith(("dim", "o")):
        out = [(pc_of(0), ROOT), (pc_of(3), THIRD), (pc_of(6), FIFTH)]
    elif q_lower.startswith(("m", "min", "mi", "-")) and "maj" not in q_lower and "M7" not in q:
        out = [(pc_of(0), ROOT), (pc_of(3), THIRD), (pc_of(fifth), FIFTH)]
    elif q_lower.startswith(("aug", "+")):
        out = [(pc_of(0), ROOT), (pc_of(4), THIRD), (pc_of(8), FIFTH)]
    else:
        out = [(pc_of(0), ROOT), (pc_of(4), THIRD), (pc_of(fifth), FIFTH)]

    # 6th
    if "6/9" in q_lower or "69" in q_lower:
        out.append((pc_of(9), SIXTH))
        out.append((pc_of(14), NINTH))
    elif "6" in q_lower and "add6" not in q_lower:
        out.append((pc_of(9), SIXTH))

    # 7th (check "M7" in original quality so GM7 is not parsed as Gm7)
    if any(x in q_lower for x in ("maj7", "Δ7", "Δ")) or "M7" in q:
        out.append((pc_of(11), SEVENTH))
    elif any(x in q_lower for x in ("7", "9", "11", "13")):
        out.append((pc_of(10), SEVENTH))

    # Extensions
    if "9" in q_lower:
        out.append((pc_of(14), NINTH))
    if "11" in q_lower:
        out.append((pc_of(17), ELEVENTH))
    if "13" in q_lower:
        out.append((pc_of(21), THIRTEENTH))
    if "add2" in q_lower or "add9" in q_lower:
        out.append((pc_of(14), NINTH))
    if "add4" in q_lower or "add11" in q_lower:
        out.append((pc_of(17), ELEVENTH))
    if "add6" in q_lower:
        out.append((pc_of(9), SIXTH))
    if "b9" in q_lower:
        out.append((pc_of(13), NINTH))
    if "#9" in q_lower:
        out.append((pc_of(15), NINTH))

    # Dedupe by pc, keeping first occurrence (so root/3rd/7th stay)
    seen: set[int] = set()
    unique: List[Tuple[int, int]] = []
    for pc, role in out:
        if pc not in seen:
            seen.add(pc)
            unique.append((pc, role))
    return unique


def _effective_chord_tones(chord: Chord, num_voices: int) -> List[int]:
    """
    When chord has more tones than voices, omit by role: 5th first, then 9th, 11th, 13th.
    E.g. G9 with 4 voices → use root, 3rd, 7th, 9th (omit 5th).
    """
    pcs = chord.pitches
    if len(pcs) <= num_voices or chord.tone_roles is None:
        return list(pcs)
    # Sort by inclusion priority (root, 3rd, 7th, 9th, 5th, …), take first num_voices
    order_idx = {r: i for i, r in enumerate(INCLUSION_ORDER)}
    sorted_roles = sorted(
        chord.tone_roles,
        key=lambda x: order_idx.get(x[1], 99),
    )
    return [pc for pc, _ in sorted_roles[:num_voices]]


def parse_progression(text: str) -> List[Chord]:
    # Split on common separators
    tokens: List[str] = []
    for part in text.replace("|", " ").replace(",", " ").split():
        tokens.append(part)
    if not tokens:
        raise ValueError("No chords found in progression.")
    return [parse_chord_symbol(tok) for tok in tokens]


def generate_harmony(
    progression: Sequence[Chord],
    num_voices: int = 4,
    base_octave: int = 4,
    weights: Optional[HarmonyWeights] = None,
    locked_voicings: Optional[Dict[int, Sequence[int]]] = None,
) -> HarmonyResult:
    """
    locked_voicings: optional dict chord_index -> voicing (list/tuple of MIDI, lowest to highest).
    Locked chords use that single voicing; others are optimized.
    """
    if num_voices < 4:
        raise ValueError("At least 4 voices are required.")
    if num_voices > 6:
        raise ValueError("More than 6 voices is not supported in this simple model.")

    w = weights or default_weights()
    pr = VOICE_RANGES.get(num_voices, (48, 79))
    low = w.range_low if w.range_low is not None else pr[0]
    high = w.range_high if w.range_high is not None else pr[1]

    locked = locked_voicings or {}
    candidates_per_step: List[List[Tuple[int, ...]]] = []
    for i, chord in enumerate(progression):
        if i in locked:
            raw = locked[i]
            if len(raw) != num_voices:
                raise ValueError(
                    f"Locked voicing for chord {i + 1} has {len(raw)} notes; expected {num_voices}."
                )
            candidates_per_step.append([tuple(sorted(raw))])
            continue
        candidates = generate_voicings_for_chord(
            chord, num_voices, low, high, base_octave, max_spread=w.max_spread
        )
        if not candidates:
            raise RuntimeError(f"No voicings generated for chord {chord.symbol}")
        candidates_per_step.append(candidates)

    paths: List[Dict[int, Tuple[float, Optional[int]]]] = []
    first_chord = progression[0]
    last_chord = progression[-1]

    first_step: Dict[int, Tuple[float, Optional[int]]] = {}
    for i, voicing in enumerate(candidates_per_step[0]):
        cost = voice_leading_cost(None, voicing, w)
        cost += _bass_root_preference_cost(voicing, first_chord)
        first_step[i] = (cost, None)
    paths.append(first_step)

    for step in range(1, len(progression)):
        prev_states = paths[-1]
        curr_states: Dict[int, Tuple[float, Optional[int]]] = {}
        same_as_prev = progression[step].symbol == progression[step - 1].symbol
        is_last = step == len(progression) - 1
        for i, curr_voicing in enumerate(candidates_per_step[step]):
            best_cost = float("inf")
            best_prev: Optional[int] = None
            for j, (prev_cost, _) in prev_states.items():
                prev_voicing = candidates_per_step[step - 1][j]
                c = prev_cost + voice_leading_cost(
                    prev_voicing, curr_voicing, w, same_chord=same_as_prev
                )
                if is_last:
                    c += _bass_root_preference_cost(curr_voicing, last_chord)
                if c < best_cost:
                    best_cost = c
                    best_prev = j
            curr_states[i] = (best_cost, best_prev)
        paths.append(curr_states)

    # Backtrack best path
    final_states = paths[-1]
    last_idx = min(final_states, key=lambda k: final_states[k][0])

    indices: List[int] = [last_idx]
    for step in range(len(progression) - 1, 0, -1):
        _, prev_idx = paths[step][indices[-1]]
        assert prev_idx is not None
        indices.append(prev_idx)
    indices.reverse()

    chosen_voicings = [candidates_per_step[step][idx] for step, idx in enumerate(indices)]

    # Transpose into voices (chord_voicing is lowest to highest)
    voices: List[List[int]] = [[] for _ in range(num_voices)]
    for chord_voicing in chosen_voicings:
        for v_idx, note in enumerate(chord_voicing):
            voices[v_idx].append(note)

    # Return highest voice first, then descending to lowest
    voices = list(reversed(voices))

    return HarmonyResult(chords=list(progression), voices=voices)


def get_chord_alternatives(
    progression: Sequence[Chord],
    num_voices: int,
    weights: Optional[HarmonyWeights],
    path_voicings: List[Tuple[int, ...]],
    chord_index: int,
    top_n: int = 8,
) -> List[Tuple[Tuple[int, ...], float]]:
    """
    Return alternative voicings for one chord, scored by local cost (prev -> cand -> next).
    path_voicings[t] = voicing at step t (lowest to highest). Returns list of (voicing, cost) sorted by cost.
    """
    if chord_index < 0 or chord_index >= len(progression):
        return []
    w = weights or default_weights()
    pr = VOICE_RANGES.get(num_voices, (48, 79))
    low = w.range_low if w.range_low is not None else pr[0]
    high = w.range_high if w.range_high is not None else pr[1]

    prev = path_voicings[chord_index - 1] if chord_index > 0 else None
    next_v = (
        path_voicings[chord_index + 1]
        if chord_index + 1 < len(path_voicings)
        else None
    )
    chord = progression[chord_index]
    same_as_prev = (
        chord_index > 0
        and progression[chord_index].symbol == progression[chord_index - 1].symbol
    )
    same_as_next = (
        chord_index + 1 < len(progression)
        and progression[chord_index].symbol == progression[chord_index + 1].symbol
    )
    candidates = generate_voicings_for_chord(
        chord, num_voices, low, high, base_octave=4, max_spread=w.max_spread
    )
    scored: List[Tuple[Tuple[int, ...], float]] = []
    for c in candidates:
        cost = voice_leading_cost(prev, c, w, same_chord=same_as_prev)
        if next_v is not None:
            cost += voice_leading_cost(c, next_v, w, same_chord=same_as_next)
        scored.append((c, cost))
    scored.sort(key=lambda x: x[1])
    return scored[:top_n]


def generate_voicings_for_chord(
    chord: Chord,
    num_voices: int,
    low: int,
    high: int,
    base_octave: int = 4,
    max_spread: int = 16,
) -> List[Tuple[int, ...]]:
    # When chord has more tones than voices (e.g. G9 with 4 voices), use effective set:
    # omit 5th first, then 9th, 11th, 13th (see _effective_chord_tones).
    effective_pcs = _effective_chord_tones(chord, num_voices)
    if len(effective_pcs) == 0:
        return []

    root_pc = chord.root_pc
    bass_pc = chord.bass_pc

    # Slash chord with bass not in chord (e.g. Dm7b5/E): bass takes one slot, upper voices from chord.
    if bass_pc is not None and bass_pc not in effective_pcs:
        return _voicings_slash_bass_outside(
            chord, num_voices, low, high, base_octave, max_spread, effective_pcs
        )

    # Build candidate chord tones from effective set only (bass may be in chord, e.g. Gsus/C)
    tone_midis: List[int] = []
    for octave in range(2, 7):
        for pc in effective_pcs:
            m = pc + 12 * octave
            if low <= m <= high:
                tone_midis.append(m)

    tone_midis = sorted(set(tone_midis))

    # When we have more voices than chord tones (e.g. GM7 with 6 voices), allow doubling beyond root.
    max_root = 2
    max_other = 2 if num_voices > len(effective_pcs) else 1
    max_per_pc = max(2, (num_voices + len(effective_pcs) - 1) // len(effective_pcs))
    max_other = min(max_other, max_per_pc)

    voicings: List[Tuple[int, ...]] = []

    def backtrack(
        current: List[int],
        start_idx: int,
        used_pcs: set[int],
        counts: Dict[int, int],
    ) -> None:
        if len(current) == num_voices:
            if current[-1] - current[0] <= max_spread:
                if all(pc in used_pcs for pc in effective_pcs):
                    if bass_pc is not None and (current[0] % 12) != bass_pc:
                        return
                    voicings.append(tuple(current))
            return

        for i in range(start_idx, len(tone_midis)):
            note = tone_midis[i]
            if current and note < current[-1]:
                continue
            pc = note % 12
            if pc not in effective_pcs:
                continue
            existing = counts.get(pc, 0)
            cap = max_root if pc == root_pc else max_other
            if existing >= cap:
                continue
            new_used = set(used_pcs)
            new_used.add(pc)
            new_counts = dict(counts)
            new_counts[pc] = existing + 1
            backtrack(current + [note], i, new_used, new_counts)

    backtrack([], 0, set(), {})

    # Limit number of voicings for performance
    if len(voicings) > 500:
        voicings = voicings[:500]

    return voicings


def _voicings_slash_bass_outside(
    chord: Chord,
    num_voices: int,
    low: int,
    high: int,
    base_octave: int,
    max_spread: int,
    effective_pcs: List[int],
) -> List[Tuple[int, ...]]:
    """Generate voicings when bass is not a chord tone (e.g. Dm7b5/E): one bass note + (n-1) chord tones above."""
    assert chord.bass_pc is not None
    bass_pc = chord.bass_pc
    upper_count = num_voices - 1
    if upper_count <= 0:
        return []
    effective_upper = _effective_chord_tones(chord, upper_count)
    if len(effective_upper) == 0:
        return []

    voicings: List[Tuple[int, ...]] = []
    for octave in range(2, 6):
        bass_note = bass_pc + 12 * octave
        if bass_note < low or bass_note > high:
            continue
        upper_low = bass_note + 1
        if upper_low > high:
            continue
        upper_candidates = _generate_upper_voicings(
            chord, upper_count, upper_low, high, max_spread, effective_upper
        )
        for u in upper_candidates:
            if u[0] - bass_note <= max_spread:
                voicings.append((bass_note,) + u)
    if len(voicings) > 500:
        voicings = voicings[:500]
    return voicings


def _generate_upper_voicings(
    chord: Chord,
    num_voices: int,
    low: int,
    high: int,
    max_spread: int,
    effective_pcs: List[int],
) -> List[Tuple[int, ...]]:
    """Generate (num_voices) notes from chord in [low, high], all from effective_pcs."""
    root_pc = chord.root_pc
    tone_midis = []
    for octave in range(2, 7):
        for pc in effective_pcs:
            m = pc + 12 * octave
            if low <= m <= high:
                tone_midis.append(m)
    tone_midis = sorted(set(tone_midis))
    max_root = 2
    max_other = 2 if num_voices > len(effective_pcs) else 1
    max_per_pc = max(2, (num_voices + len(effective_pcs) - 1) // len(effective_pcs))
    max_other = min(max_other, max_per_pc)

    out: List[Tuple[int, ...]] = []

    def backtrack(
        current: List[int],
        start_idx: int,
        used_pcs: set[int],
        counts: Dict[int, int],
    ) -> None:
        if len(current) == num_voices:
            if current[-1] - current[0] <= max_spread and all(
                pc in used_pcs for pc in effective_pcs
            ):
                out.append(tuple(current))
            return
        for i in range(start_idx, len(tone_midis)):
            note = tone_midis[i]
            if current and note < current[-1]:
                continue
            pc = note % 12
            if pc not in effective_pcs:
                continue
            existing = counts.get(pc, 0)
            cap = max_root if pc == root_pc else max_other
            if existing >= cap:
                continue
            new_used = set(used_pcs)
            new_used.add(pc)
            new_counts = dict(counts)
            new_counts[pc] = existing + 1
            backtrack(current + [note], i, new_used, new_counts)

    backtrack([], 0, set(), {})
    return out


def voice_leading_cost(
    prev: Optional[Tuple[int, ...]],
    curr: Tuple[int, ...],
    weights: Optional[HarmonyWeights] = None,
    same_chord: bool = False,
) -> float:
    """
    Cost for a single chord-to-chord transition (basic harmony/counterpoint rules).
    Voicing tuples are ordered lowest to highest (bass = index 0, soprano = index -1).
    same_chord: when True, identical adjacent chords — static voice gets no penalty.
    """
    w = weights or default_weights()
    if prev is None:
        return chord_internal_cost(curr, w)

    cost = 0.0
    n = len(prev)

    for p, c in zip(prev, curr):
        step = abs(c - p)
        if step == 0:
            if not same_chord:
                cost += w.cost_static
        elif step == 1 or step == 2:
            cost += w.cost_stepwise
        elif step <= 5:
            cost += w.cost_medium_step
        else:
            cost += w.cost_large_leap_base + w.cost_large_leap_per * (step - 5)

    for i in range(n):
        for j in range(i + 1, n):
            interval_prev = abs(prev[j] - prev[i]) % 12
            interval_curr = abs(curr[j] - curr[i]) % 12
            if interval_prev in (7, 0) and interval_curr == interval_prev:
                cost += w.cost_parallel_5_8

    if n >= 2:
        bass_prev, bass_curr = prev[0], curr[0]
        sop_prev, sop_curr = prev[-1], curr[-1]
        interval_curr = abs(sop_curr - bass_curr) % 12
        if interval_curr in (0, 7):
            bass_dir = bass_curr - bass_prev
            sop_dir = sop_curr - sop_prev
            if bass_dir != 0 and sop_dir != 0 and (bass_dir > 0) == (sop_dir > 0):
                cost += w.cost_direct_5_8

    for i in range(n):
        for j in range(i + 1, n):
            if (prev[i] - prev[j]) * (curr[i] - curr[j]) < 0:
                cost += w.cost_voice_crossing

    if n >= 2:
        bass_dir = curr[0] - prev[0]
        sop_dir = curr[-1] - prev[-1]
        if bass_dir != 0 and sop_dir != 0 and (bass_dir > 0) != (sop_dir > 0):
            cost -= w.bonus_contrary

    octave = w.spacing_octave
    for i in range(len(curr) - 1):
        dist = curr[i + 1] - curr[i]
        if dist > octave:
            cost += w.cost_wide_gap_base + w.cost_wide_gap_per * (dist - octave)
        # Inner voices (indices 1..n-2): extra penalty if gap too wide
        if 1 <= i <= n - 2 and dist > octave:
            cost += 0.4
        # Adjacent voices: avoid major 7th (11 semitones) and minor 9th (13 semitones)
        if dist == 11 or dist == 13:
            cost += 2.0

    cost += chord_internal_cost(curr, w)
    return cost


def _bass_root_preference_cost(voicing: Tuple[int, ...], chord: Chord) -> float:
    """Cost added when bass is not the chord root (for first/last chord preference)."""
    if not voicing:
        return 0.0
    bass_pc = voicing[0] % 12
    return 0.0 if bass_pc == chord.root_pc else 0.8


def chord_internal_cost(
    voicing: Tuple[int, ...],
    weights: Optional[HarmonyWeights] = None,
) -> float:
    w = weights or default_weights()
    low, high = min(voicing), max(voicing)
    span = high - low
    cost = 0.0
    if span < w.span_tight_threshold:
        cost += w.cost_span_tight
    if span > w.span_wide_threshold:
        cost += w.cost_span_wide
    return cost


def export_to_midi(result: HarmonyResult, filename: str = "output.mid") -> None:
    """
    Export the harmony to a simple MIDI file using music21.

    Each voice is assigned a different woodwind instrument to make
    the texture more vivid in playback.

    This requires music21 to be installed. If it is not available,
    this function will raise ImportError.
    """
    from music21 import stream, note, tempo, chord, instrument  # type: ignore

    s = stream.Score()
    s.append(tempo.MetronomeMark(number=80))

    num_voices = len(result.voices)

    # Woodwind palette that loops if there are more than 4–5 voices
    woodwinds = [
        instrument.Flute(),
        instrument.Oboe(),
        instrument.Clarinet(),
        instrument.Bassoon(),
        instrument.AltoSaxophone(),
        instrument.BassClarinet(),
    ]

    parts = []
    for i in range(num_voices):
        part = stream.Part(id=f"Voice {i + 1}")
        inst = woodwinds[i % len(woodwinds)]
        part.insert(0, inst)
        parts.append(part)

    for v_idx, voice in enumerate(result.voices):
        p = parts[v_idx]
        for midi_pitch in voice:
            n = note.Note(midi_pitch, quarterLength=1.0)
            p.append(n)
        s.append(p)

    # Add chord labels as a separate part with chord symbols
    chord_part = stream.Part(id="Chords")
    for ch in result.chords:
        c = chord.Chord([p + 60 for p in ch.pitches])  # on top of middle C
        c.quarterLength = 1.0
        c.addLyric(ch.symbol)
        chord_part.append(c)
    s.append(chord_part)

    s.write("midi", fp=filename)

