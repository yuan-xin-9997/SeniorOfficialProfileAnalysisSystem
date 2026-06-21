import { FormEvent, useEffect, useState } from "react";
import { api, CareerEvent, CurrentUser, Official } from "../api/client";

interface OfficialsPageProps {
  user: CurrentUser;
}

export function OfficialsPage({ user }: OfficialsPageProps) {
  const [query, setQuery] = useState("");
  const [officials, setOfficials] = useState<Official[]>([]);
  const [selected, setSelected] = useState<Official | null>(null);
  const [timeline, setTimeline] = useState<CareerEvent[]>([]);
  const [name, setName] = useState("");
  const [summary, setSummary] = useState("");
  const [eventType, setEventType] = useState("appointment");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [positionName, setPositionName] = useState("");
  const [locationName, setLocationName] = useState("");
  const [eventDescription, setEventDescription] = useState("");
  const [csvText, setCsvText] = useState(
    "name,membership_type,rank_order,profile_summary\n张三,member,1,\n李四,alternate_member,2,"
  );
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  function load(q = query) {
    setError("");
    api.listOfficials(q).then(setOfficials).catch((err) => setError(String(err)));
  }

  useEffect(() => {
    load("");
  }, []);

  async function createOfficial(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    await api.createOfficial({
      name,
      profile_summary: summary,
      review_status: "draft",
      birth_date_precision: "unknown"
    });
    setName("");
    setSummary("");
    load();
  }

  async function selectOfficial(official: Official) {
    setSelected(official);
    setMessage("");
    setError("");
    const events = await api.listTimeline(official.id);
    setTimeline(events);
  }

  async function createTimelineEvent(event: FormEvent) {
    event.preventDefault();
    if (!selected || !eventDescription.trim()) return;
    const created = await api.createTimelineEvent(selected.id, {
      event_type: eventType,
      start_date: startDate || null,
      end_date: endDate || null,
      organization_name: organizationName || null,
      position_name: positionName || null,
      location_name: locationName || null,
      description: eventDescription
    });
    setTimeline((items) => [...items, created]);
    setStartDate("");
    setEndDate("");
    setOrganizationName("");
    setPositionName("");
    setLocationName("");
    setEventDescription("");
    setMessage("履历事件已保存");
  }

  async function importMembers(event: FormEvent) {
    event.preventDefault();
    const result = await api.importCommitteeMembers({
      term_no: 20,
      term_name: "中国共产党第二十届中央委员会",
      start_year: 2022,
      end_year: 2027,
      csv_text: csvText
    });
    setMessage(
      `导入完成：新增 ${result.created_officials} 人，更新 ${result.updated_officials} 人，成员关系 ${result.memberships_upserted} 条，跳过 ${result.skipped_rows} 行`
    );
    load("");
  }

  return (
    <section>
      <div className="page-title">
        <div>
          <h1>官员档案</h1>
          <p>检索、查看和维护高级官员基础档案。</p>
        </div>
      </div>

      <div className="toolbar">
        <input
          placeholder="按姓名或摘要检索"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") load();
          }}
        />
        <button onClick={() => load()}>检索</button>
      </div>

      {user.role === "ADMIN" && (
        <form className="inline-form" onSubmit={createOfficial}>
          <input
            placeholder="姓名"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <input
            placeholder="简介摘要"
            value={summary}
            onChange={(event) => setSummary(event.target.value)}
          />
          <button>新增档案</button>
        </form>
      )}

      {error && <p className="error">{error}</p>}

      {user.role === "ADMIN" && (
        <form className="import-panel" onSubmit={importMembers}>
          <div>
            <h2>导入最近一届名单</h2>
            <p>CSV 表头支持 name,membership_type,rank_order,profile_summary。membership_type 可填 member 或 alternate_member。</p>
          </div>
          <textarea value={csvText} onChange={(event) => setCsvText(event.target.value)} />
          <button>导入第 20 届名单</button>
        </form>
      )}

      {message && <p className="success">{message}</p>}

      <div className="split-view">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>姓名</th>
                <th>出生</th>
                <th>状态</th>
                <th>审核</th>
                <th>摘要</th>
              </tr>
            </thead>
            <tbody>
              {officials.map((official) => (
                <tr
                  key={official.id}
                  className={selected?.id === official.id ? "selected-row" : ""}
                  onClick={() => selectOfficial(official)}
                >
                  <td>{official.name}</td>
                  <td>{official.birth_date || "未知"}</td>
                  <td>{official.current_status || "未知"}</td>
                  <td>{official.review_status}</td>
                  <td>{official.profile_summary || "-"}</td>
                </tr>
              ))}
              {officials.length === 0 && (
                <tr>
                  <td colSpan={5} className="empty">
                    暂无数据
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <aside className="detail-panel">
          {selected ? (
            <>
              <h2>{selected.name}</h2>
              <p>{selected.profile_summary || "暂无简介"}</p>
              <div className="timeline-list">
                {timeline.map((item) => (
                  <div className="timeline-item" key={item.id}>
                    <strong>
                      {item.start_date || "未知"} 至 {item.end_date || "未知"}
                    </strong>
                    <span>{item.event_type}</span>
                    <p>{item.description}</p>
                    <small>
                      {[item.organization_name, item.position_name, item.location_name]
                        .filter(Boolean)
                        .join(" / ") || "未填机构地点"}
                    </small>
                  </div>
                ))}
                {timeline.length === 0 && <p className="empty">暂无履历事件</p>}
              </div>

              {user.role === "ADMIN" && (
                <form className="event-form" onSubmit={createTimelineEvent}>
                  <select value={eventType} onChange={(event) => setEventType(event.target.value)}>
                    <option value="appointment">任职</option>
                    <option value="education">教育</option>
                    <option value="part_time_study">在职学习</option>
                    <option value="transfer">调任</option>
                  </select>
                  <div className="form-row">
                    <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
                    <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
                  </div>
                  <input placeholder="机构/学校" value={organizationName} onChange={(event) => setOrganizationName(event.target.value)} />
                  <input placeholder="职位/专业" value={positionName} onChange={(event) => setPositionName(event.target.value)} />
                  <input placeholder="地点" value={locationName} onChange={(event) => setLocationName(event.target.value)} />
                  <textarea placeholder="履历描述" value={eventDescription} onChange={(event) => setEventDescription(event.target.value)} />
                  <button>新增履历事件</button>
                </form>
              )}
            </>
          ) : (
            <p className="empty">点击左侧官员查看详情和履历时间线</p>
          )}
        </aside>
      </div>
    </section>
  );
}
