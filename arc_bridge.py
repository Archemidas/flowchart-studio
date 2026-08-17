"""
arc_bridge.py — Duckdown Records / Flow Chart

Bridges flowchart_engine.py's real detection output (from actual catalog
lines) into rhymekit.py's cue-sheet schema (Artifact B shape), so
rhymekit.render() can produce the arc-diagram "pseudoknot lane view" —
the genuinely new visualization from the rhyme-scheme architecture spec —
directly from data our own engine already produces, not just from the
spec's illustrative pastiche example.

This is the concrete "Studio can lead from this example" deliverable:
real track -> flowchart_engine.annotate_lines() -> this bridge ->
rhymekit's schema -> rhymekit.render() -> SVG arc diagram.

Scope note: this is a server-side/Python capability today, not yet wired
into the browser Studio (which is JS). Porting rhymekit's renderer to
JS for an in-browser "Arc Diagram" export button is a real, scoped
follow-up — not attempted in this pass. See docs/ARC_DIAGRAM_ARCHITECTURE.md.
"""

import re
import colorsys
import flowchart_engine as fe
import rhymekit as rk

# flowchart_engine tier names -> rhymekit tier names
TIER_MAP = {"perfect": "PERF", "slant": "FAM", "assonance": "ASSON", "consonance": "CONS"}


def _nucleus_vowel(tail):
    """First vowel phone in a tail (the syllable nucleus) — used to derive
    a rhymekit hue via its own embed() function, keeping 'hue = phonetic
    family' (the spec's Methodological Spine item 3) rather than reusing
    flowchart_engine's own index-cycled PALETTE."""
    for p in tail:
        if p in fe.VOWELS:
            return p if p in rk.VOW else "IH"  # rk.VOW only covers a subset; fall back
    return "IH"


