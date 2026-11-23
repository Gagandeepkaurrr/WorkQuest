import { createBrowserRouter, Link } from "react-router";
import { ProtectedShell } from "../components/layout/shell";
export const router = createBrowserRouter([
  {
    path: "/",
    lazy: async () => ({
      Component: (await import("../features/missions/landing")).Landing,
    }),
  },
  ...[
    "sign-in",
    "sign-up",
    "verify-email",
    "forgot-password",
    "reset-password",
  ].map((path) => ({
    path: `/${path}`,
    lazy: async () => ({
      Component: (await import("../features/auth/auth-page")).AuthPage,
    }),
  })),
  {
    element: <ProtectedShell />,
    children: [
      {
        path: "/missions",
        lazy: async () => ({
          Component: (await import("../features/missions/library")).Library,
        }),
      },
      {
        path: "/missions/:slug",
        lazy: async () => ({
          Component: (await import("../features/missions/briefing")).Briefing,
        }),
      },
      {
        path: "/runs/:runId",
        lazy: async () => ({
          Component: (await import("../features/workspace/workspace"))
            .Workspace,
        }),
      },
      {
        path: "/runs/:runId/debrief",
        lazy: async () => ({
          Component: (await import("../features/debrief/debrief")).Debrief,
        }),
      },
      {
        path: "/runs/:runId/compare",
        lazy: async () => ({
          Component: (await import("../features/branches/compare")).Compare,
        }),
      },
      {
        path: "/progress",
        lazy: async () => ({
          Component: (await import("../features/progress/progress")).Progress,
        }),
      },
      {
        path: "/settings",
        lazy: async () => ({
          Component: (await import("../features/settings/settings")).Settings,
        }),
      },
      {
        path: "/admin/scenarios",
        lazy: async () => ({
          Component: (await import("../features/admin/admin")).AdminScenarios,
        }),
      },
      {
        path: "/admin/scenarios/:scenarioId/edit",
        lazy: async () => ({
          Component: (await import("../features/admin/admin")).ScenarioEditor,
        }),
      },
      {
        path: "/admin/scenarios/:scenarioId/preview",
        lazy: async () => ({
          Component: (await import("../features/admin/admin")).AdminPreview,
        }),
      },
      {
        path: "/admin/operations",
        lazy: async () => ({
          Component: (await import("../features/admin/admin")).Operations,
        }),
      },
    ],
  },
  {
    path: "/reports/:token",
    lazy: async () => ({
      Component: (await import("../features/reports/public-report"))
        .PublicReportPage,
    }),
  },
  {
    path: "*",
    element: (
      <main className="empty">
        <h1>This page is unavailable.</h1>
        <Link to="/">Return home</Link>
      </main>
    ),
  },
]);
