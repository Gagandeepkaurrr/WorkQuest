import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Link,
  Navigate,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router";
import {
  Plus,
  Upload,
  Download,
  ArrowUpRight,
  ShieldCheck,
  Check,
  Play,
  Archive,
  Activity,
} from "lucide-react";
import { api, write } from "../../lib/api-client";
import { useSession } from "../auth/use-session";
import { Button } from "../../components/ui/button";
import { Dialog } from "../../components/ui/dialog";
import { Loading, ErrorState } from "../../components/feedback/states";
import { downloadJson } from "../../lib/download";
import type { RunSummary } from "../../lib/types";
type ScenarioRow = {
  id: string;
  slug: string;
  title: string;
  archived: boolean;
  active_version_id: string;
  versions: { id: string; version: number; status: string }[];
};
type Definition = {
  metadata: {
    title: string;
    description: string;
    company: string;
    role: string;
    difficulty: string;
    duration: string;
    tags: string[];
    briefing: string;
    objectives: string[];
  };
  [key: string]: unknown;
};
type Version = {
  id: string;
  scenario_id: string;
  status: string;
  draft_revision: number;
  version_number: number;
  content_hash: string;
  validated_hash: string | null;
  validation_report: {
    passed: boolean;
    errors: string[];
    golden_score: number;
    golden_time: number;
  } | null;
  definition: Definition;
};
export function AdminScenarios() {
  const user = useSession().data;
  const [error, setError] = useState<unknown>();
  const [importOpen, setImportOpen] = useState(false);
  const [source, setSource] = useState("");
  const nav = useNavigate();
  const list = useQuery({
    queryKey: ["admin-scenarios"],
    queryFn: () => api<{ items: ScenarioRow[] }>("/admin/scenarios"),
    enabled: user?.role === "admin",
  });
  if (user?.role !== "admin") return <Navigate to="/missions" />;
  if (list.isPending) return <Loading />;
  async function create(id: string) {
    try {
      const v = await write<Version>(`/admin/scenarios/${id}/versions`);
      nav(`/admin/scenarios/${id}/edit?version=${v.id}`);
    } catch (e) {
      setError(e);
    }
  }
  return (
    <div>
      <header className="page-header">
        <div>
          <span className="eyebrow">SCENARIO STUDIO</span>
          <h1>Make the learning real.</h1>
          <p>
            Draft, validate, preview, and publish immutable practice scenarios.
          </p>
        </div>
        <div className="row">
          <Button variant="secondary" asChild>
            <Link to="/admin/operations">
              <Activity size={15} /> Operations
            </Link>
          </Button>
          <Button onClick={() => setImportOpen(true)}>
            <Upload size={15} /> Import draft
          </Button>
        </div>
      </header>
      {list.error && <ErrorState error={list.error} />}
      <div className="stack">
        {list.data?.items.map((s) => (
          <article className="glass content-card" key={s.id}>
            <div className="row between">
              <div>
                <span className="tag">
                  {s.archived ? "ARCHIVED" : "AVAILABLE"}
                </span>
                <h2>{s.title}</h2>
              </div>
              <Button variant="secondary" onClick={() => void create(s.id)}>
                <Plus size={16} /> New draft version
              </Button>
            </div>
            <div className="admin-versions">
              {s.versions.map((v) => (
                <Link
                  key={v.id}
                  to={`/admin/scenarios/${s.id}/edit?version=${v.id}`}
                >
                  <span>
                    Version {v.version} · {v.status}
                  </span>
                  <ArrowUpRight size={16} />
                </Link>
              ))}
            </div>
            {!s.archived && (
              <Button
                variant="ghost"
                onClick={() => {
                  if (
                    window.confirm(
                      "Archive this scenario? Existing runs remain accessible.",
                    )
                  )
                    void write(`/admin/scenarios/${s.id}/archive`)
                      .then(() => list.refetch())
                      .catch(setError);
                }}
              >
                <Archive size={15} /> Archive new starts
              </Button>
            )}
          </article>
        ))}
      </div>
      {Boolean(error) && <ErrorState error={error} />}
      <Dialog
        open={importOpen}
        onOpenChange={setImportOpen}
        title="Import a scenario draft."
        description="Paste a private scenario definition. Supported mechanics are allowlisted; validation is required before publication. Maximum size: 2 MiB."
      >
        <div className="stack">
          <label>
            Scenario JSON
            <textarea
              className="json-editor"
              value={source}
              onChange={(e) => setSource(e.target.value)}
            />
          </label>
          <Button
            onClick={() => {
              try {
                const definition: unknown = JSON.parse(source);
                void write<Version>("/admin/scenarios/import", { definition })
                  .then((v) =>
                    nav(
                      `/admin/scenarios/${v.scenario_id}/edit?version=${v.id}`,
                    ),
                  )
                  .catch(setError);
              } catch (e) {
                setError(e);
              }
            }}
          >
            Import as draft
          </Button>
          {Boolean(error) && <ErrorState error={error} />}
        </div>
      </Dialog>
    </div>
  );
}
export function ScenarioEditor() {
  const user = useSession().data;
  const { scenarioId } = useParams();
  const [search] = useSearchParams();
  const vid = search.get("version");
  const nav = useNavigate();
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState<unknown>();
  const [message, setMessage] = useState("");
  const [publishOpen, setPublishOpen] = useState(false);
  const [section, setSection] = useState("Overview");
  const version = useQuery({
    queryKey: ["admin-version", vid],
    queryFn: () => api<Version>(`/admin/scenario-versions/${vid}`),
    enabled: user?.role === "admin",
  });
  if (user?.role !== "admin") return <Navigate to="/missions" />;
  if (version.isPending) return <Loading />;
  if (version.error || !version.data)
    return <ErrorState error={version.error} />;
  const v = version.data;
  let definition: Definition;
  try {
    definition =
      text === null ? v.definition : (JSON.parse(text) as Definition);
  } catch {
    definition = v.definition;
  }
  const readonly = v.status !== "draft";
  async function save() {
    try {
      const d: unknown = JSON.parse(text ?? JSON.stringify(v.definition));
      await write(
        `/admin/scenario-versions/${vid}`,
        { definition: d, draft_revision: v.draft_revision },
        "PUT",
      );
      setText(null);
      await version.refetch();
      setMessage(
        "Draft saved. Validate this new content hash before publication.",
      );
    } catch (e) {
      setError(e);
    }
  }
  async function preview() {
    try {
      const run = await write<RunSummary>(
        `/admin/scenario-versions/${vid}/preview`,
        {},
        "POST",
        crypto.randomUUID(),
      );
      nav(`/runs/${run.id}?branch=${run.active_branch_id}`);
    } catch (e) {
      setError(e);
    }
  }
  function field(name: string, value: string) {
    setText(
      JSON.stringify(
        { ...definition, metadata: { ...definition.metadata, [name]: value } },
        null,
        2,
      ),
    );
  }
  const sections = [
    "Overview",
    "Briefing",
    "Teammates",
    "Facts",
    "Evidence",
    "Objectives",
    "Actions",
    "Rubric",
    "Golden paths",
    "Full JSON",
  ];
  const fields: Record<string, string> = {
    Teammates: "teammates",
    Facts: "facts",
    Evidence: "artifacts",
    Objectives: "metadata",
    Actions: "action_catalog",
    Rubric: "rubric",
    "Golden paths": "golden_commands",
  };
  return (
    <div>
      <Link to="/admin/scenarios" className="text-link">
        ← Scenario studio
      </Link>
      <header className="page-header">
        <div>
          <span className="eyebrow">
            {v.status.toUpperCase()} · VERSION {v.version_number} · REVISION{" "}
            {v.draft_revision}
          </span>
          <h1>{v.definition.metadata.title}</h1>
          <p>
            {readonly
              ? "Published definitions are immutable. Create a draft to edit."
              : "Your preview is an isolated snapshot; later edits will not change it."}
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={() =>
            downloadJson(
              v.definition,
              `${scenarioId}-v${v.version_number}.json`,
            )
          }
        >
          <Download size={16} /> Export JSON
        </Button>
      </header>
      <div className="admin-toolbar">
        <Button
          disabled={readonly || text === null}
          onClick={() => void save()}
        >
          Save draft
        </Button>
        <Button
          variant="secondary"
          disabled={text !== null}
          onClick={() =>
            void write(`/admin/scenario-versions/${vid}/validate`)
              .then(() => version.refetch())
              .catch(setError)
          }
        >
          <Check size={16} /> Validate current hash
        </Button>
        <Button
          variant="secondary"
          disabled={text !== null}
          onClick={() => void preview()}
        >
          <Play size={16} /> Isolated preview
        </Button>
        <Button
          disabled={
            readonly || text !== null || v.validated_hash !== v.content_hash
          }
          onClick={() => setPublishOpen(true)}
        >
          Publish version
        </Button>
      </div>
      {message && (
        <p role="status" className="notice success">
          {message}
        </p>
      )}
      {Boolean(error) && <ErrorState error={error} />}
      <div
        className="admin-section-tabs"
        role="group"
        aria-label="Editor sections"
      >
        {sections.map((s) => (
          <button
            key={s}
            aria-pressed={section === s}
            onClick={() => setSection(s)}
          >
            {s}
          </button>
        ))}
      </div>
      <article className="glass content-card">
        {section === "Overview" ? (
          <>
            <label>
              Title
              <input
                disabled={readonly}
                value={definition.metadata.title}
                onChange={(e) => field("title", e.target.value)}
              />
            </label>
            <label>
              Description
              <textarea
                disabled={readonly}
                value={definition.metadata.description}
                onChange={(e) => field("description", e.target.value)}
              />
            </label>
            <label>
              Fictional company
              <input
                disabled={readonly}
                value={definition.metadata.company}
                onChange={(e) => field("company", e.target.value)}
              />
            </label>
          </>
        ) : section === "Briefing" ? (
          <label>
            Mission briefing
            <textarea
              className="json-editor"
              disabled={readonly}
              value={definition.metadata.briefing}
              onChange={(e) => field("briefing", e.target.value)}
            />
          </label>
        ) : (
          <label>
            {section === "Full JSON"
              ? "Complete scenario definition"
              : `${section} (edit in Full JSON)`}
            <textarea
              className="json-editor"
              readOnly={readonly || section !== "Full JSON"}
              value={
                section === "Full JSON"
                  ? (text ?? JSON.stringify(v.definition, null, 2))
                  : JSON.stringify(definition[fields[section]], null, 2)
              }
              onChange={(e) => setText(e.target.value)}
            />
          </label>
        )}
        <small>
          Strict server schema and deterministic checks are authoritative. Raw
          HTML, remote fetches, scripts and unregistered mechanics are rejected.
        </small>
      </article>
      {v.validation_report && (
        <article className="glass content-card settings-section">
          <h2>
            <ShieldCheck size={22} />{" "}
            {v.validation_report.passed
              ? "Validation passed"
              : "Validation failed"}
          </h2>
          <p>
            Golden path: score {v.validation_report.golden_score}, logical time{" "}
            {v.validation_report.golden_time}.
          </p>
          <code className="hash-text">
            Hash: {v.validated_hash ?? v.content_hash}
          </code>
          {v.validation_report.errors.map((e) => (
            <p className="field-error" key={e}>
              {e}
            </p>
          ))}
        </article>
      )}
      <Dialog
        open={publishOpen}
        onOpenChange={setPublishOpen}
        title="Publish this validated version?"
        description="New runs will use this immutable version. Existing runs stay pinned to their original definition."
      >
        <Button
          onClick={() =>
            void write(`/admin/scenario-versions/${vid}/publish`)
              .then(() => {
                setPublishOpen(false);
                return version.refetch();
              })
              .catch(setError)
          }
        >
          Publish validated version
        </Button>
      </Dialog>
    </div>
  );
}
export function AdminPreview() {
  const [search] = useSearchParams();
  const nav = useNavigate();
  const [error, setError] = useState<unknown>();
  const [requestKey] = useState(() => crypto.randomUUID());
  useEffect(() => {
    void write<RunSummary>(
      `/admin/scenario-versions/${search.get("version")}/preview`,
      {},
      "POST",
      requestKey,
    )
      .then((r) =>
        nav(`/runs/${r.id}?branch=${r.active_branch_id}`, { replace: true }),
      )
      .catch(setError);
  }, [search, nav, requestKey]);
  return error ? (
    <ErrorState error={error} />
  ) : (
    <Loading label="Creating isolated preview…" />
  );
}
export function Operations() {
  const user = useSession().data;
  const data = useQuery({
    queryKey: ["operations"],
    queryFn: () =>
      api<{
        ai_jobs: Record<string, number>;
        email_jobs: Record<string, number>;
        oldest_queued_age_seconds: number;
        provider_attempts: number;
        daily_usage: {
          period: string;
          provider_calls_reserved: number;
          tokens_reserved: number;
          tokens_measured: number;
        }[];
      }>("/admin/operations"),
    enabled: user?.role === "admin",
    refetchInterval: 10000,
  });
  if (user?.role !== "admin") return <Navigate to="/missions" />;
  if (data.isPending) return <Loading />;
  if (data.error || !data.data) return <ErrorState error={data.error} />;
  const d = data.data;
  return (
    <div>
      <header className="page-header">
        <div>
          <span className="eyebrow">
            AGGREGATE OPERATIONS · NO PRIVATE CHATS
          </span>
          <h1>Keep practice moving.</h1>
          <p>Queue health and usage counters from PostgreSQL.</p>
        </div>
      </header>
      <div className="metrics-grid">
        <article className="glass metric-card">
          <span>Oldest queued work</span>
          <strong>{d.oldest_queued_age_seconds}s</strong>
        </article>
        <article className="glass metric-card">
          <span>Built-in reply attempts</span>
          <strong>{d.provider_attempts}</strong>
        </article>
      </div>
      <div className="decision-grid settings-section">
        {[
          ["Local teammate jobs", d.ai_jobs],
          ["Email jobs", d.email_jobs],
        ].map(([title, counts]) => (
          <article className="glass content-card" key={String(title)}>
            <h2>{String(title)}</h2>
            {Object.entries(counts).map(([k, v]) => (
              <p key={k}>
                {k}: {v}
              </p>
            ))}
          </article>
        ))}
      </div>
      <div className="glass content-card">
        <h2>Daily local requests</h2>
        <div
          className="table-scroll"
          tabIndex={0}
          role="region"
          aria-label="Scrollable data table"
        >
          <table>
            <thead>
              <tr>
                <th>UTC date</th>
                <th>Requests processed</th>
              </tr>
            </thead>
            <tbody>
              {d.daily_usage.map((u) => (
                <tr key={u.period}>
                  <td>{u.period}</td>
                  <td>{u.provider_calls_reserved}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <small>
          Request limits protect this server from excessive use. Built-in
          replies use no model tokens and incur no API charges.
        </small>
      </div>
    </div>
  );
}
