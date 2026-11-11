import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import type { WorldState } from "../../lib/types";
import { display, label } from "../../lib/types";
export function ServicePanel({ world }: { world: WorldState }) {
  const m = world.metrics;
  const chartKey =
    "failure_percentage" in m
      ? "failure_percentage"
      : "invalid_reservations" in m
        ? "invalid_reservations"
        : "conversion_july15";
  const numeric = Object.entries(m).filter(
    ([k, v]) => k !== "label" && typeof v !== "object",
  );
  return (
    <div className="stack">
      <div className="panel-heading">
        <h2>What’s actually happening.</h2>
        <p>
          Simulation state · Authoritative metrics from the deterministic
          workload. Reading this panel doesn’t advance time.
        </p>
      </div>
      <div className="metrics-grid">
        {numeric.map(([k, v]) => (
          <article className="glass metric-card" key={k}>
            <span>{label(k)}</span>
            <strong>{display(v)}</strong>
          </article>
        ))}
      </div>
      <article className="glass chart-card">
        <h3>{label(chartKey)} over logical time</h3>
        <div className="chart">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={world.metric_history}>
              <CartesianGrid
                strokeDasharray="3 6"
                vertical={false}
                stroke="#dce2dc"
              />
              <XAxis dataKey="tick" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} width={35} />
              <Tooltip />
              <Line
                type="stepAfter"
                dataKey={chartKey}
                stroke="#3154df"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <details>
          <summary>Accessible metric history table</summary>
          <div
            className="table-scroll"
            tabIndex={0}
            role="region"
            aria-label="Scrollable data table"
          >
            <table>
              <thead>
                <tr>
                  <th>Simulated minute</th>
                  <th>{label(chartKey)}</th>
                </tr>
              </thead>
              <tbody>
                {world.metric_history.map((r, i) => (
                  <tr key={i}>
                    <td>{display(r.tick)}</td>
                    <td>{display(r[chartKey])}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </article>
      {Array.isArray(m.rows) && (
        <article className="glass content-card">
          <h3>Materialized report · simulation state</h3>
          <pre>{JSON.stringify(m.rows, null, 2)}</pre>
        </article>
      )}
      <section className="verification-list">
        <h3>Verification checks</h3>
        {Object.keys(world.verifications).length === 0 ? (
          <p>No checks have been run yet.</p>
        ) : (
          Object.entries(world.verifications).map(([id, v]) => (
            <div className="glass verification-item" key={id}>
              <strong>{label(id)}</strong>
              <span
                className={`tag ${v.passed && v.current ? "green" : "amber"}`}
              >
                {!v.current ? "STALE" : v.passed ? "PASS" : "FAIL"}
              </span>
              <p>{v.detail}</p>
            </div>
          ))
        )}
      </section>
    </div>
  );
}
