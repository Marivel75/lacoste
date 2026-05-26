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
    from src.services.newsletter_service import send_newsletter

    result = send_newsletter(
        args.week,
        extra_recipients=args.extra_recipients or None,
        limit=args.limit,
        prod=args.prod,
    )
    log = logging.getLogger(__name__)
    if result["sent"]:
        log.info(
            "Newsletter %s envoyée à : %s — %d articles.",
            result["week"], ", ".join(result["recipients"]), result["articles_sent"],
        )
    elif result["articles_sent"] == 0:
        log.warning("Newsletter %s — aucun article en base.", result["week"])
    else:
        log.warning(
            "Newsletter %s — %d articles trouvés mais email non configuré.",
            result["week"], result["articles_sent"],
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
    p_nl.add_argument("--week", type=str, default=None, help="Ex : 2026-W20 (mode hebdo)")
    p_nl.add_argument("--limit", type=int, default=None,
                      help="Mode quotidien : N articles les plus pertinents jamais envoyés")
    p_nl.add_argument("--prod", action="store_true",
                      help="Utiliser NEWSLETTER_RECIPIENTS au lieu de EMAIL_RECIPIENTS")
    p_nl.add_argument(
        "extra_recipients", nargs="*", metavar="EMAIL",
        help="Destinataires supplémentaires (s'ajoutent à la liste de base)",
    )
    p_nl.set_defaults(func=cmd_newsletter)

    p_db = sub.add_parser("initdb", help="Créer les tables en base")
    p_db.set_defaults(func=cmd_initdb)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
