"""
Flow Chart Engine (v0.2) — Duckdown Records
Implements the detection/assignment Logic from the Flow Chart ontology doc:
phonemic transcription -> stress detection -> syllable segmentation ->
multisyllabic / cross-word candidate generation -> similarity clustering ->
chain formation (largest-unit-first) -> color assignment -> density scoring.

Input: a list of lines, each {start, end, text}.
Output: chain-tagged structure ready to feed any renderer (webpage / burned-in
video / 3D room lyric screen) instead of hand-tagging rhymes by ear.
"""

import re
import os
import json
import itertools
import cmudict

CMU = cmudict.dict()


def _load_custom_pronunciations():
    """Merges custom_pronunciations.txt (same 'word phones...' shape as the
    Studio/JS side, sourced only from Duckdown's own catalog's slang/ad-libs
    — see docs/PHONEMIC_KNOWLEDGE.md) into CMU, overriding any dictionary
    entry for the same word. Keeps server-side and client-side (cmu_engine.js)
    in parity on the same pronunciation data."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_pronunciations.txt")
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(" ")
            word, phones = parts[0], parts[1:]
            CMU[word.lower()] = [phones]


_load_custom_pronunciations()

PALETTE = ["#e8a13c", "#5fb3a3", "#e0524a", "#8a7fd6", "#4aa3e0",
           "#d4af37", "#6fbf73", "#e07bb0", "#c98a4b", "#7a9fd6"]

VOWELS = {"AA","AE","AH","AO","AW","AY","EH","ER","EY","IH","IY","OW","OY","UH","UW"}

# ARPAbet -> IPA (standard, public linguistic mapping — see cmu_engine.js for
# the JS mirror and full docstring). Display/documentation utility, no
# interaction with rhyme-detection logic.
ARPABET_TO_IPA = {
    "AA": "ɑ", "AE": "æ", "AH": "ʌ", "AO": "ɔ", "AW": "aʊ", "AY": "aɪ",
    "B": "b", "CH": "tʃ", "D": "d", "DH": "ð", "EH": "ɛ", "ER": "ɝ", "EY": "eɪ",
    "F": "f", "G": "ɡ", "HH": "h", "IH": "ɪ", "IY": "i", "JH": "dʒ", "K": "k",
    "L": "l", "M": "m", "N": "n", "NG": "ŋ", "OW": "oʊ", "OY": "ɔɪ", "P": "p",
    "R": "ɹ", "S": "s", "SH": "ʃ", "T": "t", "TH": "θ", "UH": "ʊ", "UW": "u",
    "V": "v", "W": "w", "Y": "j", "Z": "z", "ZH": "ʒ",
}
SCHWA_REDUCIBLE = {"AH", "IH"}


def arpabet_to_ipa(phones):
    """Converts a raw ARPAbet phone list (with stress digits) to an IPA
    string, with primary/secondary stress marks (ˈ/ˌ) before the stressed
    vowel. Mirrors cmu_engine.js's arpabetToIpa() exactly."""
    out = []
    for p in phones:
        m = re.search(r"(\d)$", p)
        stress = m.group(1) if m else None
        base = re.sub(r"\d$", "", p)
        if stress == "1":
            out.append("ˈ")
        elif stress == "2":
            out.append("ˌ")
        ipa = ARPABET_TO_IPA.get(base, base.lower())
        if stress == "0" and base in SCHWA_REDUCIBLE:
            ipa = "ə"
        out.append(ipa)
    return "".join(out)


def word_to_ipa(word):
    """Looks up a word (CMU + custom-pronunciation dict) and returns its IPA
    transcription, or None if unknown."""
    phones = get_phones(clean_word(word))
    return arpabet_to_ipa(phones) if phones else None

TIER_RANK = {"perfect": 3, "slant": 2, "assonance": 1, "consonance": 1}

STOPWORDS = {
    "A","AN","AND","THE","TO","OF","IN","ON","IS","IT","I","YOU","WE","THAT",
    "THIS","FOR","WITH","AT","BUT","OR","SO","IF","AS","BE","MY","YOUR","HIS",
    "HER","ITS","OUR","THEIR","AM","ARE","WAS","WERE","DO","DOES","DID",
}


