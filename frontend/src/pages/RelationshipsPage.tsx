import { useEffect, useState } from "react";
import { api, CurrentUser, Relationship } from "../api/client";

interface RelationshipsPageProps {
  user: CurrentUser;
}

export function RelationshipsPage({ user }: RelationshipsPageProps) {
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [message, setMessage] = useState("");

  function load() {
    api.listRelationships().then(setRelationships).catch(() => setRelationships([]));
  }

  useEffect(() => {
    load();
  }, []);

  async function rebuild() {
    const result = await api.rebuildRelationships();
    setMessage(`已生成 ${result.generated_relationships} 条关系边`);
    load();
  }

  return (
    <section>
      <div className="page-title">
        <div>
          <h1>关系图谱</h1>
          <p>一期先展示关系边列表，后续接入可交互图谱画布。</p>
        </div>
        {user.role === "ADMIN" && <button onClick={rebuild}>重算关系</button>}
      </div>
      {message && <p className="success">{message}</p>}
      <div className="graph-placeholder">
        <div>
          <strong>图谱画布预留区</strong>
          <span>节点代表官员，边代表同乡、同校、同机构、上下级等关系。</span>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>关系类型</th>
              <th>主体</th>
              <th>客体</th>
              <th>强度</th>
              <th>置信度</th>
              <th>证据摘要</th>
            </tr>
          </thead>
          <tbody>
            {relationships.map((item) => (
              <tr key={item.id}>
                <td>{item.relationship_type}</td>
                <td>{item.subject_name || item.subject_official_id}</td>
                <td>{item.object_name || item.object_official_id}</td>
                <td>{item.strength_score}</td>
                <td>{item.confidence}</td>
                <td>{item.evidence_summary || "-"}</td>
              </tr>
            ))}
            {relationships.length === 0 && (
              <tr>
                <td colSpan={6} className="empty">
                  暂无关系边
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
