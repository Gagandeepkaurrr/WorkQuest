import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, FileText, ArrowUpRight, Check } from "lucide-react";
import { api } from "../../lib/api-client";
import type { Artifact, BranchState } from "../../lib/types";
import { Button } from "../../components/ui/button";
import { ErrorState, Loading } from "../../components/feedback/states";
export function EvidencePanel({
  state,
  onOpen,
  disabled,
}: {
  state: BranchState;
  onOpen: (a: Artifact) => void;
  disabled: boolean;
}) {
  const [q, setQ] = useState("");
  const list = useQuery({
    queryKey: ["artifacts", state.branch_id, state.state_revision, q],
    queryFn: () =>
      api<{ items: Artifact[] }>(
        `/branches/${state.branch_id}/artifacts?q=${encodeURIComponent(q)}`,
      ),
  });
  return (
    <div className="stack">
      <div className="panel-heading">
        <h2>Start with what you can see.</h2>
        <p>
          Evidence unlocks as you investigate. Search only includes available
          titles and content you’ve opened.
        </p>
      </div>
      <label className="search-field">
        <Search size={17} />
        <input
          aria-label="Search available evidence"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search available evidence…"
        />
      </label>
      {list.isPending ? (
        <Loading />
      ) : list.error ? (
        <ErrorState error={list.error} />
      ) : (
        <div className="evidence-grid">
          {list.data?.items.map((a) => (
            <article className="glass evidence-card" key={a.id}>
              <div className="row between">
                <span className="evidence-icon">
                  <FileText size={23} />
                </span>
                <span className="tag">{a.type}</span>
              </div>
              <h3>{a.title}</h3>
              <p>
                {a.opened ? (
                  <>
                    <Check size={14} /> Reopen: no time cost
                  </>
                ) : (
                  "First open: +1 simulated minute"
                )}
              </p>
              <Button
                variant="secondary"
                disabled={disabled && !a.opened}
                onClick={() => onOpen(a)}
              >
                {a.opened ? "Read again" : "Inspect evidence"}{" "}
                <ArrowUpRight size={16} />
              </Button>
            </article>
          ))}
          {list.data?.items.length === 0 && (
            <div className="empty">
              <h3>No available evidence matches.</h3>
              <p>Clear the search or investigate another artifact.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
export function EvidenceBody({
  branchId,
  artifactId,
}: {
  branchId: string;
  artifactId: string;
}) {
  const evidence = useQuery({
    queryKey: ["artifact", branchId, artifactId],
    queryFn: () =>
      api<{ title: string; body: string; type: string; label: string }>(
        `/branches/${branchId}/artifacts/${encodeURIComponent(artifactId)}`,
      ),
  });
  if (evidence.isPending) return <Loading />;
  if (evidence.error || !evidence.data)
    return <ErrorState error={evidence.error} />;
  return (
    <article className="artifact-view">
      <span className="eyebrow">{evidence.data.label}</span>
      <pre className={`evidence-body ${evidence.data.type}`}>
        {evidence.data.body}
      </pre>
      <small>
        Authored evidence is shown as text. It cannot execute commands or load
        remote media.
      </small>
    </article>
  );
}
