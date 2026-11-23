import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import {
  ArrowUpRight,
  ArrowRight,
  Search,
  Clock,
  ShoppingBag,
  Boxes,
  ChartNoAxesCombined,
  GitBranch,
  Sparkles,
} from "lucide-react";
import { api } from "../../lib/api-client";
import { durableWrite } from "../../lib/durable-write";
import type { Mission, RunSummary } from "../../lib/types";
import { Button } from "../../components/ui/button";
import { ErrorState, Loading } from "../../components/feedback/states";
import { useSession } from "../auth/use-session";
export function Library() {
  const [query, setQuery] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [archiveError, setArchiveError] = useState<unknown>();
  const [archiving, setArchiving] = useState<string | null>(null);
  const user = useSession().data;
  const missions = useQuery({
    queryKey: ["missions", query, difficulty],
    queryFn: () =>
      api<{ items: Mission[] }>(
        `/missions?q=${encodeURIComponent(query)}&difficulty=${difficulty}`,
      ),
  });
  const runs = useInfiniteQuery({
    queryKey: ["runs", "paged"],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      api<{ items: RunSummary[]; next_offset: number | null }>(
        `/runs?offset=${pageParam}`,
      ),
    getNextPageParam: (last) => last.next_offset,
  });
  const allRuns = runs.data?.pages.flatMap((page) => page.items) ?? [];
  async function archive(run: RunSummary) {
    setArchiving(run.id);
    setArchiveError(undefined);
    try {
      await durableWrite(`archive:${run.id}`, `/runs/${run.id}/archive`, {});
      await runs.refetch();
    } catch (error) {
      setArchiveError(error);
    } finally {
      setArchiving(null);
    }
  }
  const current = allRuns.find(
    (r) => r.status === "active" && !r.archived && !r.is_admin_preview,
  );
  return (
    <div className="library-page">
      <header className="page-header">
        <div>
          <span className="eyebrow">A LITTLE PRACTICE. A NEW PERSPECTIVE.</span>
          <h1>Your next good decision.</h1>
          <p>
            Hey {user?.display_name.split(" ")[0]}. Make space for some hands-on
            learning.
          </p>
        </div>
        <span className="date-stamp">
          <Sparkles size={16} /> Built for your curiosity
        </span>
      </header>
      <section className="library-banner glass">
        <div>
          <span className="pill">
            <span className="live-dot" /> YOUR PRACTICE, YOUR PACE
          </span>
          <h2>
            The best way to understand it?
            <br />
            <span className="serif-accent">Be the one who works it out.</span>
          </h2>
          <p>
            Investigate with a team. Make a call. Try another path.
            <br />
            Every mission is a safe place to build your instincts.
          </p>
        </div>
        <div className="banner-branch" aria-hidden="true">
          <span className="branch-node">A</span>
          <GitBranch size={74} strokeWidth={1} />
          <span className="branch-node mint">B</span>
          <span className="small">One moment. More possibilities.</span>
        </div>
      </section>
      {current && (
        <section className="continue-card glass">
          <div className="continue-icon">
            <Clock size={21} />
          </div>
          <div>
            <span className="eyebrow">RIGHT WHERE YOU LEFT OFF</span>
            <h3>{current.scenario_title}</h3>
            <p>
              {current.simulation_time} simulated minutes ·{" "}
              {current.practice_mode ? "Repeat practice" : "First approach"}
            </p>
          </div>
          <Button asChild variant="secondary">
            <Link to={`/runs/${current.id}?branch=${current.active_branch_id}`}>
              Continue <ArrowRight size={16} />
            </Link>
          </Button>
        </section>
      )}
      <section aria-labelledby="mission-heading">
        <div className="section-heading">
          <div>
            <span className="eyebrow">THE MISSION BOARD</span>
            <h2 id="mission-heading">Pick something to figure out.</h2>
          </div>
          <span className="small muted">
            Solo missions · Fictional workplaces
          </span>
        </div>
        <div className="filters">
          <label className="search-field">
            <Search size={17} />
            <input
              aria-label="Search missions"
              placeholder="Find a mission or a skill…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <select
            aria-label="Difficulty"
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value)}
          >
            <option value="">All levels</option>
            <option>Beginner</option>
            <option>Intermediate</option>
          </select>
        </div>
        <div className="mission-board pegboard">
          {missions.isPending ? (
            <Loading label="Finding your missions…" />
          ) : missions.error ? (
            <ErrorState error={missions.error} />
          ) : missions.data?.items.length === 0 ? (
            <div className="empty">
              <h3>No missions match that search.</h3>
              <p>Try another skill or clear the filters.</p>
            </div>
          ) : (
            <div className="mission-grid">
              {missions.data?.items.map((m, index) => {
                const icons = [ShoppingBag, Boxes, ChartNoAxesCombined];
                const Icon = icons[index % icons.length];
                const own = allRuns.find(
                  (r) =>
                    r.scenario_slug === m.slug &&
                    !r.archived &&
                    r.status === "active",
                );
                const locked = Boolean(
                  user?.is_demo && m.slug !== "checkout-outage",
                );
                return (
                  <article
                    className={`mission-card glass tone-${index % 3}`}
                    key={m.id}
                  >
                    <span className="pin" />
                    <div className="row between">
                      <span className="mission-icon">
                        <Icon size={26} />
                      </span>
                      <span className="mission-number">
                        CASE {String(index + 1).padStart(2, "0")}
                      </span>
                    </div>
                    <div className="mission-meta">
                      <span>{m.difficulty}</span>
                      <span>·</span>
                      <span>{m.role}</span>
                    </div>
                    <h3>{m.title}</h3>
                    <p>{m.description}</p>
                    <div className="skill-tags">
                      {m.tags.map((tag) => (
                        <span key={tag}>{tag}</span>
                      ))}
                    </div>
                    <div className="mission-card-bottom">
                      <span className="small muted">
                        <Clock size={13} /> {m.duration}
                      </span>
                      <Button asChild size="small" variant="ghost">
                        <Link
                          to={
                            locked
                              ? "/sign-up"
                              : own
                                ? `/runs/${own.id}?branch=${own.active_branch_id}`
                                : `/missions/${m.slug}`
                          }
                        >
                          {locked
                            ? "Create account"
                            : own
                              ? "Continue"
                              : "View mission"}{" "}
                          <ArrowUpRight size={17} />
                        </Link>
                      </Button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </section>
      {runs.error && <ErrorState error={runs.error} />}
      {allRuns.length > 0 && (
        <section
          className="stack content-card glass"
          aria-labelledby="saved-runs-heading"
        >
          <div>
            <h2 id="saved-runs-heading">Your saved missions.</h2>
            <p>
              Archive an older run to make room for a new one. Its results and
              branches stay available.
            </p>
          </div>
          {allRuns.map((run) => (
            <div className="row between" key={run.id}>
              <Link
                className="text-link"
                to={`/runs/${run.id}?branch=${run.active_branch_id}`}
              >
                {run.scenario_title} · {run.status}
                {run.is_admin_preview ? " · Preview" : ""}
              </Link>
              {run.archived ? (
                <span className="tag">Archived</span>
              ) : (
                <Button
                  variant="ghost"
                  size="small"
                  disabled={archiving !== null}
                  aria-label={`Archive ${run.scenario_title}`}
                  onClick={() => void archive(run)}
                >
                  {archiving === run.id ? "Archiving…" : "Archive"}
                </Button>
              )}
            </div>
          ))}
          {Boolean(archiveError) && <ErrorState error={archiveError} />}
          {runs.hasNextPage && (
            <Button
              variant="secondary"
              disabled={runs.isFetchingNextPage}
              onClick={() => void runs.fetchNextPage()}
            >
              Load older runs
            </Button>
          )}
        </section>
      )}
      <div className="library-footer">
        <GitBranch size={18} />
        <p>
          There’s more than one way through. Save a checkpoint and try the
          decision you didn’t take.
        </p>
      </div>
    </div>
  );
}
