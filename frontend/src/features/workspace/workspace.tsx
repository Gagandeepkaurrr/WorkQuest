import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import {
  Users,
  Files,
  ListChecks,
  Activity,
  SlidersHorizontal,
  NotebookPen,
  History,
  ArrowLeft,
  Clock,
  GitBranch,
  Lightbulb,
  Check,
  BookOpen,
  Pause,
  Play,
} from "lucide-react";
import { api, write } from "../../lib/api-client";
import type { Artifact, BranchState, RunSummary } from "../../lib/types";
import { Button } from "../../components/ui/button";
import { Dialog } from "../../components/ui/dialog";
import { ErrorState, Loading } from "../../components/feedback/states";
import { panels, useWorkspaceUI, type Panel } from "./ui-store";
import { useWorldCommand } from "./use-world-command";
import { EvidencePanel, EvidenceBody } from "../evidence/evidence-panel";
import { ActionsPanel } from "../actions/actions-panel";
import { TasksPanel } from "./tasks-panel";
import { ServicePanel } from "./service-panel";
import { NotesPanel } from "./notes-panel";
import { BranchControls } from "../branches/branch-controls";
import { TeamPanel } from "../conversations/team-panel";
import { useEventStream } from "../../lib/event-stream";
import { TimelinePanel } from "../timeline/timeline-panel";
const icons = [
  Users,
  Files,
  ListChecks,
  Activity,
  SlidersHorizontal,
  NotebookPen,
  History,
];
export function Workspace() {
  const { runId } = useParams();
  const [search, setSearch] = useSearchParams();
  const nav = useNavigate();
  const ui = useWorkspaceUI();
  const panel = (
    panels.includes(search.get("panel") as Panel)
      ? search.get("panel")
      : ui.panel
  ) as Panel;
  const run = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api<RunSummary>(`/runs/${runId}`),
  });
  const branchId = search.get("branch") ?? run.data?.active_branch_id;
  const state = useQuery({
    queryKey: ["state", branchId],
    queryFn: () => api<BranchState>(`/branches/${branchId}/state`),
    enabled: Boolean(branchId),
    refetchInterval: 15000,
  });
  const connection = useEventStream(branchId);
  const world = state.data?.projected_state;
  const cmd = useWorldCommand(state.data);
  const [evidence, setEvidence] = useState<Artifact | null>(null);
  const [capArtifact, setCapArtifact] = useState<Artifact | null>(null);
  const [finish, setFinish] = useState(false);
  const [help, setHelp] = useState(false);
  const [notice, setNotice] = useState("");
  function choosePanel(p: Panel) {
    ui.setPanel(p);
    setSearch({ branch: branchId ?? "", panel: p }, { replace: true });
  }
  useEffect(() => {
    const listener = (e: KeyboardEvent) => {
      if (e.altKey && e.shiftKey && e.key.match(/^[1-7]$/)) {
        e.preventDefault();
        const p = panels[Number(e.key) - 1];
        ui.setPanel(p);
        setSearch({ branch: branchId ?? "", panel: p }, { replace: true });
      }
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, [branchId, setSearch, ui]);
  async function open(a: Artifact, confirmed = false) {
    if (!a.opened) {
      if (world && world.simulation_time + 1 === 20 && !confirmed) {
        setCapArtifact(a);
        return;
      }
      const response = await cmd.execute("evidence.open", {
        artifact_id: a.id,
      });
      if (!response) return;
    }
    setEvidence(a);
    setCapArtifact(null);
  }
  async function execute(type: string, payload: Record<string, unknown> = {}) {
    const response = await cmd.execute(type, payload);
    if (response) {
      const message =
        typeof response.result.text === "string"
          ? response.result.text
          : typeof response.result.message === "string"
            ? response.result.message
            : "Simulation updated.";
      setNotice(
        message +
          (response.result.automatic_checkpoint_skipped
            ? " No automatic checkpoint was saved because a teammate reply was pending. Save a manual checkpoint once the reply settles."
            : ""),
      );
      if (response.projected_state.finalized && type === "mission.finish")
        nav(`/runs/${runId}/debrief?branch=${branchId}`);
    }
    return response;
  }
  if (run.isPending || state.isPending)
    return <Loading label="Restoring your saved investigation…" />;
  if (run.error || state.error || !state.data || !world)
    return (
      <ErrorState
        error={run.error ?? state.error}
        retry={() => void state.refetch()}
      />
    );
  if (state.data.run_id !== runId)
    return (
      <ErrorState
        error={
          new Error(
            "This approach belongs to another run. Open it from your mission board.",
          )
        }
      />
    );
  const disabled = cmd.busy || cmd.uncertain || state.data.status !== "active";
  return (
    <div className="workspace-page">
      <Link className="text-link" to="/missions">
        <ArrowLeft size={15} /> Mission board
      </Link>
      <header className="mission-header">
        <div>
          <span className="eyebrow">
            {state.data.is_admin_preview ? "ADMIN PREVIEW · " : ""}SIMULATED
            WORKPLACE
          </span>
          <h1>{state.data.scenario_title}</h1>
          <div className="row">
            <span className="small muted">
              <GitBranch size={13} /> {state.data.label}
            </span>
            <span className="tag">
              {state.data.practice_mode ? "REPEAT PRACTICE" : "FIRST APPROACH"}
            </span>
            <span className="small muted">
              {state.isFetching
                ? "Syncing…"
                : connection === "live"
                  ? "Live · progress saved"
                  : "Reconnecting · saved snapshot"}
            </span>
          </div>
        </div>
        <div className="mission-controls">
          <span className="clock-pill">
            <Clock size={16} />
            <strong>{world.simulation_time}</strong> / 20 <small>sim min</small>
          </span>
          <Button
            variant="secondary"
            size="small"
            onClick={() => setHelp(true)}
          >
            <BookOpen size={15} /> Guide
          </Button>
          {state.data.status === "finalized" ? (
            <Button asChild size="small">
              <Link to={`/runs/${runId}/debrief?branch=${branchId}`}>
                View debrief <Check size={15} />
              </Link>
            </Button>
          ) : (
            <Button
              size="small"
              disabled={disabled}
              onClick={() => setFinish(true)}
            >
              Finish attempt
            </Button>
          )}
        </div>
      </header>
      <BranchControls state={state.data} />
      <div className="workspace-toolbar glass">
        <span className="small">
          <span className="live-dot" /> Logical time moves only when you act.
        </span>
        <div className="row">
          <Button
            variant="ghost"
            size="small"
            disabled={disabled}
            onClick={() => void execute("mission.hint")}
          >
            <Lightbulb size={15} /> Hint ({world.hints.length})
          </Button>
          {state.data.status !== "finalized" && (
            <Button
              variant="ghost"
              size="small"
              disabled={cmd.busy || cmd.uncertain}
              onClick={() =>
                void write(
                  `/branches/${branchId}/${state.data.status === "paused" ? "resume" : "pause"}`,
                  { expected_state_revision: state.data!.state_revision },
                  "POST",
                  crypto.randomUUID(),
                )
                  .then(() => state.refetch())
                  .catch((e) => setNotice(String(e)))
              }
            >
              {state.data.status === "paused" ? (
                <Play size={15} />
              ) : (
                <Pause size={15} />
              )}{" "}
              {state.data.status === "paused" ? "Resume" : "Pause"}
            </Button>
          )}
        </div>
      </div>
      {state.data.status === "paused" && (
        <div className="notice">
          This branch is paused. Resume when you’re ready; wall time has no
          score impact.
        </div>
      )}
      {cmd.uncertain && (
        <div className="notice error" role="alert">
          The last command’s outcome is uncertain. Resolve it before making
          another move.
          <Button
            variant="secondary"
            onClick={() => void cmd.recover()}
            disabled={cmd.busy}
          >
            Recover previous request
          </Button>
        </div>
      )}
      {Boolean(cmd.error) && <ErrorState error={cmd.error} />}
      <p className="workspace-announcement" role="status" aria-live="polite">
        {notice}
      </p>
      <div className="workspace-grid">
        <nav className="workspace-nav" aria-label="Workspace panels">
          {panels.map((p, i) => {
            const Icon = icons[i];
            return (
              <button
                key={p}
                className={panel === p ? "active" : ""}
                aria-current={panel === p ? "page" : undefined}
                onClick={() => choosePanel(p)}
              >
                <Icon size={19} />
                <span>{p}</span>
              </button>
            );
          })}
        </nav>
        <section className="workspace-panel" key={branchId}>
          {panel === "Team" ? (
            <TeamPanel state={state.data} onEvidence={(a) => void open(a)} />
          ) : panel === "Evidence" ? (
            <EvidencePanel
              state={state.data}
              onOpen={(a) => void open(a)}
              disabled={disabled}
            />
          ) : panel === "Tasks" ? (
            <TasksPanel
              key={state.data.state_revision}
              world={world}
              execute={execute}
              disabled={disabled}
            />
          ) : panel === "Service" ? (
            <ServicePanel world={world} />
          ) : panel === "Actions" ? (
            <ActionsPanel world={world} execute={execute} disabled={disabled} />
          ) : panel === "Notes" ? (
            <NotesPanel key={branchId} branchId={branchId!} />
          ) : (
            <TimelinePanel branchId={branchId!} />
          )}
        </section>
      </div>
      <Dialog
        open={Boolean(evidence)}
        onOpenChange={(o) => {
          if (!o) setEvidence(null);
        }}
        title={evidence?.title ?? "Evidence"}
        description="Historical evidence · Reopening is free."
      >
        {evidence && (
          <EvidenceBody branchId={branchId!} artifactId={evidence.id} />
        )}
      </Dialog>
      <Dialog
        open={Boolean(capArtifact)}
        onOpenChange={(o) => {
          if (!o) setCapArtifact(null);
        }}
        title="This evidence ends the attempt."
        description="The first open costs one simulated minute and reaches the 20-minute logical cap. The server will finalize a partial assessment after opening."
      >
        <Button
          onClick={() => {
            if (capArtifact) void open(capArtifact, true);
          }}
        >
          Open evidence and end attempt
        </Button>
      </Dialog>
      <Dialog
        open={finish}
        onOpenChange={setFinish}
        title="Ready to reflect?"
        description="Finishing seals this branch and calculates your practice assessment. You can still try another approach from a saved checkpoint. Record your final recap in Tasks first."
      >
        <Button
          disabled={disabled}
          onClick={() =>
            void execute("mission.finish").then(() => setFinish(false))
          }
        >
          Finish and view assessment
        </Button>
      </Dialog>
      <Dialog
        open={help}
        onOpenChange={setHelp}
        title="A little orientation."
        description="There’s no stopwatch. Read, think and talk at your pace."
      >
        <div className="stack">
          <p>
            First evidence opens cost one simulated minute. Reopens, chat and
            notes are free. Actions show their exact logical cost before
            confirmation.
          </p>
          <p>
            Use Team for conversation, Evidence for clues, Tasks for structured
            decisions, Service for current metrics, and Actions for simulated
            operations.
          </p>
          <p>
            Keyboard: Alt + Shift + 1–7 switches panels. Tab moves through
            controls. Escape closes dialogs.
          </p>
          <p>
            Assessment: diagnosis 20 · outcome 40 · verification 20 ·
            communication 10 · judgment 10. Hints are recorded without a score
            penalty.
          </p>
          <Button onClick={() => setHelp(false)}>Let’s investigate</Button>
        </div>
      </Dialog>
    </div>
  );
}
