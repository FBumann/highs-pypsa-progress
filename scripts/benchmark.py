import re
import subprocess
import sys
import threading
import time

import pandas as pd

version = snakemake.wildcards.highs_version
resolution = int(snakemake.wildcards.resolution)
trials = int(snakemake.config["trials"])
network_file = snakemake.input[0]
output = snakemake.output[0]

NAN = float("nan")


def write(rows):
    pd.DataFrame(rows, columns=["solve_time", "solve_memory"]).to_csv(
        output, sep="\t", index=False
    )


# Install the highspy version under test -- the only variable across runs.
# A version with no installable wheel just yields NaN rows so a single bad
# version never fails the whole workflow.
try:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--force-reinstall",
            "--no-deps",
            "--no-cache-dir",
            f"highspy=={version}",
        ],
        check=True,
    )
except subprocess.CalledProcessError:
    write([[NAN, NAN]] * trials)
    sys.exit(0)

import psutil
import highspy
import pypsa

process = psutil.Process()

# The pinned (modern) linopy maps a fixed set of HighsModelStatus members to
# termination conditions. Older highspy releases predate some of them (e.g.
# kInterrupt, kMemoryLimit), which would make linopy raise AttributeError while
# building that map. We keep the harness fixed (so highspy is the only variable)
# and inject the missing members as inert sentinels: old highspy never *returns*
# these statuses, so the sentinel keys are never matched -- the solve is
# unaffected and stays comparable to newer versions on the identical LP.
_LINOPY_HIGHS_STATUS = [
    "kInfeasible",
    "kInterrupt",
    "kIterationLimit",
    "kLoadError",
    "kMemoryLimit",
    "kModelEmpty",
    "kModelError",
    "kNotset",
    "kObjectiveBound",
    "kObjectiveTarget",
    "kOptimal",
    "kPostsolveError",
    "kPresolveError",
    "kSolutionLimit",
    "kSolveError",
    "kTimeLimit",
    "kUnbounded",
    "kUnboundedOrInfeasible",
    "kUnknown",
]


class _UnsupportedStatus:
    """Sentinel for a HighsModelStatus member this highspy version lacks."""


def _inject_missing_status():
    for name in _LINOPY_HIGHS_STATUS:
        if not hasattr(highspy.HighsModelStatus, name):
            setattr(highspy.HighsModelStatus, name, _UnsupportedStatus())


_inject_missing_status()


def solve(n):
    # Backstop for any member a future linopy references that is not in the
    # list above: inject the named-missing member and retry.
    for _ in range(len(_LINOPY_HIGHS_STATUS) + 5):
        try:
            n.optimize.solve_model(solver_name="highs")
            return
        except AttributeError as error:
            match = re.search(r"has no attribute '(\w+)'", str(error))
            if not match:
                raise
            setattr(highspy.HighsModelStatus, match.group(1), _UnsupportedStatus())
    raise RuntimeError("could not resolve missing HighsModelStatus members")


def measure_solve(n):
    """Measure the solve step only.

    The model is built before measurement starts, so the highspy install, the
    PyPSA/linopy model construction, and result post-processing are excluded.
    Time is HiGHS' own reported solver runtime; memory is the peak RSS increase
    observed during the solve (HiGHS exposes no memory metric of its own).
    """
    n.optimize.create_model()

    peak = baseline = process.memory_info().rss
    stop = threading.Event()

    def sample():
        nonlocal peak
        while not stop.is_set():
            peak = max(peak, process.memory_info().rss)
            time.sleep(0.005)

    sampler = threading.Thread(target=sample)
    sampler.start()
    wall_start = time.perf_counter()
    try:
        solve(n)
    finally:
        stop.set()
        sampler.join()

    try:
        solve_time = n.model.solver_model.getRunTime()
    except Exception:
        solve_time = time.perf_counter() - wall_start

    solve_memory = max(peak - baseline, 0) / 1e6  # bytes -> MB
    return solve_time, solve_memory


rows = []
for _ in range(trials):
    # Per-trial guard: any unexpected failure for a given version degrades to
    # NaN instead of aborting the whole run.
    try:
        n = pypsa.Network(network_file)
        n.snapshots = n.snapshots[::resolution]
        rows.append(list(measure_solve(n)))
    except Exception:
        rows.append([NAN, NAN])

write(rows)
