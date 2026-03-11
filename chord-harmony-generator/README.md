# Chord Harmony Generator

This is a small Python application that:

- **Takes a chord progression as text input**
- **Generates 4-part (or more-part) harmony** that
  - respects the requested chords
  - keeps each voice in a comfortable range
  - prefers stepwise motion
  - avoids large leaps and voice crossings
  - penalizes parallel 5ths/8ves (basic classical-style voice-leading)

The core logic is in `harmony.py` and uses a simple search that chooses, for each chord, the voicing that minimizes a voice-leading cost from the previous chord.

> This is **not** a complete chorale-style engine, but a practical starting point that you can tune and extend.

## Installation (with helper script)

From `chord-harmony-generator`, you can use the provided Windows setup script:

```bash
setup_harmony_app.bat
```

This will:

- create a virtual environment in `.venv` (if it does not exist)
- activate it
- install required Python packages from `requirements.txt`

If you prefer to do it manually:

```bash
cd chord-harmony-generator
python -m venv .venv
.\.venv\Scripts\activate  # on Windows
```

Then install dependencies:

```bash
pip install -r requirements.txt
```

## CLI Usage

Run the CLI:

```bash
python main.py
```

You will be prompted for:

- **Number of voices** (e.g. `4` for SATB)
- **Chord progression**, e.g.:

```text
Cmaj | Fmaj | G7 | Cmaj
```

or:

```text
Am | Dm | G | C
```

The program prints a simple text representation of each voice over the progression. If `music21` is installed (from `requirements.txt`), it can also write a MIDI file named `output.mid` in the same folder.

## Web UI Usage

There is also a small web interface built with Flask.

1. Ensure the environment is set up (run `setup_harmony_app.bat` once).
2. Launch the web UI:

```bash
launch_harmony_web.bat
```

3. Open your browser and go to `http://127.0.0.1:5001/` if it does not open automatically.

You will see:

- **Number of voices** input (4–6)
- **Chord progression** text area
- A **Generate Harmony** button that computes and displays:
  - the chord sequence
  - each voice (highest to lowest) as note names in a table
- If `music21` is available, a **Download MIDI** link for `output.mid`.

## Chord notation

**Roots** (case-insensitive, with sharps/flats):

`C C# Db D D# Eb E F F# Gb G G# Ab A A# Bb B`

**Common qualities / symbols supported** (not exhaustive, but broad):

- **Major triad**: `C`, `Cmaj`, `CM`, `Cma`
- **Minor triad**: `Cm`, `Cmin`, `Cmi`, `C-`
- **Diminished triad**: `Cdim`, `Co`
- **Augmented triad**: `Caug`, `C+`
- **6 chords**: `C6`, `Cmaj6`, `CM6`, `C69`, `C6/9`
- **Dominant 7th and extensions**:
  - `C7`, `C9`, `C11`, `C13`
  - basic altered 9ths like `C7b9`, `C7#9`
- **Major 7th**: `Cmaj7`, `CΔ7`, `CΔ`, `CM7`
- **Minor 7th and extensions**: `Cm7`, `Cmin7`, `C-7`, `Cm9`, `Cm11`, `Cm13`
- **Half-diminished**: `Cm7b5`, `Cø7`, `Cø`
- **Fully diminished 7th**: `Cdim7`, `Co7`
- **Suspended chords**: `Csus2`, `Csus4`, `Csus`, `C7sus4`
- **Add chords**: `Cadd2`, `Cadd9`, `Cadd4`, `Cadd11`, `Cadd6`

For most extended chords (9, 11, 13, etc.) the app includes the root, 3rd (or suspended tone), 5th, 7th, and the named extensions as pitch classes. It then chooses voicings that fit within the given voice ranges.

**Inversions / slash chords**

- You can specify an explicit bass note using a slash:
  - `C/E`, `C/G`, `Am/C`, `D7/F#`, `G/B`, etc.
- The harmony generator will ensure the **lowest voice matches the slash bass** when possible.

## How the harmony is generated

Very briefly:

- Each chord symbol is converted into a set of pitch classes.
- For each chord, we generate many candidate voicings in closed or slightly open position, in reasonable ranges (for 4–6 voices).
- We compute a **cost** from the previous chord's voicing to each candidate using basic voice-leading and counterpoint-style rules; the path with the lowest total cost is chosen (dynamic programming / Viterbi-style).

### Voice-leading rules (costs in `harmony.py`)

| Rule | Effect |
|------|--------|
| **Stepwise motion** | Small steps (1–2 semitones) preferred; large leaps penalized. |
| **Parallel 5ths and octaves** | Any two voices moving in parallel P5 or P8 (or unison) get a strong penalty (all voice pairs checked). |
| **Direct (hidden) 5ths/8ves** | Bass and soprano moving in the same direction into a P5 or P8 are penalized. |
| **Voice crossing** | Two voices swapping order between chords (e.g. alto drops below tenor) is penalized. |
| **Contrary motion** | Outer voices (bass and soprano) moving in opposite directions get a small bonus. |
| **Spacing** | Very tight or very wide chord spread, and gaps > octave between adjacent voices, are penalized. |
| **Doubling** | Voicing generator allows at most one of each non-root chord tone and at most two roots. |
| **Omission** | When there are more chord tones than voices (e.g. G9 with 4 voices), the **5th is omitted first**, then 9th, 11th, 13th, so that root, 3rd, and 7th (and 9th when possible) are kept. |

Tendency-tone resolution (e.g. 7th of V7 resolving down, leading tone up) and style-specific doubling (e.g. prefer doubling root/5th over 3rd) are not modeled.

**Adjusting weights and ranges:** In the web UI, open the **"Weights & ranges"** section to change voice-leading costs and pitch range (e.g. parallel 5ths/8ves penalty, stepwise preference, range low/high, max chord spread) without editing code. On first load the form shows defaults; after generating, it shows the values that were used.

## Next ideas / extensions

- Add support for inversions (e.g. `C/E`, `G/B`).
- Add rhythmic patterns (currently each chord is treated with one “slot” of harmony).
- Export MusicXML or LilyPond for engraving.
- Add a simple GUI (Tkinter, Qt, or web front-end).

