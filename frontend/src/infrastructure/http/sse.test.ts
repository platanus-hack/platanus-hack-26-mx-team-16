import { describe, expect, it } from "vitest";
import { parseEvent } from "./sse";

describe("parseEvent", () => {
  it("parses a single typed event", () => {
    const raw = 'event: job.started\ndata: {"seq":1}';
    expect(parseEvent(raw)).toEqual({
      type: "job.started",
      data: '{"seq":1}',
    });
  });

  it("defaults type to 'message' when no event field is present", () => {
    expect(parseEvent("data: hello")).toEqual({
      type: "message",
      data: "hello",
    });
  });

  it("returns null when the frame has no data line", () => {
    expect(parseEvent("event: ready")).toBeNull();
  });

  it("ignores comment lines", () => {
    const raw = ": keep-alive\nevent: heartbeat\ndata: {}";
    expect(parseEvent(raw)).toEqual({ type: "heartbeat", data: "{}" });
  });

  it("joins multi-line data fields with a newline", () => {
    const raw = "event: chunk\ndata: line one\ndata: line two";
    expect(parseEvent(raw)).toEqual({
      type: "chunk",
      data: "line one\nline two",
    });
  });

  it("strips a single leading space after the colon", () => {
    expect(parseEvent("data:  two-spaces")).toEqual({
      type: "message",
      data: " two-spaces",
    });
  });
});
