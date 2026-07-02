import { createContext, useContext, useState, useCallback } from "react";
import { saveToken, clearToken, isLoggedIn } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [loggedIn, setLoggedIn] = useState(isLoggedIn());

  const login = useCallback((token) => {
    saveToken(token);
    setLoggedIn(true);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setLoggedIn(false);
  }, []);

  return (
    <AuthContext.Provider value={{ loggedIn, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
