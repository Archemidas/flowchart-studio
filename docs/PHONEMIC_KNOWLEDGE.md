# Flow Chart — Phonemic Knowledge Store

This is the "interlinked knowledge store" for pronunciation and rhyme-tier
knowledge: a small set of structured data files plus this document tying
them to the terms defined in `docs/ONTOLOGY.md` and the pipeline in
`docs/LOGIC.md`. It is deterministic reference data (dictionaries and
taxonomy), not model weights — nothing here is a fine-tuned model, and
nothing here is derived from third-party lyric content. See the "Sourcing"
section at the bottom for exactly what is and isn't in scope.

## 1. IPA support

`arpabet_to_ipa()` (Python, `flowchart_engine.py`) and `arpabetToIpa()` /
`wordToIpa()` (JS, `cmu_engine.js`) convert a CMU-style ARPAbet phone list
into a real IPA (International Phonetic Alphabet) transcription, with
stress marks (ˈ primary, ˌ secondary) placed before the stressed vowel.
This is a standard, public linguistic mapping (the same one used in CMU
dictionary documentation and Wiktionary pronunciation entries) — it adds
zero content of its own, it's a notation conversion.

Examples (plain dictionary words, chosen purely to demonstrate the
mapping):

| Word | ARPAbet | IPA |
|---|---|---|
| cat | K AE1 T | kˈæt |
| hat | HH AE1 T | hˈæt |
| rhythm | R IH1 DH AH0 M | ɹˈɪðəm |

## 2. Rhyme tier taxonomy, illustrated in IPA

The four tiers from `docs/ONTOLOGY.md` §2 (Strength), shown with generic
dictionary-word examples — not song lyrics — so the taxonomy has a
concrete phonemic referent independent of any specific track:

| Tier | Definition | Example pair | IPA |
|---|---|---|---|
| Perfect | Identical phones from the stressed vowel onward | cat / hat | kˈæt / hˈæt |
| Slant | Same length, exactly one phone differs | cat / cap | kˈæt / kˈæp |
| Assonance | Vowel sequence matches, consonants differ | cat / bag | kˈæt / bˈæɡ |
| Consonance | Final consonant matches, vowel differs | cat / hot | kˈæt / hˈɑt |

This table is what `compare_tails()` / `compareTails()` actually
implement — see `docs/LOGIC.md` step 6 for the clustering logic that
consumes these tier judgments.

## 3. Custom pronunciation dictionary

`custom_pronunciations.txt` (repo root, same "WORD PH ON ES" format as
`cmudict.txt`) extends the CMU dictionary with individual word
pronunciations for slang/ad-libs/contractions that the standard
dictionary doesn't cover — sourced ONLY from words that actually occur in
Duckdown's own catalog (Two Turntables & A Mic, Who Got Da Props), not
from any third-party material. Both `flowchart_engine.py` (server) and
`cmu_engine.js` (Studio, browser) load this file and merge it into the
same CMU lookup structure, overriding the dictionary for these specific
words — one shared pronunciation source, not two silos.

| Word | ARPAbet | IPA | Confidence |
|---|---|---|---|
| BCC | B IY1 S IY1 S IY1 | bˈisˈisˈi | Confirmed — initialism, spoken as three letter-names |
| BLOWIN' | B L OW1 IH0 N | blˈoʊən | Confirmed — standard "-in'" dropped-g contraction |
| CUZ | K AH1 Z | kˈʌz | Confirmed — standard "because" contraction |
| DISSED | D IH1 S T | dˈɪst | Confirmed — past tense of "diss" |
| GON' | G AO1 N | ɡˈɔn | Confirmed — standard "going to" contraction |
| I'MA | AY1 M AH0 | ˈaɪmə | Confirmed — standard "I'm going to" contraction |
| NAPPY | N AE1 P IY0 | nˈæpi | Confirmed — standard dictionary word, just missing from base CMU list |
| NIGGA | N IH1 G AH0 | nˈɪɡə | Confirmed pronunciation, included for phonemic completeness of the catalog's actual vocabulary |
| PAPPY | P AE1 P IY0 | pˈæpi | Confirmed — standard dictionary word, just missing from base CMU list |
| VIPI | — | — | **Unconfirmed** — surfaced from an auto-transcribed line in Who Got Da Props; likely a transcription artifact (name or mishearing). Deliberately left out of the pronunciation file rather than guessed. Needs the artist's confirmation of the actual word before adding an entry. |

Adding a new entry: append a line to `custom_pronunciations.txt` in the
same format, and add a row to the table above with its confidence level.
Log the addition in `docs/LEARNING_LOG.md` per the standing convention —
this file's job is data, the log's job is the "why" and "when."

## 4. Sourcing (what is and isn't in here)

**In scope**: individual word pronunciations from Duckdown's own catalog;
the public ARPAbet-IPA mapping convention; generic dictionary words used
to illustrate the rhyme-tier taxonomy.

**Not in scope, and not planned**: extracting on-screen lyric text from
third-party reference videos (via OCR or any other method) to populate
this store. That would mean capturing and storing another artist's
copyrighted lyric text, which doesn't become permitted by relabeling the
destination "a knowledge store" or the purpose "training." Reference
videos can still be studied structurally for rhyme-scheme *methodology*
(notation conventions, detection techniques) the same way earlier
reference material informed this ontology and the Vowel Run detection
pass — see `docs/ONTOLOGY.md` §8 for that precedent — but no lyric text
from those videos gets captured or stored anywhere in this system.
