import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { PublicReportContent } from "./share-dialog";
describe("public content rendering", () => {
  it("renders user-controlled aliases as text with no HTML or external embeddings", () => {
    const alias = '<img src="https://evil.test/track" onerror="alert(1)">';
    const { container } = render(
      <PublicReportContent
        report={{
          title: "Practice",
          version: 1,
          completed_at: "2026-11-11",
          outcome: "contained",
          total_score: 35,
          criteria: [],
          practice_mode: true,
          hints_used: 0,
          alias,
          label: "Practice",
        }}
      />,
    );
    expect(screen.getByText(alias)).toBeInTheDocument();
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("script")).toBeNull();
  });
});
