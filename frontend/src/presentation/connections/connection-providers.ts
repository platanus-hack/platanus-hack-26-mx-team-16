import type { LucideIcon } from "lucide-react";
import {
  Cable,
  Globe,
  Mail,
  MessageCircle,
  Slack,
  Webhook,
} from "lucide-react";

import { ConnectionProvider } from "@/src/domain/entities/connection";

/**
 * Icon shown for an account of each provider, both in the list rows and the
 * type-picker grid. Covers every {@link ConnectionProvider} value so lookups
 * never fall through.
 */
export const PROVIDER_ICON: Record<ConnectionProvider, LucideIcon> = {
  [ConnectionProvider.HTTP]: Globe,
  [ConnectionProvider.WEBHOOK]: Webhook,
  [ConnectionProvider.SLACK]: Slack,
  [ConnectionProvider.EMAIL]: Mail,
  [ConnectionProvider.WHATSAPP]: MessageCircle,
  [ConnectionProvider.DRIVE]: Cable,
};

export interface ProviderOption {
  provider: ConnectionProvider;
  icon: LucideIcon;
  /** A disabled tile renders as "coming soon" and cannot be selected. */
  enabled: boolean;
}

/**
 * Integration types offered in the creation picker, in display order. Only the
 * enabled ones open a creation modal; the rest read as "coming soon".
 */
export const PROVIDER_OPTIONS: ProviderOption[] = [
  { provider: ConnectionProvider.HTTP, icon: Globe, enabled: true },
  { provider: ConnectionProvider.SLACK, icon: Slack, enabled: true },
  { provider: ConnectionProvider.EMAIL, icon: Mail, enabled: false },
  { provider: ConnectionProvider.WHATSAPP, icon: MessageCircle, enabled: true },
];
