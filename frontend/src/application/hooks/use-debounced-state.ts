import { useRef, useState } from "react";

export function useDebouncedState(
  initialValue = "",
  delay = 350,
): [string, string, (val: string) => void] {
  const [value, setValue] = useState(initialValue);
  const [debouncedValue, setDebouncedValue] = useState(initialValue);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const onChange = (val: string) => {
    setValue(val);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setDebouncedValue(val.trim()), delay);
  };

  return [value, debouncedValue, onChange];
}
