#!/usr/bin/env python3
import argparse
import logging

from .config import Config
from .pipeline import VeillePipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)


def main():
    parser = argparse.ArgumentParser(
        prog="veille-renovation",
        description="Veille hebdomadaire rénovation énergétique",
    )
    parser.add_argument("--days", type=int, default=None, help="Jours en arrière (défaut : 7)")
    parser.add_argument("--min-score", type=int, default=None, help="Score minimum (défaut : 1)")
    args = parser.parse_args()

    config = Config.load()
    if args.days is not None:
        config.lookback_days = args.days
    if args.min_score is not None:
        config.min_score = args.min_score

    VeillePipeline(config).run()


if __name__ == "__main__":
    main()
