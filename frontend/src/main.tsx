import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router";
import "@fontsource-variable/inter";
import "./styles/globals.css";
import "./styles/print.css";
import { Providers } from "./app/providers";
import { ErrorBoundary } from "./app/error-boundary";
import { router } from "./app/router";
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <Providers>
        <a className="skip-link" href="#main">
          Skip to main content
        </a>
        <RouterProvider router={router} />
      </Providers>
    </ErrorBoundary>
  </React.StrictMode>,
);
