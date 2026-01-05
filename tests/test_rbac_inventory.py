import pytest
from fastapi import status

@pytest.mark.rbac
class TestInventoryRBACMatrix:
    """Test RBAC matrix for inventory endpoints"""
    
    # Test data for endpoints
    CREATE_ITEM_DATA = {"name": "Test Item", "quantity": 5, "price": 100.0}
    CREATE_LOCATION_DATA = {"name": "Test Location", "address": "Test Address"}
    CREATE_TX_DATA = {"item_id": 1, "quantity": 3, "type": "in", "notes": "Test"}
    UPDATE_ITEM_DATA = {"name": "Updated Item", "quantity": 10, "price": 200.0}

    # VIEWER Tests - Read Only Access
    def test_viewer_can_get_items(self, client, auth_tokens):
        """VIEWER: GET /items → 200 OK"""
        headers = {"Authorization": f"Bearer {auth_tokens['viewer']}"}
        response = client.get("/api/v1/inventory/items", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_role"] == "viewer"
        assert data["permissions"] == "READ_INVENTORY"

    def test_viewer_can_get_stock(self, client, auth_tokens):
        """VIEWER: GET /stock → 200 OK"""
        headers = {"Authorization": f"Bearer {auth_tokens['viewer']}"}
        response = client.get("/api/v1/inventory/stock", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["permissions"] == "READ_STOCK"

    def test_viewer_cannot_create_items(self, client, auth_tokens):
        """VIEWER: POST /items → 403 Forbidden"""
        headers = {"Authorization": f"Bearer {auth_tokens['viewer']}"}
        response = client.post(
            "/api/v1/inventory/items", 
            json=self.CREATE_ITEM_DATA,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Required roles: ['staff', 'admin', 'super_admin']" in response.json()["detail"]

    def test_viewer_cannot_create_transactions(self, client, auth_tokens):
        """VIEWER: POST /tx → 403 Forbidden"""
        headers = {"Authorization": f"Bearer {auth_tokens['viewer']}"}
        response = client.post(
            "/api/v1/inventory/tx",
            json=self.CREATE_TX_DATA, 
            headers=headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_cannot_create_locations(self, client, auth_tokens):
        """VIEWER: POST /locations → 403 Forbidden"""
        headers = {"Authorization": f"Bearer {auth_tokens['viewer']}"}
        response = client.post(
            "/api/v1/inventory/locations",
            json=self.CREATE_LOCATION_DATA,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # STAFF Tests - Read + Create Items/Transactions
    def test_staff_can_get_items(self, client, auth_tokens):
        """STAFF: GET /items → 200 OK"""
        headers = {"Authorization": f"Bearer {auth_tokens['staff']}"}
        response = client.get("/api/v1/inventory/items", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_role"] == "staff"

    def test_staff_can_create_items(self, client, auth_tokens):
        """STAFF: POST /items → 200 OK"""
        headers = {"Authorization": f"Bearer {auth_tokens['staff']}"}
        response = client.post(
            "/api/v1/inventory/items",
            json=self.CREATE_ITEM_DATA,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["permissions"] == "CREATE_ITEM"

    def test_staff_can_create_transactions(self, client, auth_tokens):
        """STAFF: POST /tx → 200 OK"""
        headers = {"Authorization": f"Bearer {auth_tokens['staff']}"}
        response = client.post(
            "/api/v1/inventory/tx",
            json=self.CREATE_TX_DATA,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["permissions"] == "CREATE_TRANSACTION"

    def test_staff_cannot_create_locations(self, client, auth_tokens):
        """STAFF: POST /locations → 403 Forbidden"""
        headers = {"Authorization": f"Bearer {auth_tokens['staff']}"}
        response = client.post(
            "/api/v1/inventory/locations",
            json=self.CREATE_LOCATION_DATA,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Required roles: ['admin', 'super_admin']" in response.json()["detail"]

    def test_staff_cannot_update_items(self, client, auth_tokens):
        """STAFF: PUT /items/1 → 403 Forbidden"""
        headers = {"Authorization": f"Bearer {auth_tokens['staff']}"}
        response = client.put(
            "/api/v1/inventory/items/1",
            json=self.UPDATE_ITEM_DATA,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_staff_cannot_delete_items(self, client, auth_tokens):
        """STAFF: DELETE /items/1 → 403 Forbidden"""
        headers = {"Authorization": f"Bearer {auth_tokens['staff']}"}
        response = client.delete("/api/v1/inventory/items/1", headers=headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # ADMIN Tests - Full Management Access
    def test_admin_can_create_locations(self, client, auth_tokens):
        """ADMIN: POST /locations → 200 OK"""
        headers = {"Authorization": f"Bearer {auth_tokens['admin']}"}
        response = client.post(
            "/api/v1/inventory/locations",
            json=self.CREATE_LOCATION_DATA,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["permissions"] == "CREATE_LOCATION"

    def test_admin_can_update_items(self, client, auth_tokens):
        """ADMIN: PUT /items/1 → 200 OK"""
        headers = {"Authorization": f"Bearer {auth_tokens['admin']}"}
        response = client.put(
            "/api/v1/inventory/items/1",
            json=self.UPDATE_ITEM_DATA,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["permissions"] == "UPDATE_ITEM"

    def test_admin_can_delete_items(self, client, auth_tokens):
        """ADMIN: DELETE /items/1 → 200 OK"""
        headers = {"Authorization": f"Bearer {auth_tokens['admin']}"}
        response = client.delete("/api/v1/inventory/items/1", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["permissions"] == "DELETE_ITEM"

    # Authentication Tests
    def test_no_token_returns_401(self, client):
        """No token: All endpoints → 401 Unauthorized"""
        endpoints = [
            ("GET", "/api/v1/inventory/items"),
            ("GET", "/api/v1/inventory/stock"),
            ("POST", "/api/v1/inventory/items"),
            ("POST", "/api/v1/inventory/locations"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
                
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_token_returns_401(self, client):
        """Invalid token: All endpoints → 401 Unauthorized"""  
        headers = {"Authorization": "Bearer invalid-token"}
        
        response = client.get("/api/v1/inventory/items", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED