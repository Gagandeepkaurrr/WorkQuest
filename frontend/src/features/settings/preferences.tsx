import { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, write } from "../../lib/api-client";
import { useSession } from "../auth/use-session";
import { Button } from "../../components/ui/button";
import { ErrorState } from "../../components/feedback/states";
import type { components } from "../../generated/api-types";
export type Preferences = components["schemas"]["PreferencesInput"];
export function ThemeSync() {
  const user = useSession().data;
  const prefs = useQuery({
    queryKey: ["preferences"],
    queryFn: () => api<Preferences>("/me/preferences"),
    enabled: Boolean(user),
  });
  useEffect(() => {
    document.documentElement.dataset.theme = prefs.data?.theme ?? "light";
    document.documentElement.dataset.reducedMotion = String(
      prefs.data?.reduced_motion ?? false,
    );
  }, [prefs.data]);
  return null;
}
export function Onboarding() {
  const user = useSession().data;
  const client = useQueryClient();
  const [error, setError] = useState<unknown>();
  const prefs = useQuery({
    queryKey: ["preferences"],
    queryFn: () => api<Preferences>("/me/preferences"),
    enabled: Boolean(user),
  });
  if (!prefs.data || prefs.data.onboarding_completed) return null;
  return (
    <div className="onboarding glass">
      <div>
        <span className="eyebrow">MAKE YOURSELF AT HOME</span>
        <strong>Pick a mission. Follow a clue. Make your next move.</strong>
        <p>
          Only deliberate actions move simulated time. Save checkpoints to
          explore a different decision.
        </p>
      </div>
      <Button
        variant="secondary"
        size="small"
        onClick={() =>
          void write(
            "/me/preferences",
            { ...prefs.data, onboarding_completed: true },
            "PATCH",
          )
            .then(() => client.invalidateQueries({ queryKey: ["preferences"] }))
            .catch(setError)
        }
      >
        Got it
      </Button>
      {Boolean(error) && <ErrorState error={error} />}
    </div>
  );
}
