import pytest
from fastapi import status
from unittest.mock import patch

def test_get_topics(client):
    with patch("app.services.analytics_service.get_topic_distribution") as mock_topics:
        mock_topics.return_value = {"Technology": 10}
        response = client.get("/analytics/topics")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["topics"]["Technology"] == 10

def test_get_top_keywords(client):
    with patch("app.services.analytics_service.get_top_keywords") as mock_keys:
        mock_keys.return_value = [{"keyword": "AI", "count": 5}]
        response = client.get("/analytics/top-keywords")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["keywords"][0]["keyword"] == "AI"

def test_get_trends(client):
    with patch("app.services.analytics_service.get_keyword_trends") as mock_trends:
        mock_trends.return_value = [{"date": "2024-01-01", "keyword": "AI", "count": 10}]
        response = client.get("/analytics/trends")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["trends"][0]["count"] == 10

def test_get_summary_stats(client):
    with patch("app.services.analytics_service.get_summary_stats") as mock_stats:
        mock_stats.return_value = {
            "total_summaries": 100,
            "avg_summary_length": 50.0,
            "avg_compression_ratio": 0.5,
            "min_summary_length": 10,
            "max_summary_length": 200
        }
        response = client.get("/analytics/summary-stats")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["stats"]["total_summaries"] == 100
