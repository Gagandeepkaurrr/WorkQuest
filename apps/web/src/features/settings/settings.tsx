import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import {
  ShieldCheck,
  Download,
  Mail,
  Trash2,
  Monitor,
  Sun,
  Moon,
} from "lucide-react";
import { api, write, bootstrapCsrf } from "../../lib/api-client";
import { useSession } from "../auth/use-session";
import { Button } from "../../components/ui/button";
import { Dialog } from "../../components/ui/dialog";
import { ErrorState, Loading } from "../../components/feedback/states";
import { downloadJson } from "../../lib/download";
import type { Preferences } from "./preferences";
export function Settings() {
  const user = useSession().data;
  const client = useQueryClient();
  const nav = useNavigate();
  const [name, setName] = useState<string | null>(null);
  const [current, setCurrent] = useState("");
  const [password, setPassword] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<unknown>();
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const prefs = useQuery({
    queryKey: ["preferences"],
    queryFn: () => api<Preferences>("/me/preferences"),
  });
  const sessions = useQuery({
    queryKey: ["sessions"],
    queryFn: () =>
      api<{
        items: {
          id: string;
          created_at: string;
          expires_at: string;
          user_agent: string;
          current: boolean;
        }[];
      }>("/auth/sessions"),
  });
  const shares = useQuery({
    queryKey: ["shares"],
    queryFn: () =>
      api<{
        items: {
          id: string;
          title: string;
          expires_at: string;
          revoked: boolean;
          expired: boolean;
        }[];
      }>("/me/shares"),
  });
  async function perform(action: () => Promise<unknown>, success: string) {
    setError(undefined);
    setBusy(true);
    try {
      await action();
      setMessage(success);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  if (!user || prefs.isPending) return <Loading />;
  if (prefs.error || !prefs.data) return <ErrorState error={prefs.error} />;
  return (
    <div className="settings-page">
      <header className="page-header">
        <div>
          <span className="eyebrow">MAKE THIS SPACE YOURS</span>
          <h1>A few personal touches.</h1>
          <p>Manage your profile, preferences, sessions and shared reports.</p>
        </div>
      </header>
      {message && (
        <div className="notice success" role="status">
          {message}
        </div>
      )}
      {Boolean(error) && <ErrorState error={error} />}
      <div className="settings-grid">
        <form
          className="glass content-card"
          onSubmit={(e) => {
            e.preventDefault();
            void perform(async () => {
              await write(
                "/me",
                { display_name: name ?? user.display_name },
                "PATCH",
              );
              await client.invalidateQueries({ queryKey: ["session"] });
            }, "Profile saved.");
          }}
        >
          <h2>Your profile</h2>
          <label>
            Display name
            <input
              value={name ?? user.display_name}
              required
              maxLength={80}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <p>{user.is_demo ? "Short-lived demo identity" : user.email}</p>
          <span className="row small">
            <ShieldCheck size={17} />
            {user.email_verified
              ? "Email verified"
              : user.is_demo
                ? "Demo · fixture-only access"
                : "Email not yet verified"}
          </span>
          {!user.email_verified && !user.is_demo && (
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                void perform(
                  () => write("/auth/resend-verification"),
                  "Verification email queued.",
                )
              }
            >
              <Mail size={16} /> Resend verification
            </Button>
          )}
          <Button disabled={busy}>Save profile</Button>
        </form>
        <article className="glass content-card">
          <h2>Your environment</h2>
          <label>
            Color theme
            <select
              value={prefs.data.theme}
              onChange={(e) =>
                void perform(async () => {
                  await write(
                    "/me/preferences",
                    { ...prefs.data, theme: e.target.value },
                    "PATCH",
                  );
                  await prefs.refetch();
                }, "Theme saved.")
              }
            >
              <option value="light">White glass</option>
              <option value="dark">Deep ink</option>
            </select>
          </label>
          <div className="row">
            <Sun size={20} />
            <span className="small muted">Light, calm and clear.</span>
            <Moon size={20} />
          </div>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={prefs.data.reduced_motion}
              onChange={(e) =>
                void perform(async () => {
                  await write(
                    "/me/preferences",
                    { ...prefs.data, reduced_motion: e.target.checked },
                    "PATCH",
                  );
                  await prefs.refetch();
                }, "Motion preference saved.")
              }
            />{" "}
            Reduce motion
          </label>
          <Button
            variant="ghost"
            onClick={() =>
              void perform(async () => {
                await write(
                  "/me/preferences",
                  { ...prefs.data, onboarding_completed: false },
                  "PATCH",
                );
                await prefs.refetch();
              }, "The first-run guide is visible again.")
            }
          >
            Show orientation again
          </Button>
        </article>
        {!user.is_demo && (
          <form
            className="glass content-card"
            onSubmit={(e) => {
              e.preventDefault();
              void perform(async () => {
                await write("/auth/change-password", {
                  current_password: current,
                  password,
                });
                await bootstrapCsrf();
                setCurrent("");
                setPassword("");
                await sessions.refetch();
              }, "Password changed. Other sessions were revoked.");
            }}
          >
            <h2>Password & security</h2>
            <label>
              Current password
              <input
                type="password"
                autoComplete="current-password"
                required
                maxLength={256}
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
              />
            </label>
            <label>
              New password
              <input
                type="password"
                autoComplete="new-password"
                required
                minLength={12}
                maxLength={256}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <small>12–256 characters. A long passphrase works well.</small>
            </label>
            <Button disabled={busy}>Change password</Button>
          </form>
        )}
        <article className="glass content-card">
          <h2>Active sessions</h2>
          {sessions.data?.items.map((s) => (
            <div className="session-item" key={s.id}>
              <Monitor size={19} />
              <div>
                <strong>
                  {s.current ? "This browser" : "Another session"}
                </strong>
                <small>
                  Started {new Date(s.created_at).toLocaleDateString()} ·
                  expires {new Date(s.expires_at).toLocaleDateString()}
                </small>
                <small>{s.user_agent.slice(0, 70)}</small>
              </div>
              <Button
                variant="ghost"
                size="small"
                onClick={() =>
                  void perform(async () => {
                    await api(`/auth/sessions/${s.id}`, { method: "DELETE" });
                    if (s.current) {
                      for (const key of Object.keys(sessionStorage))
                        if (key.startsWith("wq:"))
                          sessionStorage.removeItem(key);
                      client.clear();
                      nav("/sign-in");
                    } else await sessions.refetch();
                  }, "Session revoked.")
                }
              >
                Revoke
              </Button>
            </div>
          ))}
          {sessions.error && <ErrorState error={sessions.error} />}
        </article>
      </div>
      <article className="glass content-card settings-section">
        <h2>Shared report links</h2>
        <p>Links are off by default. Revocation takes effect immediately.</p>
        {shares.data?.items.length === 0 ? (
          <p className="small">You have no shared reports.</p>
        ) : (
          shares.data?.items.map((s) => (
            <div className="session-item" key={s.id}>
              <div>
                <strong>{s.title}</strong>
                <small>
                  {s.revoked
                    ? "Revoked"
                    : s.expired
                      ? "Expired"
                      : `Expires ${new Date(s.expires_at).toLocaleDateString()}`}
                </small>
              </div>
              {!s.revoked && !s.expired && (
                <Button
                  variant="secondary"
                  size="small"
                  onClick={() =>
                    void perform(async () => {
                      await api(`/shares/${s.id}`, { method: "DELETE" });
                      await shares.refetch();
                    }, "Report link revoked.")
                  }
                >
                  Revoke link
                </Button>
              )}
            </div>
          ))
        )}
      </article>
      {!user.is_demo && (
        <article className="glass content-card settings-section">
          <h2>Your data stays yours.</h2>
          <p>
            Export your visible activity, saved notes and practice results.
            Deleting your account immediately revokes access and removes owned
            records; retained backups expire under the documented 30-day policy.
          </p>
          <div className="row">
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() =>
                void perform(
                  async () =>
                    downloadJson(
                      await api("/me/export"),
                      "workquest-account.json",
                    ),
                  "Export downloaded.",
                )
              }
            >
              <Download size={16} /> Export my data
            </Button>
            <Button variant="danger" onClick={() => setDeleteOpen(true)}>
              <Trash2 size={16} /> Delete account
            </Button>
          </div>
        </article>
      )}
      <Dialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete your WorkQuest account?"
        description="This removes your runs, notes, conversations, sessions and shares. This application cannot undo deletion. Backups age out according to the retention policy."
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void perform(async () => {
              await write(
                "/me",
                { password: current, confirmation: confirm },
                "DELETE",
              );
              for (const key of Object.keys(sessionStorage))
                if (key.startsWith("wq:")) sessionStorage.removeItem(key);
              client.clear();
              nav("/");
            }, "Account deleted.");
          }}
        >
          <label>
            Current password
            <input
              type="password"
              autoComplete="current-password"
              required
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
            />
          </label>
          <label>
            Type DELETE to confirm
            <input
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </label>
          <Button variant="danger" disabled={confirm !== "DELETE" || busy}>
            Permanently delete account
          </Button>
        </form>
      </Dialog>
    </div>
  );
}
