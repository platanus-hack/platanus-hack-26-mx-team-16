import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "LlamitAI - Transform your document workflows with AI";
export const size = { width: 1200, height: 675 };
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
        padding: "60px",
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
          padding: "50px 70px",
          border: "1px solid rgba(255, 255, 255, 0.2)",
        }}
      >
        {/* Logo/Title */}
        <h1
          style={{
            fontSize: 84,
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
            fontSize: 32,
            color: "rgba(255, 255, 255, 0.9)",
            margin: "20px 0 0 0",
            textAlign: "center",
            fontWeight: 500,
            maxWidth: "700px",
            lineHeight: 1.4,
          }}
        >
          Transform your document workflows with AI-powered processing
        </p>

        {/* Features */}
        <div
          style={{
            display: "flex",
            gap: "28px",
            marginTop: "40px",
            color: "rgba(255, 255, 255, 0.85)",
            fontSize: 22,
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