def clean_word(w):
    return re.sub(r"[^A-Za-z']", "", w).upper()


def get_phones(word):
    """First pronunciation from CMU dict, or None if unknown (proper nouns,
    slang, ad-libs like 'BCC' commonly fall out here — expected, not an
    error). Breaks phone-stream continuity at that point, which correctly
    prevents multisyllabic candidates from spanning an unknown word."""
    entries = CMU.get(word.lower())
    return entries[0] if entries else None


def segment_syllables(phones):
    """Split a word's phone list into syllables for rhyme purposes: each
    syllable = a vowel (nucleus) + everything up to the next vowel (coda).
    Onset consonants before the word's FIRST vowel are deliberately dropped
    — rhyme only cares about the rime (nucleus+coda), not onset."""
    vowel_idxs = [i for i, p in enumerate(phones) if re.sub(r"\d", "", p) in VOWELS]
    syllables = []
    for k, v in enumerate(vowel_idxs):
        end = vowel_idxs[k + 1] if k + 1 < len(vowel_idxs) else len(phones)
        syl = phones[v:end]
        syllables.append({
            "phones": [re.sub(r"\d", "", p) for p in syl],
            "stressed": syl[0].endswith("1"),
        })
    return syllables


def vowels_only(tail):
    return [p for p in tail if p in VOWELS]


def compare_tails(a, b):
    if a is None or b is None or not a or not b:
        return None
    if a == b:
        return "perfect"
    if len(a) == len(b):
        diffs = sum(1 for x, y in zip(a, b) if x != y)
        if diffs == 1:
            return "slant"
    va, vb = vowels_only(a), vowels_only(b)
    if va and va == vb:
        return "assonance"
    if a[-1:] == b[-1:] and a[-1:]:
        return "consonance"
    return None


class UnionFind:
    """Kept for reference/testing only — this is single-linkage clustering
    and is what caused the v0.1 blob bug at Slant/Assonance tiers. Do not
    use for anything below 'perfect'. See cluster_candidates() for the
    complete-linkage replacement used everywhere now."""
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, x):
        while self.parent[x] != x:
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def build_word_index(lines):
    """Flat word list across all lines + per-word syllable segmentation +
    an interpolated timestamp for each word (linear spread across the
    line's [start, end] span). Timestamps are what let the engine use a
    real time-based lookahead window instead of a fixed word count — see
    estimate_bpm() and the lookahead_seconds machinery in build_chains()."""
    words = []
    for li, line in enumerate(lines):
        line_words = re.findall(r"[A-Za-z']+", line["text"])
        span = max(0.001, line["end"] - line["start"])
        step = span / max(1, len(line_words))
        for wi, w in enumerate(line_words):
            cw = clean_word(w)
            phones = get_phones(cw) if cw not in STOPWORDS else None
            syllables = segment_syllables(phones) if phones else []
            words.append({
                "line_idx": li, "word_idx_in_line": wi, "text": w,
                "syllables": syllables,
                "t": line["start"] + wi * step,
            })
    return words


def estimate_bpm(audio_path):
    """Beat-tracking BPM estimate via librosa. Optional convenience helper —
    callers can also just pass a known bpm directly to build_chains() /
    annotate_lines() without touching audio at all."""
    import librosa
    y, sr = librosa.load(audio_path, sr=None)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    return float(tempo)


def bars_to_seconds(bars, bpm, beats_per_bar=4):
    """Convert a musical-bar span to seconds at a given tempo. Used to turn
    'look back N bars' (a musically meaningful, tempo-relative unit) into a
    concrete time window in seconds, rather than assuming a fixed word count
    applies equally to a slow flow and a rapid-fire one."""
    seconds_per_beat = 60.0 / bpm
    return bars * beats_per_bar * seconds_per_beat


def build_syllable_stream(words):
    """Flatten (word_idx, syllable_idx) across the whole song, in order.
    Only words with known pronunciations contribute — an unknown word breaks
    stream continuity at that point (correctly prevents a multisyllabic
    candidate from spanning across it)."""
    stream = []
    for wi, w in enumerate(words):
        for si in range(len(w["syllables"])):
            stream.append((wi, si))
    return stream


