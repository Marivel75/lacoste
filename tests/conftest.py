from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.pipeline.models import Article


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def make_article(
    title="Test article",
    url="https://example.com/article",
    source="TestSource",
    category="Presse",
    summary="",
    published=None,
) -> Article:
    if published is None:
        published = datetime.now(tz=timezone.utc)
    return Article(
        title=title,
        url=url,
        source=source,
        category=category,
        summary=summary,
        published=published,
    )
