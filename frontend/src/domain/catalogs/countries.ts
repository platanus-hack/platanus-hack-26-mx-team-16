/**
 * Curated country catalog. Codes match the backend `CountryIsoCode` enum.
 * Add a new entry whenever the backend learns a new country.
 */

export interface CountryOption {
  code: string; // ISO 3166-1 alpha-2
  label: string;
  flag: string;
  popular?: boolean;
}

export const COUNTRIES: CountryOption[] = [
  { code: "MX", label: "México", flag: "🇲🇽", popular: true },
  { code: "BO", label: "Bolivia", flag: "🇧🇴", popular: true },
  { code: "AR", label: "Argentina", flag: "🇦🇷", popular: true },
  { code: "CO", label: "Colombia", flag: "🇨🇴", popular: true },
  { code: "PE", label: "Perú", flag: "🇵🇪", popular: true },
  { code: "CL", label: "Chile", flag: "🇨🇱", popular: true },
  { code: "US", label: "Estados Unidos", flag: "🇺🇸", popular: true },
  { code: "ES", label: "España", flag: "🇪🇸", popular: true },
  { code: "BR", label: "Brasil", flag: "🇧🇷" },
  { code: "EC", label: "Ecuador", flag: "🇪🇨" },
  { code: "UY", label: "Uruguay", flag: "🇺🇾" },
  { code: "PY", label: "Paraguay", flag: "🇵🇾" },
  { code: "CR", label: "Costa Rica", flag: "🇨🇷" },
  { code: "PA", label: "Panamá", flag: "🇵🇦" },
  { code: "GT", label: "Guatemala", flag: "🇬🇹" },
  { code: "CA", label: "Canadá", flag: "🇨🇦" },
];

const COUNTRY_INDEX = new Map(COUNTRIES.map((c) => [c.code, c]));

export function findCountry(code: string | null | undefined): CountryOption | undefined {
  if (!code) return undefined;
  return COUNTRY_INDEX.get(code.toUpperCase());
}
