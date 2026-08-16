/* ============================================================================
   Flow Chart — CMU Dictionary Phonemic Engine (JS port)
   Faithful port of flowchart_engine.py's real detection pipeline (CMU
   Pronouncing Dictionary phonemic transcription, primary-stress anchors,
   multisyllabic/cross-word candidates, complete-linkage clustering,
   BPM-adaptive time windowing, Compound Split/polyphony, cross-language
   Vowel Runs) — running client-side in the browser instead of the earlier
   spelling-based heuristic. Same tiers, same clustering algorithm, same
   window math as the server-side engine, so Studio's live preview and the
   Python engine agree on the same input instead of approximating it.

   Data dependency: cmudict.txt (plain text, one entry per line: "WORD PH
   ON ES", first pronunciation only, ~125k entries, exported directly from
   the same `cmudict` package flowchart_engine.py uses) must be reachable
   at the path passed to loadCmuDict(). Plain text rather than JSON purely
   to keep the file small and push-friendly (no per-entry quote/escaping
   overhead).
   ============================================================================ */

export const PALETTE = ["#e8a13c", "#5fb3a3", "#e0524a", "#8a7fd6", "#4aa3e0",
  "#d4af37", "#6fbf73", "#e07bb0", "#c98a4b", "#7a9fd6"];

const VOWELS = new Set(["AA","AE","AH","AO","AW","AY","EH","ER","EY","IH","IY","OW","OY","UH","UW"]);

/* ============================================================================
   IPA (International Phonetic Alphabet) support
   ARPAbet -> IPA is a standard, public linguistic mapping (used by CMU dict
   docs, Wiktionary, etc.) — not derived from any lyric content. Lets the
   engine show a real phonemic transcription for any word (dictionary or
   custom-pronunciation), independent of rhyme detection.
   ============================================================================ */
const ARPABET_TO_IPA = {
  AA: "ɑ", AE: "æ", AH: "ʌ", AO: "ɔ", AW: "aʊ", AY: "aɪ",
  B: "b", CH: "tʃ", D: "d", DH: "ð", EH: "ɛ", ER: "ɝ", EY: "eɪ",
  F: "f", G: "ɡ", HH: "h", IH: "ɪ", IY: "i", JH: "dʒ", K: "k",
  L: "l", M: "m", N: "n", NG: "ŋ", OW: "oʊ", OY: "ɔɪ", P: "p",
  R: "ɹ", S: "s", SH: "ʃ", T: "t", TH: "θ", UH: "ʊ", UW: "u",
  V: "v", W: "w", Y: "j", Z: "z", ZH: "ʒ",
};
const SCHWA_REDUCIBLE = new Set(["AH", "IH"]); // unstressed(0) reduces toward a schwa-ish vowel in casual speech

/**
 * Converts a raw ARPAbet phone list (with stress digits, e.g. from CMU dict
 * or a custom pronunciation entry) into an IPA transcription string, with
 * primary/secondary stress marks (ˈ/ˌ) placed before the stressed vowel.
 * A display/documentation utility — independent of the rhyme-tier logic.
 */
export function arpabetToIpa(phones) {
  let out = '';
  for (const p of phones) {
    const stressMatch = p.match(/(\d)$/);
    const stress = stressMatch ? stressMatch[1] : null;
    const base = p.replace(/\d$/, '');
    if (stress === '1') out += 'ˈ';
    else if (stress === '2') out += 'ˌ';
    let ipa = ARPABET_TO_IPA[base] || base.toLowerCase();
    if (stress === '0' && SCHWA_REDUCIBLE.has(base)) ipa = 'ə';
    out += ipa;
  }
  return out;
}

/** Convenience: look up a word (CMU or custom dict) and return its IPA string, or null if unknown. */
export function wordToIpa(word) {
  const phones = CMU && CMU.get(word.toUpperCase());
  return phones ? arpabetToIpa(phones) : null;
}

const TIER_RANK = { perfect: 3, slant: 2, assonance: 1, consonance: 1 };

