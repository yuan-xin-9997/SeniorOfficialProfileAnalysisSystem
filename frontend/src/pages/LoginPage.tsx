import { FormEvent, useState } from "react";
import { api, CurrentUser } from "../api/client";

interface LoginPageProps {
  onLogin: (user: CurrentUser) => void;
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const login = await api.login(username, password);
      api.setAccessToken(login.access_token);
      const currentUser = await api.me();
      onLogin(currentUser);
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-screen">
      <form className="login-card" onSubmit={submit}>
        <div className="brand login-brand">
          <span className="brand-mark">履</span>
          <div>
            <strong>高级官员履历分析系统</strong>
            <small>个人内部研究版</small>
          </div>
        </div>
        <label>
          用户名
          <input value={username} onChange={(event) => setUsername(event.target.value)} />
        </label>
        <label>
          密码
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button disabled={submitting}>{submitting ? "登录中..." : "登录"}</button>
        <p className="hint">默认管理员账号由后端环境变量初始化，首次部署后请及时修改。</p>
      </form>
    </div>
  );
}

