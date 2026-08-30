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


def test_party_role_roundtrip(client, admin_headers):
    payload = _profile("党职甲")
    payload["party_role"] = "中央政治局委员"
    created = client.post("/api/officials", json=payload, headers=admin_headers)
    assert created.status_code == 201, created.text
    assert created.json()["party_role"] == "中央政治局委员"

    payload["party_role"] = "中央委员"
    updated = client.put(f"/api/officials/{created.json()['id']}", json=payload, headers=admin_headers)
    assert updated.status_code == 200
    assert updated.json()["party_role"] == "中央委员"

    payload["party_role"] = ""
    cleared = client.put(f"/api/officials/{created.json()['id']}", json=payload, headers=admin_headers)
    assert cleared.json()["party_role"] == ""


def test_party_role_filter_is_hierarchical(client, admin_headers):
    roles = (("常委甲", "中央政治局常委"), ("局委甲", "中央政治局委员"), ("委员甲", "中央委员"),
             ("候补甲", "中央候补委员"), ("无职甲", ""))
    for name, role in roles:
        payload = _profile(name)
        payload["party_role"] = role
        created = client.post("/api/officials", json=payload, headers=admin_headers)
        assert created.status_code == 201, created.text

    def names_for(params: dict) -> set[str]:
        rows = client.get("/api/officials", params=params, headers=admin_headers).json()
        return {item["name"] for item in rows["items"]}

    assert names_for({"party_role": "中央政治局常委"}) == {"常委甲"}
    assert names_for({"party_role": "中央政治局委员"}) == {"常委甲", "局委甲"}
    assert names_for({"party_role": "中央委员"}) == {"常委甲", "局委甲", "委员甲"}
    assert names_for({"party_role": "中央候补委员"}) == {"候补甲"}

    # 与状态筛选可叠加
    assert names_for({"party_role": "中央委员", "status": "在任"}) == {"常委甲", "局委甲", "委员甲"}
    assert names_for({"party_role": "中央委员", "status": "退休"}) == set()

    unsupported = client.get("/api/officials", params={"party_role": "军委主席"}, headers=admin_headers)
    assert unsupported.status_code == 400


def test_status_filter_supports_fallen(client, admin_headers):
    for name, status_value in (("落马甲", "落马"), ("在任甲", "在任")):
        payload = _profile(name)
        payload["status"] = status_value
        created = client.post("/api/officials", json=payload, headers=admin_headers)
        assert created.status_code == 201, created.text

    rows = client.get("/api/officials", params={"status": "落马"}, headers=admin_headers).json()
    assert {item["name"] for item in rows["items"]} == {"落马甲"}
    assert rows["items"][0]["status"] == "落马"


def test_timeline_loads_selected_profiles_in_order(client, admin_headers):
    first = client.post("/api/officials", json=_profile("时间线甲"), headers=admin_headers).json()
    second = client.post("/api/officials", json=_profile("时间线乙"), headers=admin_headers).json()

    response = client.post(
        "/api/officials/timeline",
        json={"official_ids": [second["id"], first["id"], second["id"]]},
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    assert [item["name"] for item in response.json()["officials"]] == ["时间线乙", "时间线甲"]
    assert response.json()["officials"][0]["careers"][0]["start_date"] == "2020.01"
    candidates = client.get("/api/officials/timeline/candidates", headers=admin_headers)
    assert candidates.status_code == 200
    assert {item["name"] for item in candidates.json()} == {"时间线甲", "时间线乙"}


def test_timeline_rejects_missing_profile(client, admin_headers):
    response = client.post(
        "/api/officials/timeline", json={"official_ids": [99999]}, headers=admin_headers
    )
    assert response.status_code == 404


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
