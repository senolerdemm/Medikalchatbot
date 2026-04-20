from __future__ import annotations

import json
import os
import argparse
from pprint import pprint

from datasets import load_dataset


DATASET_NAME = "alibayram/turkish-hospital-medical-articles"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect gated HF medical dataset.")
    parser.add_argument("--dataset", default=DATASET_NAME)
    parser.add_argument("--split", default=None)
    parser.add_argument("--token", default=os.getenv("HF_TOKEN"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset = load_dataset(args.dataset, token=args.token)
    print("Available splits:")
    print(dataset)
    split_name = args.split or next(iter(dataset.keys()))
    split = dataset[split_name]
    print("\nColumns:")
    print(split.column_names)
    print("\nSample rows:")
    for index in range(min(3, len(split))):
        row = split[index]
        print(f"\n--- Row {index} ---")
        pprint(row)
        print("JSON preview:")
        print(json.dumps(row, ensure_ascii=False, indent=2, default=str)[:1500])


if __name__ == "__main__":
    main()
