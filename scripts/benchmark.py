import subprocess
import sys

import pypsa

version = snakemake.wildcards.highs_version
resolution = int(snakemake.wildcards.resolution)

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

n = pypsa.Network(snakemake.input[0])

n.snapshots = n.snapshots[::resolution]

n.optimize(
    solver_name="highs",
    # **snakemake.config['solver_options']
)
