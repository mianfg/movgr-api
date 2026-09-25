#!/usr/bin/env python3
"""Rewrite the movgr Deployment image in a guava checkout."""

import pathlib
import sys


def main() -> None:
    path = pathlib.Path(sys.argv[1])
    image = sys.argv[2]
    deploy = None
    result: list[str] = []
    for line in path.read_text().splitlines(True):
        if line.startswith("kind: Deployment"):
            deploy = "pending"
        elif deploy == "pending":
            if "name: movgr-redis" in line:
                deploy = "redis"
            elif "name: movgr" in line:
                deploy = "movgr"
            else:
                deploy = "unknown"
        indent = line[: len(line) - len(line.lstrip())]
        if deploy == "movgr" and line.lstrip().startswith("image:"):
            result.append(f"{indent}image: {image}\n")
            continue
        if deploy == "movgr" and line.lstrip().startswith("imagePullPolicy:"):
            result.append(f"{indent}imagePullPolicy: IfNotPresent\n")
            continue
        result.append(line)
    path.write_text("".join(result))


if __name__ == "__main__":
    main()
