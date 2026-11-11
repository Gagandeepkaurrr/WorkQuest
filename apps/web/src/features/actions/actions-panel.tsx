import { useState } from "react";
import {
  SlidersHorizontal,
  Clock,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";
import type { Action, WorldState } from "../../lib/types";
import { Button } from "../../components/ui/button";
import { Dialog } from "../../components/ui/dialog";
export function ActionsPanel({
  world,
  execute,
  disabled,
}: {
  world: WorldState;
  execute: (
    type: string,
    payload?: Record<string, unknown>,
  ) => Promise<unknown>;
  disabled: boolean;
}) {
  const [selected, setSelected] = useState<Action | null>(null);
  const [params, setParams] = useState<Record<string, unknown>>({});
  const [review, setReview] = useState(false);
  function choose(a: Action) {
    setSelected(a);
    setParams(
      Object.fromEntries(
        (a.parameters ?? []).map((p) => [
          p.name,
          p.type === "boolean" ? false : (p.choices ?? [])[0],
        ]),
      ),
    );
    setReview(false);
  }
  return (
    <div className="stack">
      <div className="panel-heading">
        <h2>A deliberate next move.</h2>
        <p>
          Every operation targets a simulated service. Review the cost and
          parameters before committing.
        </p>
      </div>
      <div className="action-grid">
        {world.actions.map((a) => (
          <article key={a.id} className="glass action-card">
            <div className="row between">
              <SlidersHorizontal size={20} />
              <span className="pill">
                <Clock size={12} /> +{a.cost} min
              </span>
            </div>
            <h3>{a.label}</h3>
            <p>{a.description}</p>
            {!a.available && (
              <small>
                {a.missing_evidence.length
                  ? a.missing_evidence.join(", ")
                  : "Not available in the current state or remaining time."}
              </small>
            )}
            <Button
              variant="secondary"
              disabled={disabled || !a.available}
              onClick={() => choose(a)}
            >
              Review operation <ArrowRight size={15} />
            </Button>
          </article>
        ))}
      </div>
      <Dialog
        open={Boolean(selected)}
        onOpenChange={(open) => {
          if (!open) setSelected(null);
        }}
        title={
          review
            ? "Confirm simulated operation"
            : (selected?.label ?? "Operation")
        }
        description={`${selected?.target ?? "Simulated service"} · +${selected?.cost ?? 0} simulated minutes. Outcomes depend on the current state.`}
      >
        {selected && (
          <div className="stack">
            {!review ? (
              (selected.parameters ?? []).map((p) => (
                <label key={p.name}>
                  {p.label}
                  {p.type === "boolean" ? (
                    <select
                      value={String(params[p.name])}
                      onChange={(e) =>
                        setParams({
                          ...params,
                          [p.name]: e.target.value === "true",
                        })
                      }
                    >
                      <option value="false">Disabled</option>
                      <option value="true">Enabled</option>
                    </select>
                  ) : (
                    <select
                      value={String(params[p.name])}
                      onChange={(e) =>
                        setParams({ ...params, [p.name]: e.target.value })
                      }
                    >
                      {(p.choices ?? []).map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                  )}
                </label>
              ))
            ) : (
              <div className="review-summary">
                <strong>{selected.label}</strong>
                {Object.entries(params).map(([k, v]) => (
                  <p key={k}>
                    {k.replaceAll("_", " ")}: {String(v)}
                  </p>
                ))}
                <p>
                  Logical time: {world.simulation_time} →{" "}
                  {world.simulation_time + selected.cost} / 20
                </p>
                {world.simulation_time + selected.cost === 20 && (
                  <div className="notice">
                    This action reaches the logical cap and ends the attempt
                    with a practice assessment.
                  </div>
                )}
              </div>
            )}
            <div className="notice">
              <ShieldCheck size={18} />
              {selected.description}
            </div>
            <Button
              disabled={disabled}
              onClick={() => {
                if (!review) setReview(true);
                else
                  void execute(selected.id, params).then(() =>
                    setSelected(null),
                  );
              }}
            >
              {review
                ? "Execute simulated operation"
                : "Continue to confirmation"}{" "}
              <ArrowRight size={16} />
            </Button>
          </div>
        )}
      </Dialog>
    </div>
  );
}
