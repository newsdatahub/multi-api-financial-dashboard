import pytest
from app.api.newsdatahub import NewsDataHubClient

def test_newsdatahub_deduplicate_headlines():
    """Test that duplicate headlines are removed."""
    client = NewsDataHubClient()

    articles = [
        {"title": "Apple releases new iPhone", "source_title": "TechCrunch", "pub_date": "2024-01-01"},
        {"title": "Apple releases new iPhone", "source_title": "Reuters", "pub_date": "2024-01-02"},
        {"title": "Different headline", "source_title": "Bloomberg", "pub_date": "2024-01-03"},
    ]

    result = client._deduplicate_articles(articles)

    # Should keep only 2 articles (one duplicate removed)
    assert len(result) == 2

def test_newsdatahub_deduplicate_sources():
    """Test that duplicate sources keep up to 2 freshest articles per source."""
    client = NewsDataHubClient()

    articles = [
        {"title": "Old article", "source_title": "Reuters", "pub_date": "2024-01-01"},
        {"title": "Newer article", "source_title": "Reuters", "pub_date": "2024-01-02"},
        {"title": "Different source", "source_title": "Bloomberg", "pub_date": "2024-01-03"},
    ]

    result = client._deduplicate_articles(articles)

    # Should keep 3 articles (2 Reuters - both kept since limit is 2 per source, 1 Bloomberg)
    assert len(result) == 3

    # Find the Reuters articles
    reuters_articles = [a for a in result if a["source_title"] == "Reuters"]
    assert len(reuters_articles) == 2
    assert reuters_articles[0]["title"] == "Newer article"  # Newest first

def test_newsdatahub_quota_headers():
    """Test quota header parsing."""
    client = NewsDataHubClient()

    headers = {
        "X-RateLimit-Limit": "100",
        "X-RateLimit-Remaining": "50",
        "X-RateLimit-Reset": "2024-12-31T23:59:59Z"
    }

    client._update_quota_from_headers(headers)

    assert client.quota_limit == 100
    assert client.quota_remaining == 50
    assert client.quota_reset == "2024-12-31T23:59:59Z"
