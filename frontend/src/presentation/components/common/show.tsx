import type { ReactNode } from "react";

interface ShowProps<T> {
  when: T | null | undefined | false;
  fallback?: ReactNode;
  children: ReactNode | ((item: T) => ReactNode);
}

export function Show<T>({ when, fallback, children }: ShowProps<T>) {
  if (!when) {
    return <>{fallback ?? null}</>;
  }

  if (typeof children === "function") {
    return <>{(children as (item: T) => ReactNode)(when)}</>;
  }

  return <>{children}</>;
}
