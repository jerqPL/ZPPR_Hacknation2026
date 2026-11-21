"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import type { SimulatedUserProfile } from "@/lib/types";
import { api } from "@/lib/api";

const STORAGE_KEY = "zppr-simulated-session";

interface UserContextValue {
  user: SimulatedUserProfile | null;
  authMethod: string | null;
  loading: boolean;
  error: string | null;
  loginAs: (personaId: string) => Promise<void>;
  logout: () => void;
}

const UserContext = createContext<UserContextValue | undefined>(undefined);

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<SimulatedUserProfile | null>(null);
  const [authMethod, setAuthMethod] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved) as {
          profile: SimulatedUserProfile;
          authMethod: string;
        };
        setUser(parsed.profile);
        setAuthMethod(parsed.authMethod);
      }
    } catch {
      // ignore corrupted storage
    }
  }, []);

  const loginAs = async (personaId: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.loginMobywatel(personaId);
      setUser(res.profile);
      setAuthMethod(res.auth_method);
      sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ profile: res.profile, authMethod: res.auth_method })
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nie udało się zalogować (symulacja)");
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    setAuthMethod(null);
    setError(null);
    sessionStorage.removeItem(STORAGE_KEY);
  };

  return (
    <UserContext.Provider value={{ user, authMethod, loading, error, loginAs, logout }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const ctx = useContext(UserContext);
  if (!ctx) {
    throw new Error("useUser must be used within UserProvider");
  }
  return ctx;
}
