# PTT Release Gap Speed Profile Report

## Scope

- Issue: `#33` under umbrella `#28`.
- Change: opt-in PTT release-gap profile for `scripts/stt_codex.py`.
- Non-scope: beam/VAD tuning, model tuning, backend changes, automatic Enter.

## Contract

- Default profile: `accuracy`.
- `accuracy` release gap: `0.75s`.
- `speed` release gap: `0.35s`.
- Direct release-gap override precedence: `--release-gap` / `STT_PTT_RELEASE_GAP`.
- Profile precedence: `--ptt-profile` / `STT_PTT_PROFILE`.
- Fallback: `accuracy` default.
- Enter remains manual.

## Deterministic Timing Delta

| profile | release gap | expected wait delta vs default |
| --- | ---: | ---: |
| `accuracy` | `0.75s` | `0.00s` |
| `speed` | `0.35s` | `-0.40s` |

- Prior/default to speed value: `0.75s -> 0.35s`.
- Expected stop-wait reduction after the last repeated trigger input: `0.40s`.

## Verification Evidence

- Default behavior unchanged:
  - `scripts/stt_codex.py` with no PTT profile resolves `ptt_profile=accuracy`.
  - no-profile release gap resolves to `0.75s`.
- Speed profile:
  - `--ptt-profile speed` resolves release gap to `0.35s`.
  - `STT_PTT_PROFILE=speed` resolves release gap to `0.35s`.
- Override precedence:
  - `STT_PTT_RELEASE_GAP` overrides profile selection.
  - explicit `--release-gap` overrides `STT_PTT_RELEASE_GAP` and profile selection.
- Manual Enter:
  - this leaf changes only stop timing configuration.
  - transcript injection still writes text only.
  - no automatic Enter behavior added.
- Fixed smoke STT:
  - not rerun for this leaf.
  - reason: release-gap profile changes CLI/env stop timing selection only.
  - unchanged surfaces: fixed WAV transcription, model, beam/VAD, audio handoff, transcript policy.

## Truncation Risk

- Live mic truncation: `not measured`.
- Reason: this leaf only adds deterministic CLI/env selection and no live PTT device smoke was run in this implementation pass.
- Risk: lowering the release gap can stop recording before the final syllable, long vowel, or trailing command token if terminal key repeat pauses before speech actually ends.
- Mitigation: `accuracy` remains the default `0.75s`; `speed` is opt-in; users can set an intermediate value with `--release-gap` or `STT_PTT_RELEASE_GAP`.

## Measurement Boundary

- Measured by deterministic tests: profile/default/override resolution.
- Not measured: live `arecord` stop latency, child PTY injection latency, terminal render latency, live utterance truncation.
