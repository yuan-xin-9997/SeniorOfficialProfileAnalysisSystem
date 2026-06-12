import { useEffect, useState } from "react";
import { api, CurrentUser, Official, Relationship, AnalysisTask } from "../api/client";

interface DashboardPageProps {
  user: CurrentUser;
}

export function DashboardPage({ user }: DashboardPageProps) {
  const [officials, setOfficials] = useState<Official[]>([]);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [tasks, setTasks] = useState<AnalysisTask[]>([]);

  useEffect(() => {
    api.listOfficials().then(setOfficials).catch(() => setOfficials([]));
    api.listRelationships().then(setRelationships).catch(() => setRelationships([]));
    api.listAnalysisTasks().then(setTasks).catch(() => setTasks([]));
  }, []);

  return (
    <section>
      <div className="page-title">
        <div>
          <h1>工作台</h1>
          <p>从最近一届中央委员会开始，沉淀公开履历、来源证据和关系分析。</p>
        </div>
      </div>
      <div className="metric-grid">
        <Metric label="官员档案" value={officials.length} />
        <Metric label="关系边" value={relationships.length} />
        <Metric label="分析任务" value={tasks.length} />
        <Metric label="当前权限" value={user.role === "ADMIN" ? "管理员" : "普通用户"} />
      </div>
      <div className="panel">
        <h2>开发状态</h2>
        <div className="status-list">
          <span>后端 API 骨架</span>
          <strong>已就绪</strong>
          <span>PostgreSQL 数据模型</span>
          <strong>已就绪</strong>
          <span>关系权重默认模板</span>
          <strong>已就绪</strong>
          <span>真实抓取与 LLM 解析</span>
          <strong>下一阶段</strong>
        </div>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

