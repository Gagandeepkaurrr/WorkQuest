import { useQuery } from "@tanstack/react-query";
import { useParams, useSearchParams, Link } from "react-router";
import { useState } from "react";
import {
  ArrowLeft,
  Printer,
  Download,
  GitBranch,
  Sparkles,
  CheckCircle2,
} from "lucide-react";
import type { components } from "../../generated/api-types";
import type { BranchState } from "../../lib/types";
import { label } from "../../lib/types";
import { api, write } from "../../lib/api-client";
import { Button } from "../../components/ui/button";
import { ErrorState, Loading } from "../../components/feedback/states";
import { BranchControls } from "../branches/branch-controls";
import { ShareDialog } from "../reports/share-dialog";
export type Report = components["schemas"]["ReportView"];
import { downloadJson } from "../../lib/download";
export function Debrief() {
  const { runId } = useParams();
  const [search] = useSearchParams();
  const branch = search.get("branch");
  const [error, setError] = useState<unknown>();
  const [replay, setReplay] = useState<{
    matched: boolean;
    state_hash: string;
  } | null>(null);
  const result = useQuery({
    queryKey: ["scorecard", branch],
    queryFn: () => api<Report>(`/branches/${branch}/scorecard`),
    refetchInterval: (q) =>
      q.state.data?.coaching_status === "queued" ? 3000 : false,
  });
  const state = useQuery({
    queryKey: ["state", branch],
    queryFn: () => api<BranchState>(`/branches/${branch}/state`),
  });
  if (result.isPending)
    return <Loading label="Preparing your practice assessment…" />;
  if (result.error || !result.data) return <ErrorState error={result.error} />;
  const r = result.data;
  return (
    <div className="print-report">
      <Link
        className="text-link no-print"
        to={`/runs/${runId}?branch=${branch}`}
      >
        <ArrowLeft size={16} /> Back to your investigation
      </Link>
      <header className="page-header">
        <div>
          <span className="eyebrow">
            PRACTICE ASSESSMENT ·{" "}
            {r.practice_mode ? "REPEAT PRACTICE" : "FIRST ATTEMPT"}
          </span>
          <h1>Every decision teaches you.</h1>
          <p>
            {r.title} · Version {r.version} · {r.hints_used.length} hints used
          </p>
        </div>
        <div className="row no-print">
          <Button variant="secondary" onClick={() => window.print()}>
            <Printer size={16} /> Print
          </Button>
          <Button
            variant="ghost"
            onClick={() => downloadJson(r, "workquest-report.json")}
          >
            <Download size={16} /> JSON
          </Button>
        </div>
      </header>
      <div className="debrief-grid">
        <article className="glass score-card">
          <span className="eyebrow">YOUR PRACTICE SCORE</span>
          <div className="score-display">
            {r.total_score}
            <small>/ 100</small>
          </div>
          <span
            className={`tag ${r.outcome === "successful" ? "green" : "amber"}`}
          >
            {r.outcome}
          </span>
          <p>
            {r.simulation_time} simulated minutes.
            <br />
            Your reading speed never affects this score.
          </p>
          <small>Calculated by the server’s deterministic rubric.</small>
        </article>
        <article className="glass criteria-card">
          <h2>The decisions behind the score.</h2>
          {r.criteria.map((c) => (
            <div className="criterion" key={c.criterion_id}>
              <div className="row between">
                <strong>{c.title}</strong>
                <span>
                  {c.awarded_points}
                  <small> / {c.maximum_points}</small>
                </span>
              </div>
              <div className="criterion-track">
                <span
                  style={{
                    width: `${(c.awarded_points / c.maximum_points) * 100}%`,
                  }}
                />
              </div>
              <p>{c.explanation}</p>
              <details>
                <summary>
                  Supporting recorded events ({c.supporting_origin_ids.length})
                </summary>
                <ul>
                  {c.supporting_origin_ids.map((id) => (
                    <li key={id}>
                      <code>{id}</code>
                    </li>
                  ))}
                </ul>
              </details>
            </div>
          ))}
        </article>
      </div>
      <div className="decision-grid debrief-details">
        <article className="glass content-card">
          <span className="eyebrow">CONNECTING THE EVIDENCE</span>
          <h3>What was going on.</h3>
          <p>{r.explanation}</p>
          <h3>
            {r.missed_checks.length
              ? "Checks to revisit"
              : "You closed the loop."}
          </h3>
          {r.missed_checks.length ? (
            <ul className="plain-list">
              {r.missed_checks.map((c) => (
                <li key={c}>{label(c)}</li>
              ))}
            </ul>
          ) : (
            <p className="row">
              <CheckCircle2 size={18} /> Every outcome and verification check is
              complete.
            </p>
          )}
        </article>
        <article className="glass content-card">
          <span className="eyebrow">OPTIONAL AI COACHING</span>
          <h3>A little perspective.</h3>
          <p>
            {r.coaching_text ??
              "Your assessment is complete. Optional coaching can help you reflect on the tradeoffs; it cannot change your score."}
          </p>
          {r.coaching_status === "queued" ? (
            <p role="status">Coaching queued. Your results are ready above.</p>
          ) : (
            <Button
              variant="secondary"
              onClick={() =>
                void write(
                  `/branches/${branch}/coaching/retry`,
                  {},
                  "POST",
                  crypto.randomUUID(),
                )
                  .then(() => result.refetch())
                  .catch(setError)
              }
            >
              <Sparkles size={16} />{" "}
              {r.coaching_text
                ? "Request another coaching attempt"
                : "Request coaching"}
            </Button>
          )}
          <small>
            AI commentary is separate from server-calculated findings.
          </small>
        </article>
      </div>
      <article className="glass content-card">
        <h3>Your action sequence.</h3>
        <div
          className="table-scroll"
          tabIndex={0}
          role="region"
          aria-label="Scrollable data table"
        >
          <table>
            <thead>
              <tr>
                <th>Minute</th>
                <th>Decision</th>
                <th>Inputs</th>
              </tr>
            </thead>
            <tbody>
              {r.action_sequence.map((a, i) => (
                <tr key={i}>
                  <td>{String(a.logical_tick)}</td>
                  <td>{label(String(a.type))}</td>
                  <td>
                    <code>{JSON.stringify(a.payload)}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="no-print">
          <Button
            variant="secondary"
            onClick={() =>
              void api<{ matched: boolean; state_hash: string }>(
                `/branches/${branch}/replay`,
              )
                .then(setReplay)
                .catch(setError)
            }
          >
            Verify recorded replay
          </Button>
          {replay && (
            <p role="status">
              Replay{" "}
              {replay.matched
                ? "matches the saved state"
                : "did not match — report this issue"}
              . No operations or AI calls were repeated.
            </p>
          )}
        </div>
      </article>
      <section className="glass retry-banner no-print">
        <div>
          <GitBranch size={26} />
          <h2>What would you do differently?</h2>
          <p>
            Try another path from a saved checkpoint. This result stays intact.
          </p>
        </div>
        {state.data && <BranchControls state={state.data} />}
      </section>
      <div className="row no-print">
        {!r.is_demo && !r.is_admin_preview && (
          <ShareDialog branchId={branch!} />
        )}
        <Button asChild variant="ghost">
          <Link to="/progress">View your progress</Link>
        </Button>
      </div>
      {Boolean(error) && <ErrorState error={error} />}
    </div>
  );
}
