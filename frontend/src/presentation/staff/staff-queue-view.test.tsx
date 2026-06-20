import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { kindBadge, stageBadge } from "./staff-queue-view";

describe("kindBadge", () => {
  it("renders a QA badge for kind=qa", () => {
    const { container } = render(<div>{kindBadge("qa")}</div>);
    expect(container.textContent).toContain("QA");
  });

  it("renders nothing for the approval kind", () => {
    const { container } = render(<div>{kindBadge("approval")}</div>);
    expect(container.textContent).toBe("");
  });

  it("renders nothing for a missing kind", () => {
    const { container } = render(<div>{kindBadge(null)}</div>);
    expect(container.textContent).toBe("");
  });
});

describe("stageBadge", () => {
  it("renders L1 / L2 for review stages and nothing otherwise", () => {
    expect(render(<div>{stageBadge("review_l1")}</div>).container.textContent).toBe("L1");
    expect(render(<div>{stageBadge("review_l2")}</div>).container.textContent).toBe("L2");
    expect(render(<div>{stageBadge(null)}</div>).container.textContent).toBe("");
  });
});
