import { useEffect, useRef } from "react";

export function useInfiniteScroll(
  fetchNextPage: () => void,
  hasNextPage: boolean | undefined,
  isFetchingNextPage: boolean,
  threshold = 150,
) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const canLoadMoreRef = useRef(false);
  const doLoadMoreRef = useRef<() => void>(() => {});

  useEffect(() => {
    canLoadMoreRef.current = !!hasNextPage && !isFetchingNextPage;
    doLoadMoreRef.current = fetchNextPage;
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const handleScroll = () => {
      const { scrollTop, clientHeight, scrollHeight } = el;
      if (scrollHeight - scrollTop - clientHeight < threshold && canLoadMoreRef.current) {
        doLoadMoreRef.current();
      }
    };
    el.addEventListener("scroll", handleScroll);
    return () => el.removeEventListener("scroll", handleScroll);
  }, [threshold]);

  return scrollRef;
}
