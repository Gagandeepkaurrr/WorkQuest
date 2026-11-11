import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { api } from "../../lib/api-client";
import { PublicHeader } from "../../components/layout/shell";
import { Loading } from "../../components/feedback/states";
import { PublicReportContent, type PublicReport } from "./share-dialog";
export function PublicReportPage() {
  const { token } = useParams();
  const report = useQuery({
    queryKey: ["public-report", token],
    queryFn: () => api<PublicReport>(`/shared-reports/${token}`),
    retry: false,
    gcTime: 0,
    staleTime: 0,
    refetchInterval: 10000,
  });
  useEffect(() => {
    const meta = document.createElement("meta");
    meta.name = "robots";
    meta.content = "noindex,nofollow";
    document.head.append(meta);
    return () => meta.remove();
  }, []);
  return (
    <div>
      <PublicHeader />
      <main id="main" className="public-report-container">
        {report.isPending ? (
          <Loading />
        ) : report.error || !report.data ? (
          <div className="empty glass">
            <h1>This report is unavailable.</h1>
            <p>The link may have expired or been revoked.</p>
            <Link className="button button-primary" to="/">
              Return to WorkQuest
            </Link>
          </div>
        ) : (
          <PublicReportContent report={report.data} />
        )}
      </main>
    </div>
  );
}
