import pytest
from fastapi import status
from uuid import uuid4

def test_list_conversations(authenticated_client, db, mock_user):
    from app.models.conversation import Conversation
    
    # Add a mock conversation
    conv = Conversation(id=uuid4(), user_id=mock_user.id, title="Test Conv")
    db.add(conv)
    db.commit()
    
    response = authenticated_client.get("/history/conversations")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert any(c["title"] == "Test Conv" for c in data)

def test_delete_conversation_success(authenticated_client, db, mock_user):
    from app.models.conversation import Conversation
    
    conv = Conversation(id=uuid4(), user_id=mock_user.id, title="Delete Me")
    db.add(conv)
    db.commit()
    
    response = authenticated_client.delete(f"/history/conversations/{conv.id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Đã xóa thành công"

def test_delete_other_user_conversation(authenticated_client, db):
    from app.models.conversation import Conversation
    
    other_user_id = uuid4()
    conv = Conversation(id=uuid4(), user_id=other_user_id, title="Not Yours")
    db.add(conv)
    db.commit()
    
    response = authenticated_client.delete(f"/history/conversations/{conv.id}")
    # Based on the route code, it returns 404 if success is False
    assert response.status_code == status.HTTP_404_NOT_FOUND
