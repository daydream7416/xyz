# -*- coding: utf-8 -*-
def test_auth_and_property_flow(test_client):
    agent_payload = {
        "name": "Premium Broker",
        "email": "broker@example.com",
        "phone": "+90 555 111 22 33",
        "company": "Metra QA",
        "experience": "10 yıl",
        "profile_photo_url": "https://example.com/photo.jpg",
        "city": "Ankara",
        "happy_customers": 120,
        "successful_sales": 85,
        "instagram_url": "https://instagram.com/metraqa",
        "facebook_url": "https://facebook.com/metraqa",
        "slug": "premium-broker",
        "is_premium": True,
    }
    resp_agent = test_client.post("/agents/", json=agent_payload)
    assert resp_agent.status_code == 200, resp_agent.text

    register_payload = {
        "name": "Test Broker",
        "email": "broker@example.com",
        "password": "StrongPass123",
        "phone": "+90 555 111 22 33",
        "company": "Metra QA",
    }
    resp = test_client.post("/auth/register", json=register_payload)
    assert resp.status_code == 200, resp.text
    user = resp.json()
    assert user["email"] == register_payload["email"]
    assert user["agent_id"] == resp_agent.json()["id"]

    resp_dup = test_client.post("/auth/register", json=register_payload)
    assert resp_dup.status_code == 400

    resp_login = test_client.post(
        "/auth/login",
        data={"email": register_payload["email"], "password": register_payload["password"]},
    )
    assert resp_login.status_code == 200, resp_login.text
    login_data = resp_login.json()
    assert login_data["user"]["email"] == register_payload["email"]
    headers = {"X-Session-Token": login_data["access_token"]}

    property_payload = {
        "title": "Merkezde İmarlı Arsa",
        "status": "Satılık",
        "category": "arsa",
        "price": "12.750.000 ₺",
        "location": "Çankaya, Ankara",
        "description": "850 m² köşe parsel, %40-2 kat imar izni.",
        "tagline": "Yatırımlık fırsat",
        "image_url": "https://example.com/image.jpg",
        "area": "850 m²",
        "rooms": None,
        "zoning_status": "Konut imarlı",
        "floor": None,
        "building_age": None,
        "featured": True,
        "specs": ["850 m²", "Konut imarlı", "E:1.80", "Yola sıfır"],
    }
    resp_create = test_client.post("/properties/", json=property_payload, headers=headers)
    assert resp_create.status_code == 200, resp_create.text
    property_id = resp_create.json()["id"]

    resp_public = test_client.get("/properties/")
    assert resp_public.status_code == 200
    assert len(resp_public.json()) == 1

    resp_by_slug = test_client.get("/properties/?agent_slug=premium-broker")
    assert resp_by_slug.status_code == 200
    assert len(resp_by_slug.json()) == 1

    resp_mine = test_client.get("/properties/?only_mine=true", headers=headers)
    assert resp_mine.status_code == 200
    assert len(resp_mine.json()) == 1

    update_payload = {
        "price": "15.000.000 ₺",
        "specs": ["850 m²", "Konut imarlı", "E:1.80", "Yola sıfır"],
    }
    resp_update = test_client.put(f"/properties/{property_id}", json=update_payload, headers=headers)
    assert resp_update.status_code == 200, resp_update.text
    assert resp_update.json()["price"] == update_payload["price"]
    assert "Yola sıfır" in resp_update.json()["specs"]

    resp_update_unauth = test_client.put(f"/properties/{property_id}", json=update_payload)
    assert resp_update_unauth.status_code in (401, 422, 403)

    resp_delete = test_client.delete(f"/properties/{property_id}", headers=headers)
    assert resp_delete.status_code == 200

    resp_after_delete = test_client.get("/properties/")
    assert resp_after_delete.status_code == 200
    assert resp_after_delete.json() == []

    resp_logout = test_client.post("/auth/logout", headers=headers)
    assert resp_logout.status_code == 200

    resp_after_logout = test_client.get("/properties/?only_mine=true", headers=headers)
    assert resp_after_logout.status_code == 401


def test_register_rejected_without_premium(test_client):
    agent_payload = {
        "name": "Standart Broker",
        "email": "standard@example.com",
        "phone": "+90 555 000 00 00",
        "company": "Metra QA",
        "experience": "5 yıl",
        "profile_photo_url": "https://example.com/photo2.jpg",
        "city": "İstanbul",
        "happy_customers": 50,
        "successful_sales": 30,
        "instagram_url": "https://instagram.com/standard",
        "facebook_url": "https://facebook.com/standard",
        "slug": "standard-broker",
        "is_premium": False,
    }
    resp_agent = test_client.post("/agents/", json=agent_payload)
    assert resp_agent.status_code == 200

    register_payload = {
        "name": "Standart Kullanıcı",
        "email": "standard@example.com",
        "password": "StrongPass123",
        "phone": "+90 555 000 00 00",
        "company": "Metra QA",
    }
    resp = test_client.post("/auth/register", json=register_payload)
    assert resp.status_code == 403

    register_payload_missing_agent = {
        "name": "Diğer Kullanıcı",
        "email": "missing@example.com",
        "password": "StrongPass123",
        "phone": "+90 555 111 11 11",
        "company": "Metra QA",
    }
    resp_missing = test_client.post("/auth/register", json=register_payload_missing_agent)
    assert resp_missing.status_code == 403
