import pytest
from fastapi import status
from uuid import uuid4

def test_list_users_as_admin(admin_client, db):
    from app.models.user import AppUser
    
    # Add another user
    user = AppUser(email="user1@example.com", role="user")
    db.add(user)
    db.commit()
    
    response = admin_client.get("/admin/users")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert any(u["email"] == "user1@example.com" for u in data)

def test_list_users_as_user(authenticated_client):
    response = authenticated_client.get("/admin/users")
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_get_logs_as_admin(admin_client, db):
    from app.models.system_log import SystemLog
    
    # Add a mock log
    log = SystemLog(
        id=uuid4(),
        request_id=str(uuid4()),
        endpoint="/test",
        method="GET",
        status_code=200
    )
    db.add(log)
    db.commit()
    
    response = admin_client.get("/admin/logs")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1

def test_get_analytics_as_admin(admin_client):
    response = admin_client.get("/admin/analytics")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "overview" in data
    assert "charts" in data

def test_update_user_role(admin_client, db):
    from app.models.user import AppUser
    
    user = AppUser(email="role_update@example.com", role="user")
    db.add(user)
    db.commit()
    db.refresh(user)
    
    response = admin_client.patch(
        f"/admin/users/{user.id}/role",
        json={"role": "admin"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["role"] == "admin"
