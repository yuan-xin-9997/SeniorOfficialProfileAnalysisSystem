import { useEffect, useMemo, useState } from "react";
import { api, CurrentUser } from "./api/client";
import { AnalysisPage } from "./pages/AnalysisPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { OfficialsPage } from "./pages/OfficialsPage";
import { RelationshipsPage } from "./pages/RelationshipsPage";
import { SourcesPage } from "./pages/SourcesPage";

type PageKey = "dashboard" | "officials" | "relationships" | "analysis" | "sources";

const pages: Array<{ key: PageKey; label: string; adminOnly?: boolean }> = [
  { key: "dashboard", label: "工作台" },
  { key: "officials", label: "官员档案" },
  { key: "relationships", label: "关系图谱" },
  { key: "analysis", label: "分析任务" },
  { key: "sources", label: "数据源", adminOnly: true }
];

export function App() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [page, setPage] = useState<PageKey>("dashboard");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const visiblePages = useMemo(
    () => pages.filter((item) => !item.adminOnly || user?.role === "ADMIN"),
    [user]
  );

  if (loading) {
    return <div className="page-shell centered">正在加载系统状态...</div>;
  }

  if (!user) {
    return <LoginPage onLogin={setUser} />;
  }

  const renderPage = () => {
    switch (page) {
      case "officials":
        return <OfficialsPage user={user} />;
      case "relationships":
        return <RelationshipsPage user={user} />;
      case "analysis":
        return <AnalysisPage />;
      case "sources":
        return <SourcesPage />;
      default:
        return <DashboardPage user={user} />;
    }
  };

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">履</span>
          <div>
            <strong>履历分析系统</strong>
            <small>内部研究版</small>
          </div>
        </div>
        <nav>
          {visiblePages.map((item) => (
            <button
              className={page === item.key ? "active" : ""}
              key={item.key}
              onClick={() => setPage(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="content">
        <header className="topbar">
          <div>
            <strong>{user.display_name || user.username}</strong>
            <span>{user.role === "ADMIN" ? "管理员" : "普通用户"}</span>
          </div>
          <button
            className="secondary"
            onClick={() => {
              api.logout().finally(() => setUser(null));
            }}
          >
            退出
          </button>
        </header>
        {renderPage()}
      </main>
    </div>
  );
}