def gather_candidates(words, stream, max_k=3, lookahead_words=None):
    # Note: lookahead_words is unused here (kept only for call-signature
    # compatibility) — windowing happens later in cluster_candidates() via
    # lookahead_seconds, not at candidate-generation time.
    """For each end-of-word syllable position with primary stress, generate
    candidate rhyme anchors for unit sizes K=max_k..1 syllables. Returns
    dict keyed by K -> list of candidates, each candidate:
    {stream_pos, tail_phones, word_start, word_end}.
    word_start != word_end marks a Cross-Word Chain candidate.

    Also returns internal_candidates: single-syllable (K=1) anchors at every
    stressed syllable that is NOT the final syllable of its word. These feed
    the separate polyphony/Compound Split pass — see find_polyphony()."""
    candidates = {k: [] for k in range(1, max_k + 1)}
    internal_candidates = []

    for pos, (wi, si) in enumerate(stream):
        stressed = words[wi]["syllables"][si]["stressed"]
        is_last_syllable_of_word = (si == len(words[wi]["syllables"]) - 1)

        if is_last_syllable_of_word:
            if not stressed:
                continue
            for k in range(1, max_k + 1):
                start = pos - k + 1
                if start < 0:
                    continue
                span = stream[start:pos + 1]
                tail_phones = []
                for (swi, ssi) in span:
                    tail_phones.extend(words[swi]["syllables"][ssi]["phones"])
                candidates[k].append({
                    "stream_pos": pos,
                    "tail": tail_phones,
                    "word_start": span[0][0],
                    "word_end": span[-1][0],
                    "t": words[wi]["t"],
                })
        else:
            # non-final syllable: only useful for polyphony if this word has
            # 2+ syllables at all, and this specific syllable carries stress
            # (an unstressed internal syllable is not a plausible rhyme
            # anchor for the same reason unstressed function words aren't)
            if stressed:
                internal_candidates.append({
                    "stream_pos": pos,
                    "tail": words[wi]["syllables"][si]["phones"],
                    "word_start": wi,
                    "word_end": wi,
                    "syllable_idx": si,
                    "syllable_count": len(words[wi]["syllables"]),
                    "t": words[wi]["t"],
                })

    return candidates, internal_candidates


def cluster_candidates(cands, lookahead_seconds, min_tier):
    """Complete-linkage clustering (v0.3 fix, replaces single-linkage
    union-find). A candidate may only join an EXISTING cluster if it meets
    min_tier against every member already in that cluster — not just one.
    This is what structurally prevents a single weak/coincidental match
    from fusing two otherwise-unrelated chains into a blob, which is
    exactly what broke Slant/Assonance under the old union-find approach
    (verified: min_tier='perfect' stayed clean under union-find purely by
    luck, because exact-match links are rare enough to not cascade — not
    because union-find itself was sound).

    The window check (v0.5: TIME-based via lookahead_seconds, not a fixed
    word count) is enforced against the most recently added member of a
    cluster, matching the ontology's premise that rhyme chains decay over
    distance rather than persisting forever. Time-based windowing is what
    lets the same 'how far back do we look' setting behave consistently
    across a slow flow and a rapid-fire one — a fixed word count doesn't,
    since word density per bar varies a lot with flow speed. See
    bars_to_seconds() for how a BPM turns into lookahead_seconds.
    """
    tier_rank_min = TIER_RANK[min_tier]
    clusters = []  # list of dicts: {members: [idx,...], tiers: {(i,j): tier}}

    for i, cand in enumerate(cands):
        joined = False
        for cluster in clusters:
            last_member = cluster["members"][-1]
            if cand["t"] - cands[last_member]["t"] > lookahead_seconds:
                continue
            # complete-linkage: must match EVERY existing member
            pairwise = {}
            ok = True
            for m in cluster["members"]:
                tier = compare_tails(cand["tail"], cands[m]["tail"])
                if not tier or TIER_RANK[tier] < tier_rank_min:
                    ok = False
                    break
                pairwise[m] = tier
            if ok:
                cluster["members"].append(i)
                for m, t in pairwise.items():
                    cluster["tiers"][(m, i)] = t
                joined = True
                break
        if not joined:
            clusters.append({"members": [i], "tiers": {}})

    chains = []
    for cluster in clusters:
        if len(cluster["members"]) < 2:
            continue
        best_tier = "consonance"
        for t in cluster["tiers"].values():
            if TIER_RANK[t] > TIER_RANK[best_tier]:
                best_tier = t
        chains.append({"members": sorted(cluster["members"]), "strength": best_tier})
    return chains


def find_vowel_runs(candidates_by_k, lookahead_seconds, min_run_length=3):
    """Cross-language technique integration: generalizes the mora work's
    'vowel sequence across units, consonants ignored' methodology (母音踏み,
    the PRIMARY rhyme currency in Japanese — see language_profiles.py) into
    an ADDITIONAL detection pass for English multisyllabic flow.

    This is a real, documented English rap technique in its own right —
    multisyllabic 'assonance chains' where a run of vowel sounds repeats
    across a phrase while the surrounding consonants differ freely — but the
    existing engine only surfaces it as a side effect of the Assonance tier
    on a single K-sized tail, which can miss it when a run is longer than
    max_k syllables or when tier clustering has already claimed those
    syllables for a stronger Perfect/Slant match at a different K.

    Runs INDEPENDENTLY of the primary chain-claiming pass (does not consume
    claimed_positions) — this is a parallel, informational technique tag,
    not a competing claim on the same words. A word can be both in a primary
    chain AND flagged as part of a vowel run.

    Returns a list of vowel-run groups: {vowels, members: [candidate dicts]}.
    """
    # Only K=2/3 candidates carry enough syllables for "run" to be meaningful;
    # a single-syllable vowel match is just the existing Assonance tier.
    pool = [c for k in (2, 3) for c in candidates_by_k.get(k, [])]
    if len(pool) < 2:
        return []

    def vowel_seq(tail):
        return tuple(p for p in tail if p in VOWELS)

    clusters = []
    for cand in pool:
        vs = vowel_seq(cand["tail"])
        if len(vs) < min_run_length:
            continue
        joined = False
        for cluster in clusters:
            last = cluster["members"][-1]
            if cand["t"] - last["t"] > lookahead_seconds:
                continue
            if cluster["vowels"] == vs:
                cluster["members"].append(cand)
                joined = True
                break
        if not joined:
            clusters.append({"vowels": vs, "members": [cand]})

    return [c for c in clusters if len(c["members"]) >= 2]


def find_polyphony(words, internal_candidates, primary_word_tag, lookahead_seconds, min_tier):
    """Compound Split / polyphony detection.

    RESOLVED (was an open ontology question, now decided): this pass runs
    AUTOMATICALLY as part of the standard pipeline — it is not a manual,
    opt-in step. Any word meeting the criteria below gets flagged; there is
    no separate flag callers need to set to enable it.

    A word is genuinely polyphonic when it has 2+ syllables, its FINAL
    syllable anchors one recurring chain (already found by the primary
    pass), AND a NON-final stressed syllable of that same word independently
    matches a *different* recurring pattern elsewhere in the song — i.e. two
    simultaneous chain memberships in one word, which is what the ontology's
    Compound Split / Polyphonic Unit terms describe (seen directly in the
    Meat Grinder reference, where a compound word splits into two colors
    because each half anchors a different rhyme family).

    This is deliberately a SEPARATE clustering pass over internal syllables
    only, rather than merging them into the primary pass — an internal
    syllable competing for the same claimed positions as final syllables
    would break the largest-unit-first priority the primary pass depends on.
    Secondary chains get their own chain_id namespace continuing the color
    cycle, so they're visually distinct from primary chains even if a viewer
    is looking at both at once.

    Known approximation: CMU phones don't map 1:1 to letters, so the
    "split point" for rendering (which characters belong to which half) is
    estimated proportionally by syllable index within the word, not derived
    from true grapheme-to-phoneme alignment. Good enough to color a word
    two-tone; not precise enough for anything requiring exact letter
    boundaries.
    """
    if len(internal_candidates) < 2:
        return [], {}

    secondary_chains_raw = cluster_candidates(internal_candidates, lookahead_seconds, min_tier)
    secondary_chains = []
    for rc in secondary_chains_raw:
        member_cands = [internal_candidates[i] for i in rc["members"]]
        secondary_chains.append({"strength": rc["strength"], "candidates": member_cands})

    secondary_chains.sort(key=lambda c: min(m["word_start"] for m in c["candidates"]))

    polyphony = {}
    for idx, sc in enumerate(secondary_chains):
        for cand in sc["candidates"]:
            wi = cand["word_start"]
            # only meaningful if this word ALSO has a primary (final-syllable)
            # chain assignment — otherwise it's just an internal chain with
            # no second membership to visually split against
            if wi not in primary_word_tag:
                continue
            if wi in polyphony:
                continue  # already flagged via an earlier secondary chain
            polyphony[wi] = {
                "secondary_chain_id": idx,
                "secondary_strength": sc["strength"],
                "syllable_idx": cand["syllable_idx"],
                "syllable_count": cand["syllable_count"],
            }

    for idx, sc in enumerate(secondary_chains):
        sc["chain_id"] = idx

    return secondary_chains, polyphony


