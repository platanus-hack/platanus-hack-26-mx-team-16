"use client";

import { create } from "zustand";

import { authHttp } from "@/src/infrastructure/http/client";
import { HttpTenantSettingsRepository } from "@/src/infrastructure/repositories/tenant-settings";
import type { TenantSettings } from "@/src/domain/entities/tenant-settings";

const repository = new HttpTenantSettingsRepository(authHttp);

interface SettingsState {
  settings: TenantSettings | null;
  isLoading: boolean;
  error: string | null;

  loadSettings: () => Promise<void>;
  updateSettings: (name: string) => Promise<void>;
  uploadAvatar: (file: File) => Promise<void>;
  regenerateWebhookKey: () => Promise<void>;
  deleteTenant: () => Promise<boolean>;
  reset: () => void;
}

const initialState = {
  settings: null,
  isLoading: false,
  error: null,
};

export const useSettingsStore = create<SettingsState>((set) => ({
  ...initialState,

  loadSettings: async () => {
    set({ isLoading: true, error: null });
    const response = await repository.get();
    if ("data" in response) {
      set({ settings: response.data });
    } else {
      set({ error: response.errors?.[0]?.message ?? "Error loading settings" });
    }
    set({ isLoading: false });
  },

  updateSettings: async (name) => {
    const response = await repository.update(name);
    if ("data" in response) {
      set({ settings: response.data });
    }
  },

  uploadAvatar: async (file) => {
    const response = await repository.updateAvatar(file);
    if ("data" in response) {
      set({ settings: response.data });
    }
  },

  regenerateWebhookKey: async () => {
    const response = await repository.regenerateWebhookKey();
    if ("data" in response) {
      set({ settings: response.data });
    }
  },

  deleteTenant: async () => {
    const response = await repository.deleteTenant();
    if ("success" in response) {
      return response.success;
    }
    return false;
  },

  reset: () => set(initialState),
}));
