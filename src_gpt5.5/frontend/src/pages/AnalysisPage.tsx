import { FormEvent, useEffect, useState } from "react";
import { api, AnalysisTask } from "../api/client";

export function AnalysisPage() {
  const [tasks, setTasks] = useState<AnalysisTask[]>([]);
  const [name, setName] = useState("关系强度分析");
  const [taskType, setTaskType] = useState("ego_network");

  function load() {
    api.listAnalysisTasks().then(setTasks).catch(() => setTasks([]));
  }

  useEffect(() => {
    load();
  }, []);

  async function createTask(event: FormEvent) {
    event.preventDefault();
    await api.createAnalysisTask({
      name,
      task_type: taskType,
      parameters: {
        max_hops: 2,
        min_score: 20
      }
    });
    load();
  }

  return (
    <section>
      <div className="page-title">
        <div>
          <h1>分析任务</h1>
          <p>保存分析参数、权重方案和结果版本，便于后续复跑。</p>
        </div>
      </div>
      <form className="inline-form" onSubmit={createTask}>
        <input value={name} onChange={(event) => setName(event.target.value)} />
        <select value={taskType} onChange={(event) => setTaskType(event.target.value)}>
          <option value="ego_network">中心网络</option>
          <option value="pair">两人路径</option>
          <option value="group_cluster">群体聚类</option>
        </select>
        <button>创建任务</button>
      </form>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>名称</th>
              <th>类型</th>
              <th>状态</th>
              <th>创建时间</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task) => (
              <tr key={task.id}>
                <td>{task.name}</td>
                <td>{task.task_type}</td>
                <td>{task.status}</td>
                <td>{new Date(task.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {tasks.length === 0 && (
              <tr>
                <td colSpan={4} className="empty">
                  暂无分析任务
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

