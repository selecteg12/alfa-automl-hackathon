# Environment, packaging and clean runs

Run the commands below from the repository root, using Python 3.12 and an activated virtual environment. The original competition environment was Linux; local checks on Windows do not reproduce every platform constraint.

## Prepare the environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r reference/requirements.txt
python tools/check_environment.py --full
python -m pip check
```

On Windows, create the environment with `py -3.12 -m venv .venv` and replace `python` in subsequent commands with `.\.venv\Scripts\python.exe`.

The full official dependency list is retained unchanged. It includes optional AutoML libraries and can require several gigabytes. The smaller `--install-core` profile installs only the diagnostic tool's core subset; it does not install the three boosting libraries needed for the full agent test suite.

Copy `.env.example` to `.env` and fill in the supplied endpoint, key and model. The solution loads this file beside `solution.py`; the platform instead supplies environment variables. Keep credentials outside Git.

An explicit API diagnostic is available:

```bash
python tools/check_environment.py --api
```

This sends one short request and can consume API budget. The diagnostic reads environment variables rather than loading `.env` itself. Ordinary dependency checks and the offline test suite do not need a live model.

## Run the agent

```bash
python solution.py /absolute/path/to/task/task.md
```

The argument is a file path. Data paths are resolved from the task materials; `submission.csv` is written next to `task.md`.

For a short offline run, set the following in the local `.env`:

```dotenv
AGENT_LLM=off
AGENT_TIME_LIMIT=300
AGENT_SAFETY_S=45
```

This exercises the deterministic fallback. A live LLM run requires the supplied `OPENAI_API_KEY`, `OPENAI_BASE_URL` and model configuration.

## Test, build and audit

```bash
python -m unittest discover -s tests -v
python tools/build_submission.py
python tools/build_submission.py --check artifacts/solution.zip
python tools/smoke_submission.py
python tools/build_submission.py --check artifacts/solution.zip --extract-to tmp/submission-check-01
```

The output directory must be new. The builder packages root-level Python files and a byte-for-byte copy of `reference/requirements.txt` named `requirements.txt`. It prints the archive size, file list and SHA256. Tests, docs, planning files, data, models, caches and `.env` are excluded.

The checks cover:

- A maximum ZIP size of 100,000,000 bytes and a flat, unambiguous file layout.
- The real `solution.py`, exact official requirements and valid Python syntax.
- Common embedded credential patterns, without printing matched values.
- Atomic replacement of the archive, preserving an existing package after a failed build.

The credential check is heuristic. Packaging alone does not verify imports, the live API, prediction quality or platform acceptance. The separate smoke tool runs the real ZIP on synthetic regression and multiclass tasks, checks schemas and learned signal, disables API access and removes the temporary inputs afterwards. These short checks do not reproduce a full competition run.

Tests needing the public competition datasets are skipped if `data/public` is absent. The 50,000-row grouped-validation test always checks partition integrity; its optional wall-clock guard uses `ML_GROUP_SPLIT_MAX_SECONDS`. Set this explicitly for a benchmark on a known host. An absolute timing threshold is not enabled in ordinary unit tests.

If a required module lives below the root, it can be included explicitly:

```bash
python tools/build_submission.py --module src/helper.py
```

It will be stored as `helper.py`. Imports are not rewritten; filename collisions are rejected.

## Check the platform layout

Create a separate clean directory for each task. Put only the extracted Python files and `requirements.txt` there, then add `task.md` and the input data at the paths described in that file. Remove any old output before testing. Run from that directory:

```bash
python3 solution.py task.md
```

Check the exit status and verify the output row count, identifiers, column order, prediction format and absence of missing values. Run without `PYTHONPATH` pointing at the source repository.

The original platform allowed 8 CPU cores, 32 GB RAM, 30 GB disk and three hours per task. It copied only root-level `.py` files and the official requirements from a ZIP of at most 100 MB. Intermediate directories can be created during execution.

Historical team planning and platform rules remain in [MATERIALS.md](MATERIALS.md) and [SUBMISSIONS.md](SUBMISSIONS.md). Their October 2026 preparation notes are historical snapshots.

## Local verification — 3 November 2026

Windows, Python 3.12.14: `check_environment.py --full` matched all 37 official package versions; `pip check` reported no broken requirements. The first full unit run executed 314 tests: 300 passed, 13 lacked public datasets and one exceeded the original five-second timing guard. After making that host-specific guard opt-in, `python -m unittest tests.test_validation -v` passed its 20 available tests, with two dataset-dependent skips. The full suite was not repeated after this test-only adjustment.

`python tools/build_submission.py` and `python tools/smoke_submission.py` succeeded. The final ZIP was 101,440 bytes; both clean tasks produced 120-row submissions with the expected identifiers and columns. Synthetic test RMSE was 1.334681; multiclass Macro F1 was 0.790759. Live API calls, full public-data runs and Linux platform acceptance were not tested here.
