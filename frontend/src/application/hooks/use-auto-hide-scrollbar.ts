import { type RefObject, useEffect, useRef } from "react";

/**
 * Detecta UNA vez si el SO usa scrollbars clásicos (ocupan layout) u overlay
 * (se dibujan encima) y lo marca en `<html data-scrollbars>`. El CSS solo
 * estiliza la barra cuando es "classic" (Windows/Linux); en "overlay" (macOS /
 * "al desplazar") deja el scrollbar nativo → 0 espacio reservado + autohide
 * nativo (Safari).
 */
let scrollbarModeApplied = false;
function ensureScrollbarMode() {
  if (scrollbarModeApplied || typeof document === "undefined") return;
  scrollbarModeApplied = true;
  const probe = document.createElement("div");
  probe.style.cssText =
    "position:absolute;top:-9999px;width:100px;height:100px;overflow:scroll;visibility:hidden;";
  document.body.appendChild(probe);
  const classic = probe.offsetWidth - probe.clientWidth > 0;
  probe.remove();
  document.documentElement.dataset.scrollbars = classic ? "classic" : "overlay";
}

/**
 * Autohide del scrollbar estilo Safari: marca `data-scrolling="true"` en el
 * elemento mientras se hace scroll y lo quita tras `idleMs` de inactividad. El
 * CSS `[data-scrollbars="classic"] .scrollbar-subtle` revela el thumb solo con
 * ese atributo (solo donde hay barra clásica; en overlay nativo no hace falta),
 * sin librerías ni hijack del scroll nativo (sticky/teclado/a11y intactos).
 *
 * Se re-engancha cuando `ref.current` cambia (null→nodo) para soportar elementos
 * que montan tarde (p. ej. tras un estado de carga); por eso el effect corre tras
 * cada render pero solo hace trabajo si el nodo cambió de identidad.
 */
export function useAutoHideScrollbar(
  ref: RefObject<HTMLElement | null>,
  idleMs = 700
) {
  const idle = useRef(idleMs);
  idle.current = idleMs;
  const attached = useRef<HTMLElement | null>(null);
  const cleanup = useRef<(() => void) | null>(null);

  useEffect(() => {
    ensureScrollbarMode();
  }, []);

  // Sin deps: corre tras cada render para enganchar el nodo cuando monte; el
  // guard de identidad evita re-enganches innecesarios.
  useEffect(() => {
    const el = ref.current;
    if (el === attached.current) return;
    cleanup.current?.();
    cleanup.current = null;
    attached.current = el;
    if (!el) return;

    let timer: ReturnType<typeof setTimeout> | null = null;
    const onScroll = () => {
      el.dataset.scrolling = "true";
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => {
        delete el.dataset.scrolling;
      }, idle.current);
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    cleanup.current = () => {
      el.removeEventListener("scroll", onScroll);
      if (timer) clearTimeout(timer);
    };
  });

  useEffect(() => () => cleanup.current?.(), []);
}
