import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PolarityBar } from "./polarity-bar";

describe("PolarityBar", () => {
  it("renders no segments when total is zero", () => {
    const { container } = render(<PolarityBar counts={{}} />);
    const bar = container.querySelector('[role="img"]') as HTMLElement;
    expect(bar.children.length).toBe(0);
  });

  it("renders a segment per non-zero polarity", () => {
    const { container } = render(
      <PolarityBar counts={{ PASS: 4, FAIL: 1, NEUTRAL: 0 }} />
    );
    const bar = container.querySelector('[role="img"]') as HTMLElement;
    // PASS + FAIL = 2 segments (NEUTRAL is 0 → omitted)
    expect(bar.children.length).toBe(2);
  });

  it("computes proportional widths", () => {
    const { container } = render(
      <PolarityBar counts={{ PASS: 3, FAIL: 1 }} />
    );
    const bar = container.querySelector('[role="img"]') as HTMLElement;
    const [pass, fail] = bar.children as unknown as HTMLElement[];
    expect(pass.style.width).toBe("75%");
    expect(fail.style.width).toBe("25%");
  });

  it("lists every polarity in the legend even when count is zero", () => {
    const { getByText } = render(
      <PolarityBar counts={{ PASS: 2 }} />
    );
    expect(getByText("Pass")).toBeInTheDocument();
    expect(getByText("Fail")).toBeInTheDocument();
    expect(getByText("Neutral")).toBeInTheDocument();
  });
});
