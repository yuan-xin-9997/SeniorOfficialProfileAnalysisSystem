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
