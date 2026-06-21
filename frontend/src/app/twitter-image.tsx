import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt =
  "Owliver — pentesting con IA: seguridad web y superficie agéntica, con calificación A–F";
export const size = { width: 1200, height: 675 };
export const contentType = "image/png";

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          justifyContent: "center",
          background: "#090704",
          fontFamily: "system-ui, -apple-system, sans-serif",
          padding: "96px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "26px" }}>
          <svg
            width="104"
            height="104"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#D1CBFF"
            strokeWidth={1.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M6 5.2 8.2 7.6" />
            <path d="M18 5.2 15.8 7.6" />
            <path d="M12 4.9c-3.9 0-6.4 3-6.4 7.2 0 4 2.7 6.9 6.4 6.9s6.4-2.9 6.4-6.9c0-4.2-2.5-7.2-6.4-7.2Z" />
            <circle cx="9.3" cy="11" r="1.85" />
            <circle cx="14.7" cy="11" r="1.85" />
            <path d="M12 13.1v1.5" />
          </svg>
          <div
            style={{
              display: "flex",
              fontSize: 96,
              fontWeight: 800,
              color: "#FCFAF4",
              letterSpacing: "-0.03em",
            }}
          >
            Owliver
          </div>
        </div>

        <div
          style={{
            display: "flex",
            marginTop: "44px",
            fontSize: 44,
            fontWeight: 600,
            color: "rgba(252,250,244,0.92)",
            maxWidth: "920px",
            lineHeight: 1.3,
          }}
        >
          ¿Qué tan segura es la IA de tu sitio?
        </div>

        <div
          style={{
            display: "flex",
            marginTop: "28px",
            fontSize: 30,
            color: "#D1CBFF",
            letterSpacing: "0.01em",
          }}
        >
          Seguridad web + superficie agéntica · Calificación A–F
        </div>
      </div>
    ),
    { ...size }
  );
}
