from dataclasses import dataclass, field
from pathlib import Path
import yaml
from dotenv import load_dotenv
import os


ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Config:
    keywords: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    lookback_days: int = 7
    min_score: int = 1
    data_dir: Path = ROOT / "data"
    email_sender: str = ""
    email_password: str = ""
    email_recipients: list[str] = field(default_factory=list)

    @property
    def email_enabled(self) -> bool:
        return bool(self.email_sender and self.email_password and self.email_recipients)

    @classmethod
    def load(cls) -> "Config":
        load_dotenv()
        keywords = cls._load_keywords(ROOT / "config" / "keywords.yml")
        sources = cls._load_sources(ROOT / "config" / "sources.yml")
        recipients_raw = os.getenv("EMAIL_RECIPIENTS", "")
        recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
        return cls(
            keywords=keywords,
            sources=sources,
            lookback_days=int(os.getenv("LOOKBACK_DAYS", 7)),
            min_score=int(os.getenv("MIN_SCORE", 1)),
            email_sender=os.getenv("EMAIL_SENDER", ""),
            email_password=os.getenv("EMAIL_PASSWORD", ""),
            email_recipients=recipients,
        )

    @staticmethod
    def _load_keywords(path: Path) -> list[str]:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return [kw.lower() for kw in data.get("keywords", [])]

    @staticmethod
    def _load_sources(path: Path) -> list[dict]:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("sources", [])
