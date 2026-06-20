import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "LlamitAI - Intelligent Document Processing Platform";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  return new ImageResponse(
    <div
      style={{
        background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "system-ui, -apple-system, sans-serif",
        padding: "80px",
      }}
    >
      {/* Main Content */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "rgba(255, 255, 255, 0.1)",
          backdropFilter: "blur(10px)",
          borderRadius: "24px",
          padding: "60px 80px",
          border: "1px solid rgba(255, 255, 255, 0.2)",
        }}
      >
        {/* Logo/Title */}
        <h1
          style={{
            fontSize: 96,
            fontWeight: 900,
            color: "white",
            margin: 0,
            letterSpacing: "-0.05em",
            textAlign: "center",
          }}
        >
          LlamitAI
        </h1>

        {/* Subtitle */}
        <p
          style={{
            fontSize: 36,
            color: "rgba(255, 255, 255, 0.9)",
            margin: "24px 0 0 0",
            textAlign: "center",
            fontWeight: 500,
            maxWidth: "800px",
            lineHeight: 1.4,
          }}
        >
          Intelligent Document Processing Platform
        </p>

        {/* Features */}
        <div
          style={{
            display: "flex",
            gap: "32px",
            marginTop: "48px",
            color: "rgba(255, 255, 255, 0.85)",
            fontSize: 24,
          }}
        >
          <span>🚀 AI-Powered</span>
          <span>📄 Smart OCR</span>
          <span>⚡ Automation</span>
        </div>
      </div>
    </div>,
    {
      ...size,
    }
  );
}
