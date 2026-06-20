"use client";

interface JsonViewerProps {
  value: string;
  className?: string;
}

export function JsonViewer({ value, className = "" }: JsonViewerProps) {
  const syntaxHighlight = (json: string) => {
    json = json
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    let result = "";
    let i = 0;

    while (i < json.length) {
      const char = json[i];

      if (char === "{" || char === "}") {
        result += `<span class="text-yellow-300 font-bold">${char}</span>`;
        i++;
      } else if (char === "[" || char === "]") {
        result += `<span class="text-cyan-300 font-bold">${char}</span>`;
        i++;
      } else if (char === ",") {
        result += `<span class="text-gray-400">,</span>`;
        i++;
      } else if (char === ":") {
        result += `<span class="text-gray-500">:</span>`;
        i++;
      } else if (char === '"') {
        let str = '"';
        i++;
        while (i < json.length && json[i] !== '"') {
          if (json[i] === "\\" && i + 1 < json.length) {
            str += json[i] + json[i + 1];
            i += 2;
          } else {
            str += json[i];
            i++;
          }
        }
        if (i < json.length) {
          str += '"';
          i++;
        }

        let j = i;
        while (
          j < json.length &&
          (json[j] === " " ||
            json[j] === "\n" ||
            json[j] === "\r" ||
            json[j] === "\t")
        ) {
          j++;
        }

        if (j < json.length && json[j] === ":") {
          result += `<span class="text-sky-400 font-semibold">${str}</span>`;
        } else {
          result += `<span class="text-emerald-400">${str}</span>`;
        }
      } else if (
        /\d/.test(char) ||
        (char === "-" && i + 1 < json.length && /\d/.test(json[i + 1]))
      ) {
        let num = "";
        while (i < json.length && /[\d.eE+\-]/.test(json[i])) {
          num += json[i];
          i++;
        }
        result += `<span class="text-orange-400">${num}</span>`;
      } else if (
        json.substring(i, i + 4) === "true" ||
        json.substring(i, i + 5) === "false"
      ) {
        const bool = json.substring(i, i + 4) === "true" ? "true" : "false";
        result += `<span class="text-purple-400">${bool}</span>`;
        i += bool.length;
      } else if (json.substring(i, i + 4) === "null") {
        result += `<span class="text-rose-400">null</span>`;
        i += 4;
      } else {
        result += char;
        i++;
      }
    }

    return result;
  };

  return (
    <div
      className={`rounded-md border border-border/30 bg-zinc-950 overflow-hidden ${className}`}
    >
      <pre className="p-4 text-xs overflow-x-auto text-gray-300">
        <code
          className="font-mono"
          dangerouslySetInnerHTML={{ __html: syntaxHighlight(value) }}
        />
      </pre>
    </div>
  );
}
