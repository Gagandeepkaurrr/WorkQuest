import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
export function useEventStream(branchId: string | undefined) {
  const client = useQueryClient();
  const [status, setStatus] = useState<"connecting" | "live" | "reconnecting">(
    "connecting",
  );
  useEffect(() => {
    if (!branchId) return;
    const key = `wq:cursor:${branchId}`;
    let source: EventSource;
    let stopped = false;
    let retry: number | undefined;
    const seen = new Set<string>();
    function connect() {
      if (stopped) return;
      const cursor = sessionStorage.getItem(key) ?? `${branchId}:0`;
      source = new EventSource(
        `/api/v1/branches/${branchId}/stream?cursor=${encodeURIComponent(cursor)}`,
      );
      source.onopen = () => setStatus("live");
      source.addEventListener("cursor", (e) => {
        if (e.lastEventId) sessionStorage.setItem(key, e.lastEventId);
      });
      source.addEventListener("update", (e) => {
        if (e.lastEventId) sessionStorage.setItem(key, e.lastEventId);
        if (seen.has(e.lastEventId)) return;
        seen.add(e.lastEventId);
        if (seen.size > 500) seen.clear();
        void client.invalidateQueries({ queryKey: ["state", branchId] });
        void client.invalidateQueries({ queryKey: ["events", branchId] });
        void client.invalidateQueries({ queryKey: ["conversation", branchId] });
        void client.invalidateQueries({ queryKey: ["scorecard", branchId] });
      });
      source.onerror = () => {
        setStatus("reconnecting");
        source.close();
        retry = window.setTimeout(connect, 5000);
      };
    }
    connect();
    return () => {
      stopped = true;
      source?.close();
      if (retry) clearTimeout(retry);
    };
  }, [branchId, client]);
  return status;
}
