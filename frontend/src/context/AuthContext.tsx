import React, { createContext, useContext, useState, useEffect } from 'react';
import { getCurrentUser, switchUserRole, loginUser, setAuthToken, getAuthToken } from '../services/api';

export type UserRole = 'CUSTOMER' | 'SUPPORT_AGENT' | 'SUPERVISOR' | 'MANAGER' | 'ADMIN';

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  organization_id: string;
  is_active: boolean;
  permissions: string[];
}

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  hasPermission: (permission: string) => boolean;
  switchRole: (role: UserRole, organizationId?: string) => Promise<void>;
  login: (email: string, password: string, organizationId?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>({
    id: 'USR-ADMIN-01',
    email: 'admin@novacart.com',
    name: 'Alice Admin',
    role: 'ADMIN',
    organization_id: 'ORG-NOVACART',
    is_active: true,
    permissions: [
      'cases:view',
      'cases:modify',
      'actions:execute',
      'actions:approve',
      'customer:view',
      'analytics:view',
      'policies:modify',
      'audit:view',
      'users:manage',
      'org:manage'
    ]
  });
  const [token, setToken] = useState<string | null>(getAuthToken());
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(() => {
    // Attempt auto-login with default ADMIN role if no token exists
    const initAuth = async () => {
      try {
        const storedToken = getAuthToken();
        if (storedToken) {
          const profile = await getCurrentUser();
          setUser(profile);
        } else {
          // Default to ADMIN for seamless evaluation experience
          const data = await switchUserRole('ADMIN', 'ORG-NOVACART');
          setUser(data.user);
          setToken(data.access_token);
        }
      } catch (err) {
        console.warn('Initial auth fetch warning:', err);
      }
    };
    initAuth();
  }, []);

  const hasPermission = (permission: string): boolean => {
    if (!user) return false;
    if (user.role === 'ADMIN') return true;
    return user.permissions.includes(permission);
  };

  const switchRole = async (newRole: UserRole, organizationId: string = 'ORG-NOVACART') => {
    setIsLoading(true);
    try {
      const data = await switchUserRole(newRole, organizationId);
      setUser(data.user);
      setToken(data.access_token);
    } catch (err) {
      console.error('Role switch failed:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string, organizationId?: string) => {
    setIsLoading(true);
    try {
      const data = await loginUser(email, password, organizationId);
      setUser(data.user);
      setToken(data.access_token);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    setAuthToken(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, hasPermission, switchRole, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
