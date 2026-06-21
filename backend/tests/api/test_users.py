from unittest.mock import ANY

import pytest
import requests
from expects import equal, expect

from src.common.domain.constants.status import HTTP_200_OK, HTTP_201_CREATED
from tests.api.conftest import BASE_URL, LoginTestContext


@pytest.mark.api
@pytest.mark.parametrize(
    argnames="payload",
    argvalues=[
        {
            "email": "tenant_user1@test.com",
            "password": "pass1234567890",
            "firstName": "John",
            "lastName": "Doe",
            "isOwner": True,
            "status": "ACTIVE",
            "phoneNumber": None,
        },
        {
            "email": "tenant_user2@test.com",
            "password": "pass1234567890",
            "firstName": "Jane",
            "lastName": "Smith",
            "isOwner": True,
            "status": "ACTIVE",
            "phoneNumber": None,
        },
    ],
)
def test_create_tenant_users(login_user: LoginTestContext, payload: dict):
    """Test creating tenant users with reuse=true for idempotency"""
    headers = {
        "Authorization": f"Bearer {login_user.access_token}",
        "x-tenant": login_user.tenant_slug,
    }

    # Use reuse=true to make the endpoint idempotent
    # If user exists, it returns 200 with existing user
    # If user doesn't exist, it creates and returns 201
    response = requests.post(
        url=f"{BASE_URL}/v1/tenants/users",
        headers=headers,
        params={"reuse": True},
        json=payload,
        timeout=30,
    )

    # Accept both 200 (existing user) and 201 (newly created)
    assert response.status_code in [HTTP_200_OK, HTTP_201_CREATED], (
        f"Expected 200 or 201, got {response.status_code}: {response.text}"
    )

    # Store the user ID for subsequent tests
    login_user.tenant_user_ids.append(response.json()["data"]["uuid"])


@pytest.mark.api
def test_tenant_user_list(login_user: LoginTestContext):
    """Test listing tenant users"""
    headers = {
        "Authorization": f"Bearer {login_user.access_token}",
        "x-tenant": login_user.tenant_slug,
    }

    response = requests.get(
        url=f"{BASE_URL}/v1/tenants/users?reuse=true",
        headers=headers,
        timeout=30,
    )

    expect(response.status_code).to(equal(HTTP_200_OK))


@pytest.mark.api
def test_get_tenant_user(login_user: LoginTestContext):
    """Test getting a single tenant user by ID"""
    headers = {
        "Authorization": f"Bearer {login_user.access_token}",
        "x-tenant": login_user.tenant_slug,
    }

    tenant_user_id = login_user.tenant_user_ids[0]
    response = requests.get(
        url=f"{BASE_URL}/v1/tenants/users/{tenant_user_id}",
        headers=headers,
        timeout=30,
    )

    expect(response.status_code).to(equal(HTTP_200_OK))
    data = response.json()["data"]
    expect(data["uuid"]).to(equal(tenant_user_id))


@pytest.mark.api
def test_update_tenant_user(login_user: LoginTestContext):
    """Test updating a tenant user"""
    headers = {
        "Authorization": f"Bearer {login_user.access_token}",
        "x-tenant": login_user.tenant_slug,
    }

    tenant_user_id = login_user.tenant_user_ids[0]
    response = requests.put(
        url=f"{BASE_URL}/v1/tenants/users/{tenant_user_id}",
        headers=headers,
        json={
            "email": "tenant_user1@test.com",
            "firstName": "Updated John",
            "lastName": "Updated Doe",
            "isOwner": False,
            "status": "INACTIVE",
            "phoneNumber": None,
        },
        timeout=30,
    )

    expect(response.status_code).to(equal(HTTP_200_OK))
    data = response.json()["data"]
    expect(data).to(
        equal(
            {
                "uuid": ANY,
                "firstName": "Updated John",
                "lastName": "Updated Doe",
                "phoneNumber": None,
                "emailAddress": ANY,
                "isOwner": False,
                "isSupport": False,
                "photoUrl": None,
                "status": "INACTIVE",
                "tenantRole": None,
                "createdAt": ANY,
            }
        )
    )


@pytest.mark.api
def test_delete_tenant_user(login_user: LoginTestContext):
    """Test deleting a tenant user"""
    headers = {
        "Authorization": f"Bearer {login_user.access_token}",
        "x-tenant": login_user.tenant_slug,
    }

    tenant_user_id = login_user.tenant_user_ids[1]
    response = requests.delete(
        url=f"{BASE_URL}/v1/tenants/users/{tenant_user_id}",
        headers=headers,
        timeout=30,
    )

    expect(response.status_code).to(equal(HTTP_200_OK))