# ============================================================================
# Rhyme-graph / strength / stress additions — integrating the "201-210"
# compositional calculus framework (decomposition/composition/aggregation/
# segmentation/clustering/layering/nesting/embedding/weaving/fusion) as a
# formal vocabulary for what this engine already does, plus three genuinely
# new outputs the framework's ontology calls for that weren't here before:
# a proper rhyme GRAPH (not just flat chains), a continuous rhyme STRENGTH
# score alongside the discrete tiers, and per-line STRESS PATTERN strings.
# See docs/RHYME_GRAPH_FRAMEWORK.md for the full mapping and rationale.
# ============================================================================

def stress_pattern_string(words, line_idx):
    """Builds an 'S u S u' style stress-pattern string for one line, using
    the same primary-stress flags segment_syllables() already computes —
    this just surfaces them as the Stress Representation the framework
    calls for, rather than leaving stress implicit in anchor selection."""
    marks = []
    for w in words:
        if w["line_idx"] != line_idx:
            continue
        for syl in w["syllables"]:
            marks.append("S" if syl["stressed"] else "u")
    return " ".join(marks)


def word_bar_index(t, bpm, beats_per_bar=4, downbeat_offset=0.0):
    """Approximate bar index for a timestamp, given tempo. Uses a flat
    downbeat_offset (default 0 = assumes the first beat starts at t=0)
    rather than a real detected downbeat phase — pass downbeat_offset from
    tempo_meter.analyze()'s downbeat_phase for a precise version. Good
    enough for a cross-bar YES/NO flag; not precise enough for exact bar
    numbering without the real phase.
    """
    if not bpm:
        return None
    bar_seconds = bars_to_seconds(1, bpm, beats_per_bar)
    return int((t - downbeat_offset) // bar_seconds)


def rhyme_strength_score(tier, member_ts, lookahead_seconds):
    """Continuous rhyme-strength score (the ontology's weighted R = w1*V +
    w2*C + w3*S + w4*T + ... formula), as a supplement to — not a
    replacement for — the discrete tier system. Base value comes from the
    tier (the only phonetic-similarity signal already computed per pair);
    modulated by temporal proximity across the chain's members, since
    tighter, closer-together rhymes read as 'stronger' than the same tier
    spread thin across a long window. Returns 0..1.
    """
    tier_base = {"perfect": 1.0, "slant": 0.75, "assonance": 0.55, "consonance": 0.4}.get(tier, 0.4)
    if len(member_ts) < 2 or lookahead_seconds <= 0:
        return round(tier_base, 3)
    gaps = [b - a for a, b in zip(member_ts, member_ts[1:])]
    avg_gap = sum(gaps) / len(gaps)
    proximity = max(0.0, 1.0 - (avg_gap / lookahead_seconds))
    score = tier_base * (0.7 + 0.3 * proximity)  # proximity nudges, doesn't dominate
    return round(min(1.0, score), 3)


def build_rhyme_graph(all_chains, secondary_chains, vowel_runs):
    """Renders the chain-based detection output as an explicit node/edge
    graph — 'rhyme_scheme = graph, not string' from the framework. Additive:
    doesn't replace the chain-based output annotate_lines() already
    returns, just re-expresses it in graph form for callers that want it
    (e.g. a future rhyme-relation visualization distinct from the
    line-by-line colored view).

    Nodes are word indices actually involved in some rhyme relation.
    Edges connect consecutive members within a chain (primary or
    secondary/polyphonic) or a vowel run, typed accordingly, carrying the
    tier and continuous strength score.
    """
    nodes = set()
    edges = []

    for c in all_chains:
        ts = [cand["t"] for cand in c["candidates"]]
        score = rhyme_strength_score(c["strength"], ts, ts[-1] - ts[0] + 1 if len(ts) > 1 else 1)
        ordered = sorted(c["candidates"], key=lambda cand: cand["t"])
        for a, b in zip(ordered, ordered[1:]):
            nodes.add(a["word_end"]); nodes.add(b["word_end"])
            edges.append({
                "source": a["word_end"], "target": b["word_end"],
                "type": "cross_word_rhyme" if (a["word_start"] != a["word_end"] or b["word_start"] != b["word_end"]) else "rhyme",
                "tier": c["strength"], "strength_score": score,
                "unit_size": c["k"], "chain_id": c["chain_id"],
            })

    for sc in secondary_chains:
        ts = [cand["t"] for cand in sc["candidates"]]
        score = rhyme_strength_score(sc["strength"], ts, ts[-1] - ts[0] + 1 if len(ts) > 1 else 1)
        ordered = sorted(sc["candidates"], key=lambda cand: cand["t"])
        for a, b in zip(ordered, ordered[1:]):
            nodes.add(a["word_start"]); nodes.add(b["word_start"])
            edges.append({
                "source": a["word_start"], "target": b["word_start"],
                "type": "polyphonic_rhyme", "tier": sc["strength"],
                "strength_score": score, "chain_id": sc["chain_id"],
            })

    for run_idx, run in enumerate(vowel_runs):
        ordered = sorted(run["members"], key=lambda cand: cand["t"])
        for a, b in zip(ordered, ordered[1:]):
            nodes.add(a["word_end"]); nodes.add(b["word_end"])
            edges.append({
                "source": a["word_end"], "target": b["word_end"],
                "type": "vowel_run", "run_id": run_idx,
            })

    return {"nodes": sorted(nodes), "edges": edges}


def build_chains(lines, bpm=None, bars_lookahead=8, lookahead_seconds=None,
                  min_tier="perfect", max_k=3, polyphony_min_tier="slant"):
    """
    NOTE (v0 known limitation, carried over from v0.1): union-find is
    single-linkage clustering — one weak pairwise match can fuse two
    otherwise-unrelated chains into a giant blob. Verified in testing:
    min_tier="perfect" stays clean; "slant"/"assonance" cascade badly.
    Do not lower min_tier below "perfect" until this is replaced with
    clique-based or centroid clustering (still a v1 task).

    Multisyllabic + cross-word handling (new in v0.2): candidates are
    generated for K=max_k..1 syllables ending at each stressed, end-of-word
    syllable. Larger K is resolved FIRST and claims its end-positions, so a
    3-syllable chain takes priority over the 2-syllable and 1-syllable
    sub-tails of the same words — matching the ontology's Unit Size axis
    (prefer the most specific/longest matching unit, not the shortest).
    A candidate whose word_start != word_end is a Cross-Word Chain: the
    rhyme unit spans a word boundary, exactly the pattern seen in the DOOM
    reference where two consecutive words share one highlight color.

    RESOLVED (v0.5) — BPM-adaptive window: the lookahead window is now
    TIME-based, not a fixed word count. Pass either:
    - bpm (+ optional bars_lookahead, default 8 bars) to derive the window
      from actual tempo via bars_to_seconds(), or
    - lookahead_seconds directly if you already know the window you want.
    If neither is given, falls back to a default of 90 BPM / 8 bars — a
    reasonable boom-bap-range assumption, not a substitute for actually
    detecting tempo (use estimate_bpm() on the track's audio when possible).
    """
    if lookahead_seconds is None:
        lookahead_seconds = bars_to_seconds(bars_lookahead, bpm or 90)

    words = build_word_index(lines)
    stream = build_syllable_stream(words)
    candidates_by_k, internal_candidates = gather_candidates(
        words, stream, max_k=max_k, lookahead_words=None)

    claimed_positions = set()
    all_chains = []  # each: {members: [candidate dicts], strength, k}

    for k in range(max_k, 0, -1):
        cands = [c for c in candidates_by_k[k] if c["stream_pos"] not in claimed_positions]
        if len(cands) < 2:
            continue
        raw_chains = cluster_candidates(cands, lookahead_seconds, min_tier)
        for rc in raw_chains:
            member_cands = [cands[i] for i in rc["members"]]
            for c in member_cands:
                claimed_positions.add(c["stream_pos"])
            all_chains.append({
                "k": k, "strength": rc["strength"], "candidates": member_cands,
            })

    # order by first appearance (earliest word_start) for deterministic color cycling
    all_chains.sort(key=lambda c: min(m["word_start"] for m in c["candidates"]))
    for idx, c in enumerate(all_chains):
        c["chain_id"] = idx
        c["color"] = PALETTE[idx % len(PALETTE)]

    # word_idx -> chain assignment info (a word can be the END of at most
    # one chain's anchor; if it's mid-span of a cross-word candidate it also
    # gets tagged so the renderer can highlight the whole span)
    word_tag = {}
    for c in all_chains:
        # cross-bar flag: does this chain span a bar boundary anywhere,
        # per the framework's Cross-Bar Rhyme concept? Only computed when
        # bpm is known (word_bar_index returns None otherwise, so every
        # comparison is skipped and cross_bar stays False — never guessed).
        ordered = sorted(c["candidates"], key=lambda cd: cd["t"])
        bar_idxs = [word_bar_index(cd["t"], bpm) for cd in ordered]
        chain_cross_bar = bpm is not None and len(set(b for b in bar_idxs if b is not None)) > 1
        for cand in c["candidates"]:
            span_words = list(range(cand["word_start"], cand["word_end"] + 1))
            for wi in span_words:
                word_tag[wi] = {
                    "chain_id": c["chain_id"], "color": c["color"],
                    "strength": c["strength"], "unit_size": c["k"],
                    "cross_word": cand["word_start"] != cand["word_end"],
                    "cross_bar": chain_cross_bar,
                    "span": span_words,
                }

    secondary_chains, polyphony = find_polyphony(
        words, internal_candidates, word_tag, lookahead_seconds, polyphony_min_tier)
    for wi, p in polyphony.items():
        sc = secondary_chains[p["secondary_chain_id"]]
        word_tag[wi]["polyphonic"] = True
        word_tag[wi]["secondary_chain_id"] = sc["chain_id"]
        word_tag[wi]["secondary_color"] = PALETTE[
            (len(all_chains) + sc["chain_id"]) % len(PALETTE)]
        word_tag[wi]["secondary_strength"] = p["secondary_strength"]
        # approximate split point: proportional to syllable index, since
        # phones don't map 1:1 to letters (documented limitation)
        frac = p["syllable_idx"] / max(1, p["syllable_count"])
        word_tag[wi]["split_fraction"] = round(frac, 2)

    # Mora-methodology cross-pollination: tag words involved in a detected
    # vowel run, independent of their primary-chain membership. See
    # find_vowel_runs() docstring for why this runs as a separate pass.
    vowel_runs = find_vowel_runs(candidates_by_k, lookahead_seconds)
    for run_idx, run in enumerate(vowel_runs):
        for cand in run["members"]:
            for wi in range(cand["word_start"], cand["word_end"] + 1):
                word_tag.setdefault(wi, {"chain_id": None})
                word_tag[wi].setdefault("vowel_runs", [])
                word_tag[wi]["vowel_runs"].append({
                    "run_id": run_idx, "vowel_seq": "".join(run["vowels"]),
                    "run_size": len(run["members"]),
                })

    return words, all_chains, word_tag, secondary_chains, vowel_runs


def annotate_lines(lines, bpm=None, bars_lookahead=8, lookahead_seconds=None,
                    min_tier="perfect", max_k=3, polyphony_min_tier="slant"):
    words, chains, word_tag, secondary_chains, vowel_runs = build_chains(
        lines, bpm=bpm, bars_lookahead=bars_lookahead,
        lookahead_seconds=lookahead_seconds, min_tier=min_tier, max_k=max_k,
        polyphony_min_tier=polyphony_min_tier)

    out_lines = []
    wi = 0
    for li, line in enumerate(lines):
        line_words = re.findall(r"[A-Za-z']+", line["text"])
        tagged = []
        rhyming = 0
        for local_i, w in enumerate(line_words):
            tag = word_tag.get(wi)
            has_primary = bool(tag) and tag.get("chain_id") is not None
            entry = {"word": w, "chain": tag["chain_id"] if tag else None}
            if has_primary:
                rhyming += 1
                entry.update({
                    "color": tag["color"], "strength": tag["strength"],
                    "unit_size": tag["unit_size"], "cross_word": tag["cross_word"],
                    "cross_bar": tag.get("cross_bar", False),
                    "position": "end" if local_i == len(line_words) - 1 else "internal",
                })
                if tag.get("polyphonic"):
                    entry.update({
                        "polyphonic": True,
                        "secondary_chain": tag["secondary_chain_id"],
                        "secondary_color": tag["secondary_color"],
                        "secondary_strength": tag["secondary_strength"],
                        "split_fraction": tag["split_fraction"],
                    })
            if tag and tag.get("vowel_runs"):
                entry["vowel_runs"] = tag["vowel_runs"]
            tagged.append(entry)
            wi += 1
        density = round(rhyming / len(line_words), 2) if line_words else 0.0
        out_lines.append({"start": line["start"], "end": line["end"],
                           "words": tagged, "density": density,
                           "stress_pattern": stress_pattern_string(words, li)})

    chain_directory = []
    for c in chains:
        ts = sorted(cand["t"] for cand in c["candidates"])
        span = (ts[-1] - ts[0]) if len(ts) > 1 else 1
        chain_directory.append({
            "chain_id": c["chain_id"], "color": c["color"], "strength": c["strength"],
            "unit_size": c["k"], "size": len(c["candidates"]),
            "cross_word_count": sum(1 for cand in c["candidates"] if cand["word_start"] != cand["word_end"]),
            "cross_bar": bpm is not None and len(set(
                b for b in (word_bar_index(t, bpm) for t in ts) if b is not None)) > 1,
            "strength_score": rhyme_strength_score(c["strength"], ts, max(span, 1)),
        })
    secondary_directory = [
        {"chain_id": sc["chain_id"], "strength": sc["strength"], "size": len(sc["candidates"])}
        for sc in secondary_chains
    ]
    polyphonic_word_count = sum(1 for l in out_lines for w in l["words"] if w.get("polyphonic"))
    vowel_run_directory = [
        {"run_id": idx, "vowel_seq": "".join(r["vowels"]), "size": len(r["members"])}
        for idx, r in enumerate(vowel_runs)
    ]
    return {"lines": out_lines, "chains": chain_directory,
            "secondary_chains": secondary_directory,
            "polyphonic_word_count": polyphonic_word_count,
            "vowel_runs": vowel_run_directory,
            "rhyme_graph": build_rhyme_graph(chains, secondary_chains, vowel_runs)}


if __name__ == "__main__":
    import sys
    with open(sys.argv[1]) as f:
        lines = json.load(f)
    bpm_arg = float(sys.argv[2]) if len(sys.argv) > 2 else None
    result = annotate_lines(lines, bpm=bpm_arg)
    print(json.dumps(result, indent=2))