def _family_hue_variant(nuc, variant_index):
    """rhymekit.embed() maps only ~12 vowels to hues, but a real song can
    (and does — 21 chains from 12 vowels on Two Turntables & A Mic alone)
    have more rhyme groups than there are vowel families. render()'s own
    QA invariant demands a unique hue per group, so pure family-based
    color collides on real multi-chain tracks — a real scaling gap in the
    spec's small-example design, not something to paper over silently.
    Fix: keep the same base hue (still 'hue = phonetic family') but vary
    lightness/saturation deterministically per chain sharing that family,
    so groups in the same vowel family read as a family (similar hue)
    while staying individually distinguishable — same principle the spec
    itself already uses for tier-based stroke width, just extended to
    hue when family alone can't carry enough distinct colors."""
    h, b = rk.VOW.get(nuc, ("MID", "CENT"))
    base_hue = (190 - 70 * rk.BI[b] + 15 * rk.HI[h]) % 360
    # Small hue nudge (stays visually "in the family") plus lightness
    # banding — two knobs instead of one gives enough distinct
    # combinations for any real song's chain count without hue drifting
    # into a different vowel family's territory (+/-18deg max).
    hue = (base_hue + (variant_index % 5 - 2) * 9) % 360
    lightness = max(0.32, min(0.82, 0.72 - 0.12 * rk.HI[h] - 0.07 * (variant_index // 5)))
    r, g, bl = colorsys.hls_to_rgb(hue / 360, lightness, 0.85)
    return "#%02X%02X%02X" % (int(r * 255), int(g * 255), int(bl * 255))


def build_cue_sheet(lines, bpm=None, bars_lookahead=8, min_tier="perfect", max_k=3):
    """Runs the real engine on `lines` ({start,end,text} dicts, same input
    shape as annotate_lines) and returns a rhymekit-schema dict."""
    result = fe.annotate_lines(lines, bpm=bpm, bars_lookahead=bars_lookahead, min_tier=min_tier, max_k=max_k)

    # Rebuild the internal candidate structures once more (annotate_lines
    # doesn't expose word_start/word_end/tail directly in its public
    # output) so the bridge has what it needs for sites/arcs — this is the
    # one place the bridge reaches past the public API into build_chains.
    words, all_chains, word_tag, secondary_chains, vowel_runs = fe.build_chains(
        lines, bpm=bpm, bars_lookahead=bars_lookahead, min_tier=min_tier, max_k=max_k)

    rk_lines = []
    for li, line in enumerate(lines):
        rk_lines.append({
            "id": f"L{li}", "text": line["text"], "t0": line["start"], "t1": line["end"],
            "phrase": f"P{li // 2}",  # approximate 2-line phrase grouping; no real phrase-boundary data yet
        })

    sites = {}
    for c in all_chains:
        for cand in c["candidates"]:
            for wi in range(cand["word_start"], cand["word_end"] + 1):
                w = words[wi]
                sid = f"s{wi}"
                sites[sid] = {
                    "id": sid, "voice": "v0",
                    "chunk": w["text"],
                    "layer": "SPINE" if wi == cand["word_end"] and cand["word_end"] == cand["word_start"] else "LOCAL",
                    "tier": TIER_MAP.get(c["strength"], "FAM"),
                    "t0": w["t"], "t1": w["t"] + 0.3,
                    "latent": False,
                }

    groups = []
    palette = {}
    used_colors = set()
    family_counts = {}
    for c in all_chains:
        gid = f"g{c['chain_id']}"
        member_ids = sorted({f"s{wi}" for cand in c["candidates"] for wi in range(cand["word_start"], cand["word_end"] + 1)})
        groups.append({
            "id": gid, "tier": TIER_MAP.get(c["strength"], "FAM"),
            "layer": "LOCAL", "members": member_ids,
        })
        nuc = _nucleus_vowel(c["candidates"][0]["tail"])
        variant = family_counts.get(nuc, 0)
        family_counts[nuc] = variant + 1
        color = _family_hue_variant(nuc, variant)
        # Deterministic dedup: two different vowel families can still round
        # to the same integer RGB after HLS conversion (confirmed on real
        # data — 4 of 21 chains collided this way on Two Turntables & A
        # Mic even with the variant scheme above). render()'s hue-
        # injectivity QA check is a hard requirement, so guarantee it here
        # rather than hoping the color math never coincides.
        bump = 0
        while color in used_colors:
            bump += 1
            color = _family_hue_variant(nuc, variant + bump * 7)
        used_colors.add(color)
        palette[gid] = color

    # rhymekit's render() looks up hue via GROUP_FAMILY -> palette[family],
    # not palette[group_id] directly. Simplest correct bridge: monkeypatch
    # a per-track GROUP_FAMILY so each of OUR chain ids maps to itself,
    # and put the actual colors under those same keys in the palette.
    group_family = {g["id"]: g["id"] for g in groups}

    arcs = []
    for c in all_chains:
        ordered = sorted(c["candidates"], key=lambda cd: cd["t"])
        for a, b in zip(ordered, ordered[1:]):
            arcs.append({
                "g": f"g{c['chain_id']}", "a": f"s{a['word_end']}", "b": f"s{b['word_end']}",
                "cross": word_tag.get(a["word_end"], {}).get("cross_bar", False),
                "span_bars": 0,
            })

    phrases = []
    for pid in sorted({l["phrase"] for l in rk_lines}, key=lambda p: int(p[1:])):
        member_lines = [l["id"] for l in rk_lines if l["phrase"] == pid]
        phrases.append({"id": pid, "lines": member_lines, "scheme": f"{pid}.auto"})

    doc = {
        "track": {"id": "flowchart-bridge", "bar_s": fe.bars_to_seconds(1, bpm or 90)},
        "voices": [{"id": "v0", "kind": "main"}],
        "lines": rk_lines,
        "sites": list(sites.values()),
        "groups": groups,
        "arcs": arcs,
        "phrases": phrases,
        "palette": palette,
    }
    return doc, group_family


def render_arc_diagram(lines, out_svg_path, bpm=None, **kwargs):
    """One-call convenience: real lines -> cue sheet -> SVG arc diagram."""
    doc, group_family = build_cue_sheet(lines, bpm=bpm, **kwargs)
    original_group_family = dict(rk.GROUP_FAMILY)
    rk.GROUP_FAMILY.clear()
    rk.GROUP_FAMILY.update(group_family)
    try:
        rk.render(doc, out_svg_path)
    finally:
        rk.GROUP_FAMILY.clear()
        rk.GROUP_FAMILY.update(original_group_family)
    return doc


if __name__ == "__main__":
    import sys, json
    with open(sys.argv[1]) as f:
        lines = json.load(f)
    bpm = float(sys.argv[3]) if len(sys.argv) > 3 else None
    render_arc_diagram(lines, sys.argv[2], bpm=bpm)
