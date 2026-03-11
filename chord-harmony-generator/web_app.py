from __future__ import annotations

import json
from flask import Flask, request, redirect, url_for, render_template_string, send_file

from harmony import (
    parse_progression,
    generate_harmony,
    export_to_midi,
    default_weights,
    weights_from_form,
    get_chord_alternatives,
)

app = Flask(__name__)


INDEX_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Chord Harmony Generator</title>
    <style>
      body {
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        margin: 0;
        padding: 0;
        background: #0f172a;
        color: #e5e7eb;
      }
      .container {
        max-width: 900px;
        margin: 3rem auto;
        padding: 2rem;
        background: rgba(15, 23, 42, 0.9);
        border-radius: 1rem;
        box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.9);
        border: 1px solid rgba(148, 163, 184, 0.4);
      }
      h1 {
        margin-top: 0;
        font-size: 1.8rem;
        letter-spacing: 0.03em;
      }
      p.lead {
        color: #9ca3af;
        margin-top: 0.25rem;
        margin-bottom: 1.75rem;
      }
      label {
        display: block;
        font-weight: 600;
        margin-bottom: 0.35rem;
      }
      input[type="text"], input[type="number"], textarea {
        width: 100%;
        padding: 0.6rem 0.75rem;
        border-radius: 0.5rem;
        border: 1px solid #4b5563;
        background: #020617;
        color: #e5e7eb;
        font-size: 0.95rem;
        box-sizing: border-box;
      }
      input[type="text"]:focus, input[type="number"]:focus, textarea:focus {
        outline: none;
        border-color: #38bdf8;
        box-shadow: 0 0 0 1px #38bdf8;
      }
      textarea {
        resize: vertical;
        min-height: 3.5rem;
      }
      .field-group {
        margin-bottom: 1.25rem;
      }
      .hint {
        font-size: 0.8rem;
        color: #9ca3af;
        margin-top: 0.25rem;
      }
      .error {
        background: rgba(239, 68, 68, 0.08);
        border: 1px solid rgba(239, 68, 68, 0.7);
        color: #fecaca;
        padding: 0.75rem 1rem;
        border-radius: 0.75rem;
        margin-bottom: 1rem;
        font-size: 0.9rem;
      }
      .btn-row {
        display: flex;
        gap: 0.75rem;
        align-items: center;
        margin-top: 0.5rem;
      }
      button.primary {
        background: linear-gradient(135deg, #38bdf8, #6366f1);
        color: #0b1120;
        border: none;
        padding: 0.7rem 1.4rem;
        font-weight: 600;
        border-radius: 999px;
        cursor: pointer;
        font-size: 0.95rem;
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        box-shadow: 0 10px 25px -10px rgba(59, 130, 246, 0.7);
      }
      button.primary:hover {
        filter: brightness(1.05);
      }
      .results {
        margin-top: 2rem;
        padding-top: 1.5rem;
        border-top: 1px solid #1f2937;
      }
      .chords {
        font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        background: #020617;
        padding: 0.6rem 0.75rem;
        border-radius: 0.5rem;
        border: 1px solid #4b5563;
        font-size: 0.85rem;
        overflow-x: auto;
      }
      table.voices {
        width: 100%;
        border-collapse: collapse;
        margin-top: 1rem;
        font-size: 0.85rem;
      }
      table.voices th, table.voices td {
        border: 1px solid #1f2937;
        padding: 0.4rem 0.5rem;
        text-align: left;
        white-space: nowrap;
      }
      table.voices th {
        background: #020617;
        font-weight: 600;
      }
      table.voices tr:nth-child(even) td {
        background: rgba(15, 23, 42, 0.85);
      }
      .pill {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.78rem;
        padding: 0.25rem 0.55rem;
        border-radius: 999px;
        border: 1px solid #374151;
        background: rgba(15, 23, 42, 0.85);
        color: #9ca3af;
      }
      .pill strong {
        color: #e5e7eb;
      }
      .download {
        margin-top: 1rem;
      }
      .download a {
        color: #a5b4fc;
        text-decoration: none;
        font-size: 0.9rem;
      }
      .download a:hover {
        text-decoration: underline;
      }
      .visualizer {
        margin-top: 1rem;
        border-radius: 0.75rem;
        background: #020617;
        border: 1px solid #1f2937;
        padding: 0.75rem 0.9rem;
      }
      .voice-row {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin-bottom: 0.35rem;
      }
      .voice-label {
        font-size: 0.8rem;
        color: #9ca3af;
        width: 3rem;
      }
      .voice-track {
        display: flex;
        gap: 0.25rem;
        flex-wrap: nowrap;
        overflow-x: auto;
      }
      .note-box {
        min-width: 2.3rem;
        text-align: center;
        font-size: 0.78rem;
        padding: 0.25rem 0.3rem;
        border-radius: 0.4rem;
        color: #020617;
        background: #38bdf8;
        box-shadow: 0 4px 10px -4px rgba(56, 189, 248, 0.7);
        white-space: nowrap;
      }
      .note-box.voice-1 { background: #38bdf8; }
      .note-box.voice-2 { background: #a5b4fc; }
      .note-box.voice-3 { background: #4ade80; }
      .note-box.voice-4 { background: #facc15; }
      .note-box.voice-5 { background: #fb7185; }
      .note-box.voice-6 { background: #fdba74; }
      .weights-section {
        margin-bottom: 1rem;
        padding: 0.75rem 1rem;
        background: #020617;
        border: 1px solid #1f2937;
        border-radius: 0.5rem;
      }
      .weights-section summary {
        cursor: pointer;
        font-weight: 600;
        color: #e5e7eb;
      }
      .weights-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
        gap: 0.75rem 1rem;
        margin-top: 0.75rem;
      }
      .weight-item label {
        font-size: 0.8rem;
        font-weight: 500;
        color: #9ca3af;
      }
      .weight-item input {
        width: 100%;
        padding: 0.4rem 0.5rem;
        font-size: 0.9rem;
      }
      .lock-whatif-row td {
        vertical-align: top;
        padding: 0.5rem;
        font-size: 0.8rem;
      }
      .lock-whatif-label {
        color: #9ca3af;
        font-weight: 600;
      }
      .lock-label {
        display: block;
        margin-bottom: 0.35rem;
        cursor: pointer;
      }
      .lock-label input { margin-right: 0.25rem; }
      .whatif-details summary {
        cursor: pointer;
        color: #a5b4fc;
      }
      .whatif-list {
        list-style: none;
        padding: 0;
        margin: 0.35rem 0 0 0;
        max-height: 12rem;
        overflow-y: auto;
      }
      .whatif-item {
        padding: 0.25rem 0;
        border-bottom: 1px solid #1f2937;
        font-size: 0.75rem;
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.25rem;
      }
      .whatif-item.current { color: #9ca3af; }
      .whatif-notes { font-family: ui-monospace, monospace; color: #e5e7eb; }
      .whatif-cost { color: #6b7280; }
      .whatif-use-btn {
        background: #374151;
        color: #e5e7eb;
        border: 1px solid #4b5563;
        padding: 0.2rem 0.5rem;
        border-radius: 0.25rem;
        cursor: pointer;
        font-size: 0.7rem;
      }
      .whatif-use-btn:hover { background: #4b5563; }
      .whatif-current-badge { color: #4ade80; font-size: 0.7rem; }
      @media (max-width: 640px) {
        .container {
          margin: 1.5rem;
          padding: 1.5rem;
        }
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Chord Harmony Generator</h1>
      <p class="lead">
        Enter a chord progression and generate smooth multi-part harmony with optimized voice leading.
      </p>

      {% if error %}
        <div class="error">{{ error }}</div>
      {% endif %}

      <form method="post" action="{{ url_for('index') }}" id="harmony-form">
        <div class="field-group">
          <label for="voices">Number of voices</label>
          <input type="number" id="voices" name="voices" min="4" max="6" value="{{ voices or 4 }}">
          <div class="hint">Between 4 and 6. 4 is typical SATB-style harmony.</div>
        </div>

        <div class="field-group">
          <label for="progression">Chord progression</label>
          <textarea id="progression" name="progression" placeholder="Cmaj | Fmaj | G7 | Cmaj">{{ progression or "" }}</textarea>
          <div class="hint">
            Examples: <code>Cmaj | Fmaj | G7 | Cmaj</code> or <code>Am Dm G C</code>. Use spaces, pipes <code>|</code>, or commas.
          </div>
        </div>

        <details class="weights-section" {% if result %}open{% endif %}>
          <summary>Weights &amp; ranges</summary>
          <p class="hint" style="margin-bottom: 0.75rem;">Adjust voice-leading costs and pitch range. Leave blank to use defaults. Higher cost = stronger penalty.</p>
          <div class="weights-grid">
            <div class="weight-item">
              <label for="cost_static">Static voice</label>
              <input type="number" id="cost_static" name="cost_static" step="0.1" min="0" placeholder="0.5" value="{{ weights_form.get('cost_static', '') }}">
            </div>
            <div class="weight-item">
              <label for="cost_stepwise">Stepwise motion</label>
              <input type="number" id="cost_stepwise" name="cost_stepwise" step="0.1" min="0" placeholder="0.2" value="{{ weights_form.get('cost_stepwise', '') }}">
            </div>
            <div class="weight-item">
              <label for="cost_medium_step">Medium step (3–5 semitones)</label>
              <input type="number" id="cost_medium_step" name="cost_medium_step" step="0.1" min="0" placeholder="0.5" value="{{ weights_form.get('cost_medium_step', '') }}">
            </div>
            <div class="weight-item">
              <label for="cost_large_leap_base">Large leap (base)</label>
              <input type="number" id="cost_large_leap_base" name="cost_large_leap_base" step="0.1" min="0" placeholder="1.5" value="{{ weights_form.get('cost_large_leap_base', '') }}">
            </div>
            <div class="weight-item">
              <label for="cost_large_leap_per">Large leap (per semitone)</label>
              <input type="number" id="cost_large_leap_per" name="cost_large_leap_per" step="0.05" min="0" placeholder="0.1" value="{{ weights_form.get('cost_large_leap_per', '') }}">
            </div>
            <div class="weight-item">
              <label for="cost_parallel_5_8">Parallel 5ths/8ves</label>
              <input type="number" id="cost_parallel_5_8" name="cost_parallel_5_8" step="0.1" min="0" placeholder="4" value="{{ weights_form.get('cost_parallel_5_8', '') }}">
            </div>
            <div class="weight-item">
              <label for="cost_direct_5_8">Direct (hidden) 5ths/8ves</label>
              <input type="number" id="cost_direct_5_8" name="cost_direct_5_8" step="0.1" min="0" placeholder="3" value="{{ weights_form.get('cost_direct_5_8', '') }}">
            </div>
            <div class="weight-item">
              <label for="cost_voice_crossing">Voice crossing</label>
              <input type="number" id="cost_voice_crossing" name="cost_voice_crossing" step="0.1" min="0" placeholder="2.5" value="{{ weights_form.get('cost_voice_crossing', '') }}">
            </div>
            <div class="weight-item">
              <label for="bonus_contrary">Contrary motion (bonus, subtracted)</label>
              <input type="number" id="bonus_contrary" name="bonus_contrary" step="0.05" min="0" placeholder="0.25" value="{{ weights_form.get('bonus_contrary', '') }}">
            </div>
            <div class="weight-item">
              <label for="cost_span_tight">Chord span too tight</label>
              <input type="number" id="cost_span_tight" name="cost_span_tight" step="0.1" min="0" placeholder="1" value="{{ weights_form.get('cost_span_tight', '') }}">
            </div>
            <div class="weight-item">
              <label for="cost_span_wide">Chord span too wide</label>
              <input type="number" id="cost_span_wide" name="cost_span_wide" step="0.1" min="0" placeholder="1.5" value="{{ weights_form.get('cost_span_wide', '') }}">
            </div>
            <div class="weight-item">
              <label for="span_tight_threshold">Span tight below (semitones)</label>
              <input type="number" id="span_tight_threshold" name="span_tight_threshold" min="0" placeholder="6" value="{{ weights_form.get('span_tight_threshold', '') }}">
            </div>
            <div class="weight-item">
              <label for="span_wide_threshold">Span wide above (semitones)</label>
              <input type="number" id="span_wide_threshold" name="span_wide_threshold" min="0" placeholder="20" value="{{ weights_form.get('span_wide_threshold', '') }}">
            </div>
            <div class="weight-item">
              <label for="range_low">Range low (MIDI, e.g. 48)</label>
              <input type="number" id="range_low" name="range_low" min="24" max="127" placeholder="auto" value="{{ weights_form.get('range_low', '') }}">
            </div>
            <div class="weight-item">
              <label for="range_high">Range high (MIDI, e.g. 79)</label>
              <input type="number" id="range_high" name="range_high" min="24" max="127" placeholder="auto" value="{{ weights_form.get('range_high', '') }}">
            </div>
            <div class="weight-item">
              <label for="max_spread">Max chord spread (semitones)</label>
              <input type="number" id="max_spread" name="max_spread" min="8" max="24" placeholder="16" value="{{ weights_form.get('max_spread', '') }}">
            </div>
          </div>
        </details>

        <div class="btn-row">
          <button class="primary" type="submit">
            ▶ Generate Harmony
          </button>
          <span class="pill"><strong>Tip</strong> Harmony is recomputed instantly as you tweak chords.</span>
        </div>

      {% if result %}
        <input type="hidden" name="locked_voicings" id="locked_voicings_input" value="{{ locked_voicings_json }}">
        <div class="results">
          <h2>Result</h2>
          <div class="field-group">
            <label>Chords</label>
            <div class="chords">
              {{ result.chords | map(attribute='symbol') | join(' | ') }}
            </div>
          </div>

          <div class="field-group">
            <label>Voices (highest to lowest)</label>
            <table class="voices">
              <thead>
                <tr>
                  <th>Voice</th>
                  {% for idx in range(result_step_count) %}
                    <th>Step {{ idx + 1 }}</th>
                  {% endfor %}
                </tr>
              </thead>
              <tbody>
                {% for v_idx, voice_notes in enumerate(note_names_by_voice) %}
                  <tr>
                    <td>Voice {{ v_idx + 1 }}</td>
                    {% for note in voice_notes %}
                      <td>{{ note }}</td>
                    {% endfor %}
                  </tr>
                {% endfor %}
                <tr class="lock-whatif-row">
                  <td class="lock-whatif-label">Lock / What if</td>
                  {% for step in range(result_step_count) %}
                    <td class="lock-whatif-cell">
                      <label class="lock-label" title="Lock this voicing for re-optimize">
                        <input type="checkbox" class="lock-cb" data-chord-index="{{ step }}" data-voicing="{{ chord_voicings_json_list[step] }}" {% if step in locked_chord_indices %}checked{% endif %}>
                        Lock
                      </label>
                      <details class="whatif-details">
                        <summary>What if</summary>
                        <ul class="whatif-list">
                          {% for alt in alternatives_per_chord[step] %}
                            <li class="whatif-item {{ 'current' if alt.is_current else '' }}">
                              <span class="whatif-notes">{{ alt.midi_str }}</span>
                              <span class="whatif-cost">cost {{ alt.cost }}</span>
                              {% if not alt.is_current %}
                                <button type="button" class="whatif-use-btn" data-chord-index="{{ step }}" data-voicing="{{ alt.midi_json }}">Use this</button>
                              {% else %}
                                <span class="whatif-current-badge">current</span>
                              {% endif %}
                            </li>
                          {% endfor %}
                        </ul>
                      </details>
                    </td>
                  {% endfor %}
                </tr>
              </tbody>
            </table>
          </div>

          <div class="field-group">
            <label>Visualizer</label>
            <div class="visualizer">
              {% for v_idx, voice_notes in enumerate(note_names_by_voice) %}
                <div class="voice-row">
                  <div class="voice-label">Voice {{ v_idx + 1 }}</div>
                  <div class="voice-track">
                    {% for note in voice_notes %}
                      <div class="note-box voice-{{ v_idx + 1 }}" title="{{ note }}">
                        {{ note }}
                      </div>
                    {% endfor %}
                  </div>
                </div>
              {% endfor %}
            </div>
          </div>

          <div class="download">
            {% if midi_available %}
              <a href="{{ url_for('download_midi') }}">⬇ Download MIDI (output.mid)</a>
            {% else %}
              <span class="hint">To export MIDI, install <code>music21</code> (already in <code>requirements.txt</code>).</span>
            {% endif %}
          </div>
        </div>
      {% endif %}
      </form>

      {% if result %}
      <script>
        (function() {
          var form = document.getElementById("harmony-form");
          var lockedInput = document.getElementById("locked_voicings_input");
          if (!form || !lockedInput) return;
          function getLocked() {
            try { return JSON.parse(lockedInput.value || "{}"); } catch (e) { return {}; }
          }
          function setLocked(obj) {
            lockedInput.value = JSON.stringify(obj);
          }
          form.querySelectorAll(".lock-cb").forEach(function(cb) {
            cb.addEventListener("change", function() {
              var locked = getLocked();
              var idx = this.getAttribute("data-chord-index");
              var voicing = this.getAttribute("data-voicing");
              if (this.checked && voicing) {
                try { locked[idx] = JSON.parse(voicing); } catch (e) {}
              } else {
                delete locked[idx];
              }
              setLocked(locked);
            });
          });
          form.querySelectorAll(".whatif-use-btn").forEach(function(btn) {
            btn.addEventListener("click", function() {
              var locked = getLocked();
              var idx = this.getAttribute("data-chord-index");
              var voicing = this.getAttribute("data-voicing");
              if (idx != null && voicing) {
                try { locked[idx] = JSON.parse(voicing); } catch (e) {}
                setLocked(locked);
                form.submit();
              }
            });
          });
        })();
      </script>
      {% endif %}
    </div>
  </body>
</html>
"""


def _weights_to_form(w) -> dict:
    """Convert HarmonyWeights to dict of string values for form pre-fill."""
    return {
        "cost_static": str(w.cost_static),
        "cost_stepwise": str(w.cost_stepwise),
        "cost_medium_step": str(w.cost_medium_step),
        "cost_large_leap_base": str(w.cost_large_leap_base),
        "cost_large_leap_per": str(w.cost_large_leap_per),
        "cost_parallel_5_8": str(w.cost_parallel_5_8),
        "cost_direct_5_8": str(w.cost_direct_5_8),
        "cost_voice_crossing": str(w.cost_voice_crossing),
        "bonus_contrary": str(w.bonus_contrary),
        "cost_wide_gap_base": str(w.cost_wide_gap_base),
        "cost_wide_gap_per": str(w.cost_wide_gap_per),
        "spacing_octave": str(w.spacing_octave),
        "cost_span_tight": str(w.cost_span_tight),
        "cost_span_wide": str(w.cost_span_wide),
        "span_tight_threshold": str(w.span_tight_threshold),
        "span_wide_threshold": str(w.span_wide_threshold),
        "range_low": str(w.range_low) if w.range_low is not None else "",
        "range_high": str(w.range_high) if w.range_high is not None else "",
        "max_spread": str(w.max_spread),
    }


def _parse_locked_voicings(form_value: str) -> tuple[dict, dict]:
    """
    Parse locked_voicings from form (JSON with string keys). Returns
    (locked_for_backend: dict int->list, locked_for_form: dict str->list for re-submit).
    """
    if not form_value or not form_value.strip():
        return {}, {}
    try:
        raw = json.loads(form_value)
    except (json.JSONDecodeError, TypeError):
        return {}, {}
    if not isinstance(raw, dict):
        return {}, {}
    locked_backend = {}
    locked_form = {}
    for k, v in raw.items():
        try:
            idx = int(k)
        except (ValueError, TypeError):
            continue
        if not isinstance(v, list) or not all(isinstance(x, int) for x in v):
            continue
        locked_backend[idx] = v
        locked_form[k] = v
    return locked_backend, locked_form


@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    result = None
    note_names_by_voice = None
    voices = 4
    progression_text = ""
    midi_available = False
    weights_form = _weights_to_form(default_weights())
    chord_voicings = []
    chord_voicings_json_list = []
    alternatives_per_chord = []
    locked_voicings_json = "{}"
    locked_chord_indices = set()

    if request.method == "POST":
        progression_text = request.form.get("progression", "").strip()
        voices_raw = request.form.get("voices", "").strip() or "4"
        weights = weights_from_form(request.form)
        weights_form = _weights_to_form(weights)
        locked_backend, locked_form = _parse_locked_voicings(
            request.form.get("locked_voicings", "") or ""
        )
        locked_voicings_json = json.dumps(locked_form) if locked_form else "{}"
        locked_chord_indices = set(int(k) for k in locked_form) if locked_form else set()

        try:
            voices = int(voices_raw)
            if not (4 <= voices <= 6):
                raise ValueError
        except ValueError:
            error = "Number of voices must be an integer between 4 and 6."
        else:
            if not progression_text:
                error = "Please enter at least one chord."
            else:
                try:
                    chords = parse_progression(progression_text)
                except ValueError as e:
                    error = f"Error parsing progression: {e}"
                else:
                    try:
                        result = generate_harmony(
                            chords,
                            num_voices=voices,
                            weights=weights,
                            locked_voicings=locked_backend if locked_backend else None,
                        )
                    except Exception as e:  # pragma: no cover - defensive
                        error = f"Error generating harmony: {e}"
                    else:
                        note_names_by_voice = result.as_note_names()
                        try:
                            export_to_midi(result, filename="output.mid")
                            midi_available = True
                        except ImportError:
                            midi_available = False
                        except Exception:
                            midi_available = False

                        n = len(result.voices)
                        num_chords = len(result.chords)
                        path_voicings = [
                            tuple(
                                result.voices[n - 1 - v][t]
                                for v in range(n)
                            )
                            for t in range(num_chords)
                        ]
                        chord_voicings = [list(p) for p in path_voicings]
                        alternatives_per_chord = []
                        for k in range(num_chords):
                            alts = get_chord_alternatives(
                                chords, voices, weights, path_voicings, k
                            )
                            current = path_voicings[k]
                            options = []
                            for voicing, cost in alts:
                                midi_list = list(voicing)
                                options.append(
                                    {
                                        "midi": midi_list,
                                        "midi_json": json.dumps(midi_list),
                                        "midi_str": ", ".join(str(m) for m in midi_list),
                                        "cost": round(cost, 2),
                                        "is_current": voicing == current,
                                    }
                                )
                            alternatives_per_chord.append(options)
                        chord_voicings_json_list = [
                            json.dumps(cv) for cv in chord_voicings
                        ]

    return render_template_string(
        INDEX_TEMPLATE,
        error=error,
        result=result,
        note_names_by_voice=note_names_by_voice,
        result_step_count=len(result.chords) if result else 0,
        voices=voices,
        progression=progression_text,
        midi_available=midi_available,
        weights_form=weights_form,
        chord_voicings=chord_voicings,
        chord_voicings_json_list=chord_voicings_json_list,
        alternatives_per_chord=alternatives_per_chord,
        locked_voicings_json=locked_voicings_json,
        locked_chord_indices=locked_chord_indices,
        enumerate=enumerate,
        range=range,
    )


@app.route("/download-midi")
def download_midi():
    # Serve the last generated MIDI file if it exists
    try:
        return send_file("output.mid", as_attachment=True)
    except Exception:
        return redirect(url_for("index"))


if __name__ == "__main__":
    # Run the app in debug mode for development; you can change host/port here.
    app.run(debug=True, port=5001)

