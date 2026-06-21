/**
 * `/watchlist` — permanent redirect to `/watcher` (§F11). The watchlist + the
 * inspection-bench grade explainer were merged into a single `/watcher`
 * workspace; this route is kept only so existing links/bookmarks still resolve.
 */
import { redirect } from "next/navigation";

export default function WatchlistRedirect() {
  redirect("/watcher");
}
