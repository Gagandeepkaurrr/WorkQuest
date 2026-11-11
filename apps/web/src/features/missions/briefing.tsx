import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router";
import { useState } from "react";
import {
  ArrowLeft,
  ArrowUpRight,
  Check,
  Clock,
  GitBranch,
  ShieldCheck,
} from "lucide-react";
import { durableWrite } from "../../lib/durable-write";
import { api } from "../../lib/api-client";
import type { Mission, RunSummary } from "../../lib/types";
import { Button } from "../../components/ui/button";
import { ErrorState, Loading } from "../../components/feedback/states";
export function Briefing() {
  const { slug } = useParams();
  const nav = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const mission = useQuery({
    queryKey: ["mission", slug],
    queryFn: () => api<Mission>(`/missions/${slug}`),
  });
  const runs = useQuery({
    queryKey: ["runs"],
    queryFn: () => api<{ items: RunSummary[] }>("/runs"),
  });
  if (mission.isPending) return <Loading />;
  if (mission.error || !mission.data)
    return <ErrorState error={mission.error} />;
  const m = mission.data;
  const owned = runs.data?.items.filter(
    (r) => r.scenario_slug === slug && !r.archived,
  );
  async function start() {
    setBusy(true);
    try {
      const r = await durableWrite<RunSummary>(
        `start:${m.version_id}`,
        "/runs",
        { scenario_version_id: m.version_id },
      );
      nav(`/runs/${r.id}?branch=${r.active_branch_id}`);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="briefing-page">
      <Link to="/missions" className="text-link">
        <ArrowLeft size={16} /> Back to your mission board
      </Link>
      <header className="page-header">
        <div>
          <span className="eyebrow">YOUR BRIEFING · {m.company}</span>
          <h1>{m.title}</h1>
          <p>{m.description}</p>
        </div>
      </header>
      <div className="briefing-grid">
        <article className="glass content-card">
          <span className="tag">SIMULATED WORKPLACE</span>
          <h2>You’re on the team.</h2>
          <p className="prose">{m.briefing}</p>
          <h3>Your objectives</h3>
          <ul className="objective-list">
            {m.objectives.map((o) => (
              <li key={o}>
                <Check size={17} />
                {o}
              </li>
            ))}
          </ul>
          <h3>A team in your corner.</h3>
          <div className="teammate-intro">
            <span className="avatar blue">M</span>
            <div>
              <strong>Maya</strong>
              <small>Platform engineer · AI teammate</small>
            </div>
            <span className="avatar">L</span>
            <div>
              <strong>Leo</strong>
              <small>Product / data engineer · AI teammate</small>
            </div>
          </div>
        </article>
        <aside className="stack">
          <article className="glass content-card">
            <span className="eyebrow">MAKE YOUR FIRST MOVE</span>
            <h3>
              {m.difficulty} · {m.role}
            </h3>
            <p className="row">
              <Clock size={16} />
              {m.duration} at your pace
            </p>
            <div className="skill-tags">
              {m.tags.map((t) => (
                <span key={t}>{t}</span>
              ))}
            </div>
            <Button onClick={() => void start()} disabled={busy}>
              {busy
                ? "Creating your run…"
                : owned?.length
                  ? "Start a fresh run"
                  : "Enter the workplace"}{" "}
              <ArrowUpRight size={18} />
            </Button>
            <small>Starting a fresh run keeps your previous attempts.</small>
            {Boolean(error) && <ErrorState error={error} />}
          </article>
          <article className="glass content-card compact">
            <h3>
              <GitBranch size={20} /> A different choice is always possible.
            </h3>
            <p>
              Checkpoints preserve your work. Trying another approach creates an
              independent branch.
            </p>
          </article>
          <div className="notice">
            <ShieldCheck size={20} />
            <p>
              All actions, services and consequences are simulated. Chat cannot
              execute an operation.
            </p>
          </div>
          {owned?.map((r) => (
            <Link
              className="glass previous-run"
              key={r.id}
              to={`/runs/${r.id}?branch=${r.active_branch_id}`}
            >
              <span>
                {r.status === "finalized" ? "Review" : "Continue"} previous
                approach
              </span>
              <ArrowRightIcon />
            </Link>
          ))}
        </aside>
      </div>
    </div>
  );
}
function ArrowRightIcon() {
  return <ArrowUpRight size={18} />;
}
