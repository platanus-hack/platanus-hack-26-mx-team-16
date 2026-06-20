"use client";

import { create } from "zustand";

import { useSessionStore } from "@/src/application/contexts/session-store";
import type { User } from "@/src/domain/entities/user";
import type {
  UpdatePasswordPayload,
  UpdateProfilePayload,
} from "@/src/domain/repositories/profile";
import { authHttp } from "@/src/infrastructure/http/client";
import { HttpProfileRepository } from "@/src/infrastructure/repositories/http-profile";

const repository = new HttpProfileRepository(authHttp);

interface ProfileState {
  profile: User | null;
  isLoading: boolean;
  isSaving: boolean;
  isChangingPassword: boolean;
  error: string | null;
  saveError: string | null;
  saveSuccess: boolean;
  passwordError: string | null;
  passwordSuccess: boolean;

  loadProfile: () => Promise<void>;
  updateProfile: (payload: UpdateProfilePayload) => Promise<void>;
  updatePassword: (payload: UpdatePasswordPayload) => Promise<void>;
  clearFeedback: () => void;
  reset: () => void;
}

const initialState = {
  profile: null,
  isLoading: false,
  isSaving: false,
  isChangingPassword: false,
  error: null,
  saveError: null,
  saveSuccess: false,
  passwordError: null,
  passwordSuccess: false,
};

export const useProfileStore = create<ProfileState>((set) => ({
  ...initialState,

  loadProfile: async () => {
    set({ isLoading: true, error: null });
    const response = await repository.get();
    if ("data" in response) {
      set({ profile: response.data });
    } else {
      set({
        error: response.errors?.[0]?.message ?? "Error al cargar el perfil",
      });
    }
    set({ isLoading: false });
  },

  updateProfile: async (payload) => {
    set({ isSaving: true, saveError: null, saveSuccess: false });
    const response = await repository.update(payload);
    if ("data" in response) {
      set({ profile: response.data, saveSuccess: true });
      useSessionStore.getState().setUser(response.data);
    } else {
      set({
        saveError:
          response.errors?.[0]?.message ?? "Error al actualizar el perfil",
      });
    }
    set({ isSaving: false });
  },

  updatePassword: async (payload) => {
    set({
      isChangingPassword: true,
      passwordError: null,
      passwordSuccess: false,
    });
    const response = await repository.updatePassword(payload);
    if ("data" in response) {
      set({ passwordSuccess: true });
    } else {
      set({
        passwordError:
          response.errors?.[0]?.message ?? "Error al cambiar la contraseña",
      });
    }
    set({ isChangingPassword: false });
  },

  clearFeedback: () => {
    set({
      saveSuccess: false,
      saveError: null,
      passwordSuccess: false,
      passwordError: null,
    });
  },

  reset: () => set(initialState),
}));
