import requests
from packaging.version import parse


def list_versions():
    url = "https://pypi.org/pypi/highspy/json"
    json = requests.get(url, timeout=5).json()["releases"]
    versions = sorted(json, key=parse, reverse=True)
    return list(set(versions).difference(config["forbidden"]))


configfile: "config.yaml"


storage:
    provider="http",


wildcard_constraints:
    highs_version="[dev0-9.]*",
    resolution="[0-9]*",


rule all:
    input:
        "web/index.html",


rule benchmark:
    input:
        storage.http(config["file"], keep_local=True),
    output:
        "benchmark/run_{resolution}_{highs_version}.tsv",
    script:
        "scripts/benchmark.py"


rule web:
    input:
        expand(
            "benchmark/run_{resolution}_{highs_version}.tsv",
            highs_version=list_versions(),
            **config["scenarios"],
        ),
    output:
        csv="web/results.csv",
        html="web/index.html",
    script:
        "scripts/web.py"
