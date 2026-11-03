"""Run the actual flat ZIP on two synthetic tasks, offline and outside the source tree."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.build_submission import audit_archive


def check_task(archive: Path, folder: Path, kind: str) -> dict:
    import numpy as np
    import pandas as pd
    from sklearn.metrics import f1_score, mean_squared_error
    from tests.synth import make_task

    target, identifier, layout = (
        ("demand", "row_key", "nested") if kind == "regression"
        else ("segment", "case_key", "flat")
    )
    folder.mkdir()
    with zipfile.ZipFile(archive) as package:
        package.extractall(folder)
    task = make_task(folder, kind=kind, n_train=400, n_test=120,
                     target=target, id_col=identifier, layout=layout,
                     crlf=True, bom=True)
    env = os.environ.copy()
    for name in ("PYTHONPATH", "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"):
        env.pop(name, None)
    env.update(AGENT_LLM="off", AGENT_TIME_LIMIT="150", AGENT_SAFETY_S="30", ML_N_JOBS="2")
    completed = subprocess.run(
        [sys.executable, "-X", "utf8", "solution.py", "task.md"],
        cwd=folder, env=env, capture_output=True, timeout=180,
    )
    if completed.returncode:
        raise ValueError(f"{kind}: solution exited with code {completed.returncode}")
    result = pd.read_csv(folder / "submission.csv")
    if (result.columns.tolist() != [identifier, target]
            or len(result) != len(task.truth)
            or result[identifier].tolist() != task.truth[identifier].tolist()
            or result.isna().any().any()):
        raise ValueError(f"{kind}: invalid submission schema, identifiers or values")
    if kind == "regression":
        metric = "rmse"
        score = float(np.sqrt(mean_squared_error(task.truth[target], result[target])))
        if not np.isfinite(result[target]).all() or score >= np.std(task.truth[target]):
            raise ValueError("regression: predictions did not improve on a constant baseline")
    else:
        metric = "f1_macro"
        score = float(f1_score(task.truth[target], result[target], average="macro"))
        if not set(result[target]) <= set(task.truth[target]) or score <= 0.5:
            raise ValueError("multiclass: invalid labels or insufficient signal learned")
    return {"task": kind, "exit": completed.returncode, "rows": len(result),
            "columns": result.columns.tolist(), "metric": metric, "score": round(score, 6)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ROOT / "artifacts" / "solution.zip")
    args = parser.parse_args()
    try:
        archive = args.archive.resolve()
        audit_archive(archive, ROOT / "reference" / "requirements.txt")
        # Only packaged modules and generated inputs reach the child processes.
        # Temporary task files and captured output are removed after the check.
        with tempfile.TemporaryDirectory(prefix="alfa-zip-smoke-") as temporary:
            for kind in ("regression", "multiclass"):
                print(json.dumps(check_task(archive, Path(temporary) / kind, kind)), flush=True)
        return 0
    except (OSError, ValueError, zipfile.BadZipFile, subprocess.TimeoutExpired) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
