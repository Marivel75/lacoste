from datetime import datetime, timezone

from src.pipeline.models import Article


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
