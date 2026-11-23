import { useInfiniteQuery } from "@tanstack/react-query";
import { api } from "../../lib/api-client";
import type { Event } from "../../lib/types";
import { label } from "../../lib/types";
import { Button } from "../../components/ui/button";
import { ErrorState, Loading } from "../../components/feedback/states";
type EventPage = {
  items: Event[];
  inherited_prefix: Event[];
  cursor: string;
  last_event_seq: number;
};
export function TimelinePanel({ branchId }: { branchId: string }) {
  const events = useInfiniteQuery({
    queryKey: ["events", branchId],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      api<EventPage>(`/branches/${branchId}/events?after=${pageParam}`),
    getNextPageParam: (last) => {
      const scanned = Number(last.cursor.split(":").at(-1));
      return scanned < last.last_event_seq ? scanned : undefined;
    },
  });
  if (events.isPending) return <Loading />;
  if (events.error) return <ErrorState error={events.error} />;
  const items = events.data.pages.flatMap((p) => [
    ...p.inherited_prefix,
    ...p.items,
  ]);
  return (
    <div className="stack">
      <div className="panel-heading">
        <h2>How you got here.</h2>
        <p>
          A recorded history of your investigation. Reviewing it never re-runs
          an action.
        </p>
      </div>
      <ol className="timeline">
        {items.map((e) => (
          <li className="glass" key={e.id}>
            <span className="timeline-dot" />
            <div>
              <span className="eyebrow">MINUTE {e.logical_tick}</span>
              <h3>{label(e.type)}</h3>
              <p>
                {typeof e.payload?.reply_text === "string"
                  ? e.payload.reply_text
                  : typeof e.payload?.text === "string"
                    ? e.payload.text
                    : JSON.stringify(
                        e.payload?.result ?? e.payload?.payload ?? {},
                      )}
              </p>
            </div>
            <small>#{e.seq}</small>
          </li>
        ))}
      </ol>
      {events.hasNextPage && (
        <Button
          variant="secondary"
          disabled={events.isFetchingNextPage}
          onClick={() => void events.fetchNextPage()}
        >
          Load more history
        </Button>
      )}
    </div>
  );
}
