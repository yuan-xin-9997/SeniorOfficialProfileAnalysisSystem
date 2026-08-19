"""高级官员履历与关系 API 基本单元测试。"""


def _profile(name: str = "张三") -> dict:
    return {
        "name": name,
        "gender": "男",
        "birth_date": "1970-01-01",
        "ethnicity": "汉族",
        "native_place": "北京",
        "education": "研究生",
        "current_position": "主任",
        "organization": "示例机构",
        "administrative_rank": "正厅级",
        "status": "在任",
        "summary": "测试人物",
        "photo_url": "",
        "source_url": "https://example.com/profile",
        "tags": ["测试"],
        "careers": [{"start_date": "2020.01", "end_date": "至今", "organization": "示例机构", "position": "主任", "sort_order": 0}],
    }


def test_official_crud_and_dashboard(client, admin_headers):
    created = client.post("/api/officials", json=_profile(), headers=admin_headers)
    assert created.status_code == 201, created.text
    official_id = created.json()["id"]
    assert created.json()["careers"][0]["position"] == "主任"

    listing = client.get("/api/officials?keyword=张三", headers=admin_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    payload = _profile()
    payload["current_position"] = "局长"
    updated = client.put(f"/api/officials/{official_id}", json=payload, headers=admin_headers)
    assert updated.status_code == 200
    assert updated.json()["current_position"] == "局长"

    dashboard = client.get("/api/officials/dashboard", headers=admin_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["official_count"] == 1
    assert dashboard.json()["career_count"] == 1


def test_relation_lifecycle(client, admin_headers):
    first = client.post("/api/officials", json=_profile("甲"), headers=admin_headers).json()
    second = client.post("/api/officials", json=_profile("乙"), headers=admin_headers).json()
    relation = client.post("/api/officials/relations", json={"source_id": first["id"], "target_id": second["id"], "relation_type": "同事", "description": "测试关系"}, headers=admin_headers)
    assert relation.status_code == 201, relation.text
    assert relation.json()["source_name"] == "甲"
    rows = client.get("/api/officials/relations", headers=admin_headers)
    assert len(rows.json()) == 1
    deleted = client.delete(f"/api/officials/relations/{relation.json()['id']}", headers=admin_headers)
    assert deleted.status_code == 204


def test_official_list_pagination(client, admin_headers):
    for name in ("分页甲", "分页乙", "分页丙"):
        created = client.post("/api/officials", json=_profile(name), headers=admin_headers)
        assert created.status_code == 201, created.text

    first_page = client.get("/api/officials?page=1&page_size=2", headers=admin_headers)
    second_page = client.get("/api/officials?page=2&page_size=2", headers=admin_headers)

    assert first_page.status_code == 200
    assert first_page.json()["total"] == 3
    assert first_page.json()["page"] == 1
    assert first_page.json()["page_size"] == 2
    assert len(first_page.json()["items"]) == 2
    assert second_page.status_code == 200
    assert second_page.json()["page"] == 2
    assert len(second_page.json()["items"]) == 1


def test_relation_analysis_uses_both_profiles(client, admin_headers, monkeypatch):
    first = client.post("/api/officials", json=_profile("分析甲"), headers=admin_headers).json()
    second_payload = _profile("分析乙")
    second_payload["organization"] = "另一机构"
    second = client.post("/api/officials", json=second_payload, headers=admin_headers).json()
    captured = {}

    def fake_chat(self, system, user):
        captured["user"] = user
        return '{"relation_type":"曾任同事","summary":"两人履历存在任职交集。","evidence":["2020.01 至今任职经历存在交集"],"confidence":"高"}'

    monkeypatch.setattr("app.backend.api.officials.LLMClient.chat", fake_chat)
    response = client.post(
        "/api/officials/relations/analyze",
        json={"source_id": first["id"], "target_id": second["id"]},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["relation_type"] == "曾任同事"
    assert response.json()["confidence"] == "高"
    assert "分析甲" in captured["user"] and "分析乙" in captured["user"]


def test_relation_analysis_rejects_same_person(client, admin_headers):
    official = client.post("/api/officials", json=_profile(), headers=admin_headers).json()
    response = client.post(
        "/api/officials/relations/analyze",
        json={"source_id": official["id"], "target_id": official["id"]},
        headers=admin_headers,
    )
    assert response.status_code == 400
