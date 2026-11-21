"use client";

import React, { createContext, useContext, useState } from "react";
import type { SimulatedUserProfile } from "@/lib/types";
import { api } from "@/lib/api";

interface UserContextValue {
  user: SimulatedUserProfile | null;
  authMethod: string | null;
  loading: boolean;
  loginAs: (personaId: string) => Promise<void>;
  logout: () => void;
}

const UserContext = createContext<UserContextValue | undefined>(undefined);

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<SimulatedUserProfile | null>(null);
  const [authMethod, setAuthMethod] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const loginAs = async (personaId: string) => {
    setLoading(true);
    try {
      const res = await api.loginMobywatel(personaId);
      setUser(res.profile);
      setAuthMethod(res.auth_method);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    setAuthMethod(null);
  };

  return (
    <UserContext.Provider value={{ user, authMethod, loading, loginAs, logout }}>
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
