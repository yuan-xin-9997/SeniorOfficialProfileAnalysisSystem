import { FormEvent, useEffect, useState } from "react";
import { api, SourceConfig, SourceDocument } from "../api/client";

export function SourcesPage() {
  const [sources, setSources] = useState<SourceConfig[]>([]);
  const [documents, setDocuments] = useState<SourceDocument[]>([]);
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [crawlingId, setCrawlingId] = useState<string | null>(null);
  const [parsingId, setParsingId] = useState<string | null>(null);

  function load() {
    api.listSourceConfigs().then(setSources).catch(() => setSources([]));
    api.listSourceDocuments().then(setDocuments).catch(() => setDocuments([]));
  }

  useEffect(() => {
    load();
  }, []);

  async function createSource(event: FormEvent) {
    event.preventDefault();
    if (!name.trim() || !baseUrl.trim()) return;
    setError("");
    setMessage("");
    await api.createSourceConfig({
      name,
      base_url: baseUrl,
      source_type: "official",
      trust_level: "A",
      crawl_strategy: "requests",
      frequency_cron: "0 3 * * 1",
      request_interval_seconds: 3,
      max_retry: 3,
      is_enabled: true
    });
    setName("");
    setBaseUrl("");
    setMessage("数据源已新增");
    load();
  }

  async function crawl(source: SourceConfig) {
    setCrawlingId(source.id);
    setError("");
    setMessage("");
    try {
      const document = await api.crawlSourceConfig(source.id);
      setMessage(
        `抓取完成：${document.title || document.url}，状态 ${document.parse_status}`
      );
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "抓取失败");
    } finally {
      setCrawlingId(null);
    }
  }

  async function parseDocument(document: SourceDocument) {
    setParsingId(document.id);
    setError("");
    setMessage("");
    try {
      const result = await api.parseSourceDocument(document.id);
      const official = result.official_name ? `匹配 ${result.official_name}` : "未匹配官员";
      setMessage(
        `解析完成：${official}，候选 ${result.parsed_candidates} 条，新增 ${result.created_events} 条，重复 ${result.skipped_duplicates} 条`
      );
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "解析失败");
    } finally {
      setParsingId(null);
    }
  }

  return (
    <section>
      <div className="page-title">
        <div>
          <h1>数据源</h1>
          <p>默认每周抓取，可按数据源覆盖 Cron 表达式。</p>
        </div>
      </div>
      <form className="inline-form" onSubmit={createSource}>
        <input
          placeholder="数据源名称"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <input
          placeholder="URL"
          value={baseUrl}
          onChange={(event) => setBaseUrl(event.target.value)}
        />
        <button>新增数据源</button>
      </form>
      {message && <p className="success">{message}</p>}
      {error && <p className="error">{error}</p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>名称</th>
              <th>类型</th>
              <th>可信度</th>
              <th>频率</th>
              <th>状态</th>
              <th>URL</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((source) => (
              <tr key={source.id}>
                <td>{source.name}</td>
                <td>{source.source_type}</td>
                <td>{source.trust_level}</td>
                <td>{source.frequency_cron}</td>
                <td>{source.is_enabled ? "启用" : "停用"}</td>
                <td>{source.base_url}</td>
                <td>
                  <button
                    className="secondary"
                    disabled={crawlingId === source.id}
                    onClick={() => crawl(source)}
                  >
                    {crawlingId === source.id ? "抓取中..." : "立即抓取"}
                  </button>
                </td>
              </tr>
            ))}
            {sources.length === 0 && (
              <tr>
                <td colSpan={7} className="empty">
                  暂无数据源
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="page-title secondary-title">
        <div>
          <h2>抓取记录</h2>
          <p>保存原始 HTML 和正文快照，后续解析模块会从这些正文中抽取履历。</p>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>标题</th>
              <th>状态</th>
              <th>HTTP</th>
              <th>抓取时间</th>
              <th>正文摘要</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((document) => (
              <tr key={document.id}>
                <td>
                  <a href={document.url} target="_blank" rel="noreferrer">
                    {document.title || document.url}
                  </a>
                </td>
                <td>{document.parse_status}</td>
                <td>{document.http_status || "-"}</td>
                <td>{new Date(document.fetched_at).toLocaleString()}</td>
                <td className="excerpt">{document.plain_text_excerpt || "-"}</td>
                <td>
                  <button
                    className="secondary"
                    disabled={parsingId === document.id}
                    onClick={() => parseDocument(document)}
                  >
                    {parsingId === document.id ? "解析中..." : "解析履历"}
                  </button>
                </td>
              </tr>
            ))}
            {documents.length === 0 && (
              <tr>
                <td colSpan={6} className="empty">
                  暂无抓取记录
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
