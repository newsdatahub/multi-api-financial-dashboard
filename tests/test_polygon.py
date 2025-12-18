import pytest
from datetime import datetime
from app.api.polygon import PolygonClient

def test_polygon_transform_response():
    """Test that Polygon API response is transformed correctly."""
    client = PolygonClient()

    # Mock API response
    api_response = {
        "results": [
            {
                "t": 1700000000000,  # Unix timestamp in milliseconds
                "o": 150.0,
                "h": 152.0,
                "l": 149.0,
                "c": 151.0,
                "v": 1000000
            },
            {
                "t": 1700086400000,
                "o": 151.0,
                "h": 153.0,
                "l": 150.0,
                "c": 152.0,
                "v": 1100000
            }
        ]
    }

    result = client._transform_response(api_response, "AAPL")

    assert result["ticker"] == "AAPL"
    assert len(result["prices"]) == 2
    assert result["current_price"] == 152.0
    assert result["previous_close"] == 151.0
    assert "date" in result["prices"][0]
    assert result["prices"][0]["close"] == 151.0

def test_polygon_transform_empty_results():
    """Test transformation with empty results."""
    client = PolygonClient()

    api_response = {"results": []}
    result = client._transform_response(api_response, "AAPL")

    assert result["ticker"] == "AAPL"
    assert result["prices"] == []
    assert result["current_price"] is None
    assert result["previous_close"] is None