const STOPWORDS = new Set([
  "A","AN","AND","THE","TO","OF","IN","ON","IS","IT","I","YOU","WE","THAT",
  "THIS","FOR","WITH","AT","BUT","OR","SO","IF","AS","BE","MY","YOUR","HIS",
  "HER","ITS","OUR","THEIR","AM","ARE","WAS","WERE","DO","DOES","DID",
]);

let CMU = null; // Map<string, string[]> word -> phones (with stress digits)

function parseDictText(text, into) {
  const lines = text.split('\n');
  for (const line of lines) {
    if (!line) continue;
    const sp = line.indexOf(' ');
    if (sp === -1) continue;
    into.set(line.slice(0, sp), line.slice(sp + 1).split(' '));
  }
}

export async function loadCmuDict(url = 'cmudict.txt') {
  if (CMU) return CMU;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load CMU dictionary from ${url}: ${res.status}`);
  const text = await res.text();
  CMU = new Map();
  parseDictText(text, CMU);
  return CMU;
}

/**
 * Loads custom_pronunciations.txt (same "WORD PH ON ES" format as
 * cmudict.txt) and merges it into the live CMU map, OVERRIDING any CMU
 * entry for the same word. This is the pronunciation half of the
 * knowledge-store idea: individual word pronunciations — not lyric text —
 * for slang/ad-libs/proper nouns that don't exist in the standard
 * dictionary, sourced from Duckdown's own catalog. See
 * docs/PHONEMIC_KNOWLEDGE.md for what's in here and why, including which
 * entries are confirmed vs. best-guess. Call after loadCmuDict().
 */
export async function loadCustomPronunciations(url = 'custom_pronunciations.txt') {
  if (!CMU) throw new Error('Call loadCmuDict() before loadCustomPronunciations().');
  let res;
  try { res = await fetch(url); } catch { return false; }
  if (!res.ok) return false;
  const text = await res.text();
  const entries = new Map();
  parseDictText(text, entries);
  entries.forEach((phones, word) => CMU.set(word, phones));
  return entries.size;
}

export function isCmuDictLoaded() { return CMU !== null; }
export function cmuDictSize() { return CMU ? CMU.size : 0; }

function cleanWord(w) {
  return w.replace(/[^A-Za-z']/g, '').toUpperCase();
}

function getPhones(word) {
  return CMU.get(word) || null; // null => unknown word (proper noun/slang/ad-lib)
}

function stripStress(p) { return p.replace(/\d/g, ''); }

function segmentSyllables(phones) {
  const vowelIdxs = [];
  phones.forEach((p, i) => { if (VOWELS.has(stripStress(p))) vowelIdxs.push(i); });
  const syllables = [];
  vowelIdxs.forEach((v, k) => {
    const end = k + 1 < vowelIdxs.length ? vowelIdxs[k + 1] : phones.length;
    const syl = phones.slice(v, end);
    syllables.push({
      phones: syl.map(stripStress),
      stressed: syl[0].endsWith('1'),
    });
  });
  return syllables;
}

function vowelsOnly(tail) { return tail.filter(p => VOWELS.has(p)); }

function arrEq(a, b) { return a.length === b.length && a.every((x, i) => x === b[i]); }

function compareTails(a, b) {
  if (!a || !b || a.length === 0 || b.length === 0) return null;
  if (arrEq(a, b)) return 'perfect';
  if (a.length === b.length) {
    let diffs = 0;
    for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) diffs++;
    if (diffs === 1) return 'slant';
  }
  const va = vowelsOnly(a), vb = vowelsOnly(b);
  if (va.length && arrEq(va, vb)) return 'assonance';
  if (a[a.length - 1] === b[b.length - 1] && a[a.length - 1]) return 'consonance';
  return null;
}

export function barsToSeconds(bars, bpm, beatsPerBar = 4) {
  const secondsPerBeat = 60.0 / bpm;
  return bars * beatsPerBar * secondsPerBeat;
}

function buildWordIndex(lines) {
  const words = [];
  lines.forEach((line, li) => {
    const lineWords = line.text.match(/[A-Za-z']+/g) || [];
    const span = Math.max(0.001, line.end - line.start);
    const step = span / Math.max(1, lineWords.length);
    lineWords.forEach((w, wi) => {
      const cw = cleanWord(w);
      const isStop = STOPWORDS.has(cw);
      const phones = isStop ? null : getPhones(cw);
      const syllables = phones ? segmentSyllables(phones) : [];
      // "known" tracks whether the word was genuinely absent from the CMU
      // dictionary (proper noun/slang/ad-lib) vs. deliberately skipped
      // because it's a stopword — only the former should ever be reported
      // to the user as an "unknown word" diagnostic.
      words.push({ lineIdx: li, text: w, syllables, t: line.start + wi * step, known: isStop || !!phones, isStop });
    });
  });
  return words;
}

function buildSyllableStream(words) {
  const stream = [];
  words.forEach((w, wi) => {
    for (let si = 0; si < w.syllables.length; si++) stream.push([wi, si]);
  });
  return stream;
}

function gatherCandidates(words, stream, maxK = 3) {
  const candidatesByK = {}; for (let k = 1; k <= maxK; k++) candidatesByK[k] = [];
  const internalCandidates = [];

  stream.forEach(([wi, si], pos) => {
    const stressed = words[wi].syllables[si].stressed;
    const isLast = si === words[wi].syllables.length - 1;
    if (isLast) {
      if (!stressed) return;
      for (let k = 1; k <= maxK; k++) {
        const start = pos - k + 1;
        if (start < 0) continue;
        const span = stream.slice(start, pos + 1);
        let tail = [];
        span.forEach(([swi, ssi]) => { tail = tail.concat(words[swi].syllables[ssi].phones); });
        candidatesByK[k].push({
          streamPos: pos, tail,
          wordStart: span[0][0], wordEnd: span[span.length - 1][0],
          t: words[wi].t,
        });
      }
    } else if (stressed) {
      internalCandidates.push({
        streamPos: pos, tail: words[wi].syllables[si].phones,
        wordStart: wi, wordEnd: wi,
        syllableIdx: si, syllableCount: words[wi].syllables.length,
        t: words[wi].t,
      });
    }
  });

  return [candidatesByK, internalCandidates];
}

// Complete-linkage clustering — a candidate joins an existing cluster only
// if it meets min_tier against EVERY member already in it, not just one.
// (This is the fix for the v0.1 single-linkage blob bug — see LEARNING_LOG.)
function clusterCandidates(cands, lookaheadSeconds, minTier) {
  const tierRankMin = TIER_RANK[minTier];
  const clusters = []; // {members: [idx...], tiers: Map}

  cands.forEach((cand, i) => {
    let joined = false;
    for (const cluster of clusters) {
      const lastMember = cluster.members[cluster.members.length - 1];
      if (cand.t - cands[lastMember].t > lookaheadSeconds) continue;
      let ok = true;
      const pairwise = [];
      for (const m of cluster.members) {
        const tier = compareTails(cand.tail, cands[m].tail);
        if (!tier || TIER_RANK[tier] < tierRankMin) { ok = false; break; }
        pairwise.push([m, tier]);
      }
      if (ok) {
        cluster.members.push(i);
        pairwise.forEach(([m, t]) => cluster.tiers.set(`${m},${i}`, t));
        joined = true;
        break;
      }
    }
    if (!joined) clusters.push({ members: [i], tiers: new Map() });
  });

  const chains = [];
  for (const cluster of clusters) {
    if (cluster.members.length < 2) continue;
    let bestTier = 'consonance';
    for (const t of cluster.tiers.values()) {
      if (TIER_RANK[t] > TIER_RANK[bestTier]) bestTier = t;
    }
    chains.push({ members: [...cluster.members].sort((a, b) => a - b), strength: bestTier });
  }
  return chains;
}

function findVowelRuns(candidatesByK, lookaheadSeconds, minRunLength = 3) {
  const pool = [...(candidatesByK[2] || []), ...(candidatesByK[3] || [])];
  if (pool.length < 2) return [];

  const vowelSeq = tail => tail.filter(p => VOWELS.has(p));
  const clusters = [];
  for (const cand of pool) {
    const vs = vowelSeq(cand.tail);
    if (vs.length < minRunLength) continue;
    let joined = false;
    for (const cluster of clusters) {
      const last = cluster.members[cluster.members.length - 1];
      if (cand.t - last.t > lookaheadSeconds) continue;
      if (arrEq(cluster.vowels, vs)) { cluster.members.push(cand); joined = true; break; }
    }
    if (!joined) clusters.push({ vowels: vs, members: [cand] });
  }
  return clusters.filter(c => c.members.length >= 2);
}

function findPolyphony(internalCandidates, primaryWordTag, lookaheadSeconds, minTier) {
  if (internalCandidates.length < 2) return [[], {}];

  const rawChains = clusterCandidates(internalCandidates, lookaheadSeconds, minTier);
  const secondaryChains = rawChains.map(rc => ({
    strength: rc.strength,
    candidates: rc.members.map(i => internalCandidates[i]),
  }));
  secondaryChains.sort((a, b) => Math.min(...a.candidates.map(m => m.wordStart)) - Math.min(...b.candidates.map(m => m.wordStart)));

  const polyphony = {};
  secondaryChains.forEach((sc, idx) => {
    sc.candidates.forEach(cand => {
      const wi = cand.wordStart;
      if (!(wi in primaryWordTag)) return;
      if (wi in polyphony) return;
      polyphony[wi] = {
        secondaryChainId: idx, secondaryStrength: sc.strength,
        syllableIdx: cand.syllableIdx, syllableCount: cand.syllableCount,
      };
    });
  });
  secondaryChains.forEach((sc, idx) => { sc.chainId = idx; });
  return [secondaryChains, polyphony];
}

function buildChains(lines, { bpm = null, barsLookahead = 8, lookaheadSeconds = null,
  minTier = 'perfect', maxK = 3, polyphonyMinTier = 'slant' } = {}) {
  if (lookaheadSeconds == null) lookaheadSeconds = barsToSeconds(barsLookahead, bpm || 90);

  const words = buildWordIndex(lines);
  const stream = buildSyllableStream(words);
  const [candidatesByK, internalCandidates] = gatherCandidates(words, stream, maxK);

  const claimedPositions = new Set();
  const allChains = [];

  for (let k = maxK; k >= 1; k--) {
    const cands = candidatesByK[k].filter(c => !claimedPositions.has(c.streamPos));
    if (cands.length < 2) continue;
    const rawChains = clusterCandidates(cands, lookaheadSeconds, minTier);
    rawChains.forEach(rc => {
      const memberCands = rc.members.map(i => cands[i]);
      memberCands.forEach(c => claimedPositions.add(c.streamPos));
      allChains.push({ k, strength: rc.strength, candidates: memberCands });
    });
  }

  allChains.sort((a, b) => Math.min(...a.candidates.map(m => m.wordStart)) - Math.min(...b.candidates.map(m => m.wordStart)));
  allChains.forEach((c, idx) => { c.chainId = idx; c.color = PALETTE[idx % PALETTE.length]; });

  const wordTag = {};
  allChains.forEach(c => {
    c.candidates.forEach(cand => {
      const spanWords = [];
      for (let wi = cand.wordStart; wi <= cand.wordEnd; wi++) spanWords.push(wi);
      spanWords.forEach(wi => {
        wordTag[wi] = {
          chainId: c.chainId, color: c.color, strength: c.strength, unitSize: c.k,
          crossWord: cand.wordStart !== cand.wordEnd, span: spanWords,
        };
      });
    });
  });

  const [secondaryChains, polyphony] = findPolyphony(internalCandidates, wordTag, lookaheadSeconds, polyphonyMinTier);
  for (const wiStr in polyphony) {
    const wi = parseInt(wiStr, 10);
    const p = polyphony[wi];
    const sc = secondaryChains[p.secondaryChainId];
    wordTag[wi].polyphonic = true;
    wordTag[wi].secondaryChainId = sc.chainId;
    wordTag[wi].secondaryColor = PALETTE[(allChains.length + sc.chainId) % PALETTE.length];
    wordTag[wi].secondaryStrength = p.secondaryStrength;
    const frac = p.syllableIdx / Math.max(1, p.syllableCount);
    wordTag[wi].splitFraction = Math.round(frac * 100) / 100;
  }

  const vowelRuns = findVowelRuns(candidatesByK, lookaheadSeconds);
  vowelRuns.forEach((run, runIdx) => {
    run.members.forEach(cand => {
      for (let wi = cand.wordStart; wi <= cand.wordEnd; wi++) {
        if (!wordTag[wi]) wordTag[wi] = { chainId: null };
        if (!wordTag[wi].vowelRuns) wordTag[wi].vowelRuns = [];
        wordTag[wi].vowelRuns.push({ runId: runIdx, vowelSeq: run.vowels.join(''), runSize: run.members.length });
      }
    });
  });

  return { words, allChains, wordTag, secondaryChains, vowelRuns };
}

/**
 * Primary entry point — mirrors flowchart_engine.py's annotate_lines exactly.
 * @param {Array<{start:number,end:number,text:string}>} lines
 * @param {object} opts {bpm, barsLookahead, lookaheadSeconds, minTier, maxK, polyphonyMinTier}
 * @returns {object} {lines, chains, secondaryChains, polyphonicWordCount, vowelRuns, unknownWords}
 */
export function annotateLines(lines, opts = {}) {
  if (!CMU) throw new Error('CMU dictionary not loaded — call loadCmuDict() first.');
  const { words, allChains, wordTag, secondaryChains, vowelRuns } = buildChains(lines, opts);

  const outLines = [];
  const unknownWords = new Set();
  let wi = 0;
  lines.forEach((line, li) => {
    const lineWords = line.text.match(/[A-Za-z']+/g) || [];
    const tagged = [];
    let rhyming = 0;
    lineWords.forEach((w, localI) => {
      const tag = wordTag[wi];
      const hasPrimary = !!tag && tag.chainId != null;
      const entry = { word: w, chain: tag ? tag.chainId : null };
      if (hasPrimary) {
        rhyming++;
        Object.assign(entry, {
          color: tag.color, strength: tag.strength, unitSize: tag.unitSize,
          crossWord: tag.crossWord, position: localI === lineWords.length - 1 ? 'end' : 'internal',
        });
        if (tag.polyphonic) {
          Object.assign(entry, {
            polyphonic: true, secondaryChain: tag.secondaryChainId,
            secondaryColor: tag.secondaryColor, secondaryStrength: tag.secondaryStrength,
            splitFraction: tag.splitFraction,
          });
        }
      }
      if (tag && tag.vowelRuns) entry.vowelRuns = tag.vowelRuns;
      if (!words[wi] || !words[wi].known) unknownWords.add(cleanWord(w));
      tagged.push(entry);
      wi++;
    });
    const density = lineWords.length ? Math.round((rhyming / lineWords.length) * 100) / 100 : 0;
    outLines.push({ start: line.start, end: line.end, text: line.text, words: tagged, density });
  });

  const chainDirectory = allChains.map(c => ({
    chainId: c.chainId, color: c.color, strength: c.strength, unitSize: c.k,
    size: c.candidates.length,
    crossWordCount: c.candidates.filter(cand => cand.wordStart !== cand.wordEnd).length,
  }));
  const secondaryDirectory = secondaryChains.map(sc => ({ chainId: sc.chainId, strength: sc.strength, size: sc.candidates.length }));
  const polyphonicWordCount = outLines.reduce((acc, l) => acc + l.words.filter(w => w.polyphonic).length, 0);
  const vowelRunDirectory = vowelRuns.map((r, idx) => ({ runId: idx, vowelSeq: r.vowels.join(''), size: r.members.length }));

  return {
    lines: outLines, chains: chainDirectory, secondaryChains: secondaryDirectory,
    polyphonicWordCount, vowelRuns: vowelRunDirectory,
    unknownWords: [...unknownWords],
  };
}
