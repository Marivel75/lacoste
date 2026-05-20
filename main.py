#!/usr/bin/env python3
"""
Veille Rénovation Énergétique — point d'entrée CLI

Usage:
    python main.py collect [--days N] [--min-score N]
    python main.py newsletter [--week 2026-W20]
    python main.py initdb
"""
import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)


def cmd_collect(args) -> None:
    from src.config import Config
    from src.pipeline.pipeline import VeillePipeline

    config = Config.load()
    if args.days is not None:
        config.lookback_days = args.days
    if args.min_score is not None:
        config.min_score = args.min_score
    VeillePipeline(config).run()


def cmd_newsletter(args) -> None:
    # Stub — sera implémenté dans la carte [Lacoste] Service newsletter
    logging.getLogger(__name__).info(
        "Newsletter %s — non encore implémenté", args.week or "semaine courante"
    )


def cmd_initdb(_args) -> None:
    from src.db.init_db import init_db
    init_db()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lacoste",
        description="Veille Rénovation Énergétique — OPTIMMO Énergies",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_collect = sub.add_parser("collect", help="Lancer la collecte RSS")
    p_collect.add_argument("--days", type=int, default=None)
    p_collect.add_argument("--min-score", type=int, default=None)
    p_collect.set_defaults(func=cmd_collect)

    p_nl = sub.add_parser("newsletter", help="Envoyer la newsletter")
    p_nl.add_argument("--week", type=str, default=None, help="Ex : 2026-W20")
    p_nl.set_defaults(func=cmd_newsletter)

    p_db = sub.add_parser("initdb", help="Créer les tables en base")
    p_db.set_defaults(func=cmd_initdb)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
