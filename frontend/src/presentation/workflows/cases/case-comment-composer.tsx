"use client";

import { useMutation } from "@tanstack/react-query";
import { MessageSquarePlus } from "lucide-react";
import { useState } from "react";

import { localHttp } from "@/src/infrastructure/http/client";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Textarea } from "@/src/presentation/components/ui/textarea";

interface Props {
  workflowUuid: string;
  caseId: string;
  /** Refetch del detalle (el timeline vive en el store Zustand del caso). */
  onPosted?: () => void;
}

/**
 * E5 · composer de comentarios del caso (handoff L1→L2). POST vía BFF
 * (`/api/workflows/{wf}/cases/{id}/comments`) ⇒ case_event `comment.added`
 * que el timeline ya pinta tras el refetch.
 */
export function CaseCommentComposer({ workflowUuid, caseId, onPosted }: Props) {
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);

  const post = useMutation({
    mutationFn: async (text: string) => {
      const res = await localHttp.post(
        `/workflows/${workflowUuid}/cases/${caseId}/comments`,
        { body: text }
      );
      return res.data;
    },
  });

  const handleSubmit = () => {
    const trimmed = body.trim();
    if (!trimmed || post.isPending) return;
    setError(null);
    post.mutate(trimmed, {
      onSuccess: () => {
        setBody("");
        onPosted?.();
      },
      onError: () =>
        setError("No se pudo publicar el comentario. Inténtalo de nuevo."),
    });
  };

  return (
    <div className="space-y-2">
      <Textarea
        rows={2}
        value={body}
        onChange={(e) => setBody(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit();
        }}
        placeholder="Añade un comentario al historial del caso… (⌘↵ para publicar)"
        aria-label="Comentario del caso"
      />
      <div className="flex items-center justify-between gap-2">
        {error ? (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : (
          <span />
        )}
        <ActionButton
          size="sm"
          icon={<MessageSquarePlus />}
          loading={post.isPending}
          disabled={!body.trim()}
          onClick={handleSubmit}
        >
          Comentar
        </ActionButton>
      </div>
    </div>
  );
}
