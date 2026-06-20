export interface TimezoneOption {
  code: string; // IANA tz id
  label: string;
  popular?: boolean;
}

export const TIMEZONES: TimezoneOption[] = [
  { code: "America/Mexico_City", label: "Ciudad de México (UTC−6)", popular: true },
  { code: "America/La_Paz", label: "La Paz (UTC−4)", popular: true },
  { code: "America/Argentina/Buenos_Aires", label: "Buenos Aires (UTC−3)", popular: true },
  { code: "America/Bogota", label: "Bogotá (UTC−5)", popular: true },
  { code: "America/Lima", label: "Lima (UTC−5)", popular: true },
  { code: "America/Santiago", label: "Santiago (UTC−4)", popular: true },
  { code: "America/Sao_Paulo", label: "São Paulo (UTC−3)" },
  { code: "America/New_York", label: "New York (UTC−5)", popular: true },
  { code: "America/Los_Angeles", label: "Los Angeles (UTC−8)" },
  { code: "America/Chicago", label: "Chicago (UTC−6)" },
  { code: "Europe/Madrid", label: "Madrid (UTC+1)", popular: true },
  { code: "Europe/London", label: "London (UTC+0)" },
  { code: "UTC", label: "UTC", popular: true },
];

const TIMEZONE_INDEX = new Map(TIMEZONES.map((t) => [t.code, t]));

export function findTimezone(code: string | null | undefined): TimezoneOption | undefined {
  if (!code) return undefined;
  return TIMEZONE_INDEX.get(code);
}

/** Browser's IANA tz id (e.g. "America/Mexico_City"); falls back to UTC. */
export function detectBrowserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}
