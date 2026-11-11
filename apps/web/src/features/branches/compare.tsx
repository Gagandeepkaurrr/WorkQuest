import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router";
import { api } from "../../lib/api-client";
import type { BranchState } from "../../lib/types";
import { label } from "../../lib/types";
import type { Report } from "../debrief/debrief";
import type { BranchSummary } from "./branch-controls";
import { Loading, ErrorState } from "../../components/feedback/states";
type Side = {
  branch: BranchState;
  scorecard: Report | null;
  divergence_checkpoint: string | null;
  actions: { type: string; logical_tick: number }[];
};
export function Compare() {
  const { runId } = useParams();
  const [search, setSearch] = useSearchParams();
  const branches = useQuery({
    queryKey: ["branches", runId],
    queryFn: () => api<{ items: BranchSummary[] }>(`/runs/${runId}/branches`),
  });
  const left = search.get("left") ?? branches.data?.items[0]?.id;
  const right = search.get("right") ?? branches.data?.items[1]?.id;
  const data = useQuery({
    queryKey: ["compare", runId, left, right],
    queryFn: () =>
      api<{ left: Side; right: Side }>(
        `/runs/${runId}/compare?left=${left}&right=${right}`,
      ),
    enabled: Boolean(left && right),
  });
  return (
    <div>
      <header className="page-header">
        <div>
          <span className="eyebrow">TWO PLAYED APPROACHES</span>
          <h1>The difference a decision makes.</h1>
          <p>Actual recorded outcomes. No invented counterfactual results.</p>
        </div>
      </header>
      <div className="comparison-grid">
        {["left", "right"].map((side) => (
          <label key={side}>
            {side === "left" ? "First branch" : "Compare with"}
            <select
              value={side === "left" ? left : right}
              onChange={(e) =>
                setSearch({
                  ...Object.fromEntries(search),
                  [side]: e.target.value,
                })
              }
            >
              {branches.data?.items.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.label} · {b.status}
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>
      {data.isPending ? (
        <Loading />
      ) : data.error ? (
        <ErrorState error={data.error} />
      ) : (
        data.data && (
          <div className="comparison-grid">
            {[data.data.left, data.data.right].map((s, i) => (
              <article className="glass content-card" key={i}>
                <span className="tag">{s.branch.status}</span>
                <h2>{s.branch.label}</h2>
                <div className="score-display">
                  {s.scorecard?.total_score ?? "—"}
                  <small>/ 100</small>
                </div>
                <p>
                  {s.scorecard?.outcome ?? "Not yet assessed"} ·{" "}
                  {s.branch.projected_state.simulation_time} simulated minutes ·{" "}
                  {s.branch.projected_state.hints.length} hints
                </p>
                {s.scorecard?.criteria.map((c) => (
                  <div className="row between" key={c.criterion_id}>
                    <span>{c.title}</span>
                    <strong>
                      {c.awarded_points}/{c.maximum_points}
                    </strong>
                  </div>
                ))}
                <h3>Action sequence</h3>
                <ol className="plain-list">
                  {s.actions.map((a, j) => (
                    <li key={j}>
                      t={a.logical_tick} · {label(a.type)}
                    </li>
                  ))}
                </ol>
                <small>
                  Divergence checkpoint:{" "}
                  {s.divergence_checkpoint ?? "Root approach"}
                </small>
                <Link
                  className="button button-secondary"
                  to={`/runs/${runId}?branch=${s.branch.branch_id}`}
                >
                  Open this branch
                </Link>
              </article>
            ))}
          </div>
        )
      )}
    </div>
  );
}
