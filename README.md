## Continuous HiGHS Benchmark

This workflow runs small benchmark cases for solving
[PyPSA](https://pypsa.readthedocs.io) networks with the
[HiGHS](https://highs.dev) solver. The test case is a small single-node capacity
expansion model for a 100% renewable electricity system with exogenous demand,
wind and solar generation, battery storage and hydrogen storage. The temporal
resolution is currently varied from 2-hourly to 6-hourly resolution for a full
year.

The benchmark is automatically executed for **all** available HiGHS versions on
[PyPI]("https://pypi.org/pypi/highspy") on the 1st of every month at 5 AM and
the results are subsequently deployed to
https://fneum.github.io/highs-pypsa-progress/. Every run re-benchmarks all
versions on the same machine, so the version-to-version comparison within a
published chart is always measured on identical hardware.

## Run Locally

Install [uv](https://docs.astral.sh/uv/), then run:

```sh
uv run snakemake -j1 -F
```

`uv` automatically creates the environment from `pyproject.toml`/`uv.lock` on
first run.

## License

MIT
