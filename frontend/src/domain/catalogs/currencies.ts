export interface CurrencyOption {
  code: string; // ISO 4217
  label: string;
  symbol: string;
  popular?: boolean;
}

export const CURRENCIES: CurrencyOption[] = [
  { code: "USD", label: "US Dollar", symbol: "$", popular: true },
  { code: "MXN", label: "Peso Mexicano", symbol: "$", popular: true },
  { code: "BOB", label: "Boliviano", symbol: "Bs.", popular: true },
  { code: "ARS", label: "Peso Argentino", symbol: "$", popular: true },
  { code: "COP", label: "Peso Colombiano", symbol: "$", popular: true },
  { code: "PEN", label: "Sol Peruano", symbol: "S/", popular: true },
  { code: "CLP", label: "Peso Chileno", symbol: "$", popular: true },
  { code: "EUR", label: "Euro", symbol: "€", popular: true },
  { code: "BRL", label: "Real Brasileño", symbol: "R$" },
  { code: "UYU", label: "Peso Uruguayo", symbol: "$" },
  { code: "PYG", label: "Guaraní", symbol: "₲" },
  { code: "CRC", label: "Colón", symbol: "₡" },
  { code: "GTQ", label: "Quetzal", symbol: "Q" },
  { code: "CAD", label: "Dólar Canadiense", symbol: "$" },
];

const CURRENCY_INDEX = new Map(CURRENCIES.map((c) => [c.code, c]));

export function findCurrency(code: string | null | undefined): CurrencyOption | undefined {
  if (!code) return undefined;
  return CURRENCY_INDEX.get(code.toUpperCase());
}
