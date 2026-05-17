import pytest
from fastapi import status
from uuid import uuid4
from datetime import datetime

def test_create_rating(authenticated_client, db, mock_user):
    conv_id = uuid4()
    response = authenticated_client.post(
        "/rating/",
        json={"conversation_id": str(conv_id), "rating": 5, "feedback": "Good"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["rating"] == 5

def test_get_rating_success(authenticated_client, db, mock_user):
    from app.models.rating import Rating
    conv_id = uuid4()
    rating = Rating(
        id=uuid4(),
        conversation_id=conv_id, 
        user_id=mock_user.id, 
        rating=4, 
        feedback="Nice",
        created_at=datetime.now()
    )
    db.add(rating)
    db.commit()
    
    response = authenticated_client.get(f"/rating/conversation/{conv_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["rating"] == 4

def test_get_rating_not_found(authenticated_client):
    conv_id = uuid4()
    response = authenticated_client.get(f"/rating/conversation/{conv_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
