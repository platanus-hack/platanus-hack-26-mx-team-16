export const queryKeys = {
  members: {
    all: ["members"] as const,
  },
  invitations: {
    pending: ["invitations", "pending"] as const,
  },
  roles: {
    all: ["roles"] as const,
    detail: (uuid: string) => ["roles", uuid] as const,
  },
  settings: {
    all: ["settings"] as const,
  },
};
