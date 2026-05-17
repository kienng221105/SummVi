import pytest
from fastapi import status

def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={"email": "newuser@example.com", "password": "password123"}
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "id" in data

def test_register_existing_user(client, db):
    from app.models.user import AppUser
    from app.services.auth_service import get_password_hash
    
    # Pre-register a user
    user = AppUser(email="existing@example.com", password_hash=get_password_hash("password123"))
    db.add(user)
    db.commit()
    
    response = client.post(
        "/auth/register",
        json={"email": "existing@example.com", "password": "password123"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Email đã được đăng ký"

def test_login_success(client, db):
    from app.models.user import AppUser
    from app.services.auth_service import get_password_hash
                                        
    user = AppUser(email="login@example.com", password_hash=get_password_hash("password123"))
    db.add(user)
    db.commit()
    
    response = client.post(
        "/auth/login",
        data={"username": "login@example.com", "password": "password123"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()

def test_login_fail(client):
    response = client.post(
        "/auth/login",
        data={"username": "wrong@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_read_me(authenticated_client, mock_user):
    response = authenticated_client.get("/auth/me")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["email"] == mock_user.email
