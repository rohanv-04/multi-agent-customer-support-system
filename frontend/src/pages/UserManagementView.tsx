import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Shield, 
  UserPlus, 
  Key, 
  CheckCircle, 
  Lock, 
  Building, 
  RefreshCw,
  Eye,
  AlertTriangle
} from 'lucide-react';
import { useAuth, UserRole } from '../context/AuthContext';
import { listTenantUsers, createTenantUser, updateTenantUserRole, listOrganizations } from '../services/api';

export const UserManagementView: React.FC = () => {
  const { user, hasPermission, switchRole } = useAuth();
  const [users, setUsers] = useState<any[]>([]);
  const [organizations, setOrganizations] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [selectedRole, setSelectedRole] = useState<UserRole>('SUPPORT_AGENT');

  // New user form state
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserName, setNewUserName] = useState('');
  const [newUserPassword, setNewUserPassword] = useState('password123');
  const [newUserRole, setNewUserRole] = useState<UserRole>('SUPPORT_AGENT');
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchUsers = async () => {
    setIsLoading(true);
    try {
      const [uData, orgData] = await Promise.all([
        listTenantUsers().catch(() => []),
        listOrganizations().catch(() => [])
      ]);
      setUsers(uData || []);
      setOrganizations(orgData || []);
    } catch (err) {
      console.error('Failed to load users:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [user?.organization_id]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatusMsg(null);
    try {
      await createTenantUser({
        email: newUserEmail,
        name: newUserName,
        password: newUserPassword,
        role: newUserRole,
        organization_id: user?.organization_id
      });
      setStatusMsg({ type: 'success', text: `User ${newUserEmail} created successfully!` });
      setShowCreateModal(false);
      setNewUserEmail('');
      setNewUserName('');
      fetchUsers();
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to create user' });
    }
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await updateTenantUserRole(userId, newRole);
      setStatusMsg({ type: 'success', text: 'User role updated successfully!' });
      fetchUsers();
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to update user role' });
    }
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'ADMIN':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/20 text-red-400 border border-red-500/30">ADMIN</span>;
      case 'MANAGER':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/20 text-purple-400 border border-purple-500/30">MANAGER</span>;
      case 'SUPERVISOR':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30">SUPERVISOR</span>;
      case 'SUPPORT_AGENT':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-400 border border-blue-500/30">AGENT</span>;
      case 'CUSTOMER':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">CUSTOMER</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/20 text-slate-400">{role}</span>;
    }
  };

  const matrixRoles: UserRole[] = ['CUSTOMER', 'SUPPORT_AGENT', 'SUPERVISOR', 'MANAGER', 'ADMIN'];
  const permissionsList = [
    { key: 'cases:view', label: 'View Support Cases' },
    { key: 'cases:modify', label: 'Modify Cases & Transitions' },
    { key: 'actions:execute', label: 'Execute Gateway Actions' },
    { key: 'actions:approve', label: 'Approve High-Risk Actions' },
    { key: 'customer:view', label: 'View Customer 360' },
    { key: 'analytics:view', label: 'View Operational Analytics' },
    { key: 'policies:modify', label: 'Modify Policies & RAG' },
    { key: 'audit:view', label: 'View 5W1H Audit Logs' },
    { key: 'users:manage', label: 'Manage Tenant Users' },
    { key: 'org:manage', label: 'Enterprise Org Settings' },
  ];

  const hasMatrixPermission = (role: UserRole, permKey: string): boolean => {
    if (role === 'ADMIN') return true;
    if (role === 'MANAGER') return permKey !== 'org:manage';
    if (role === 'SUPERVISOR') return ['cases:view', 'cases:modify', 'actions:execute', 'actions:approve', 'customer:view', 'analytics:view', 'audit:view'].includes(permKey);
    if (role === 'SUPPORT_AGENT') return ['cases:view', 'cases:modify', 'actions:execute', 'customer:view'].includes(permKey);
    if (role === 'CUSTOMER') return ['cases:view', 'customer:view'].includes(permKey);
    return false;
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2.5 bg-gradient-to-tr from-cyan-600 to-blue-600 rounded-xl shadow-lg shadow-cyan-500/20 text-white">
              <Shield className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
              Enterprise Security & RBAC Management
            </h1>
          </div>
          <p className="text-sm text-slate-400">
            Manage multi-tenant organization boundaries, role-based access control, cryptographic sessions, and user accounts.
          </p>
        </div>

        {/* Quick Role & Tenant Switcher Bar */}
        <div className="flex items-center gap-3 bg-slate-900/80 border border-slate-800 p-2 rounded-xl backdrop-blur-md">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800/80 rounded-lg text-xs font-medium text-slate-300">
            <Building className="w-3.5 h-3.5 text-cyan-400" />
            <span>{user?.organization_id || 'ORG-NOVACART'}</span>
          </div>

          <div className="flex items-center gap-1">
            <span className="text-xs text-slate-400 mr-1 font-medium">Switch Role:</span>
            {matrixRoles.map((r) => (
              <button
                key={r}
                onClick={() => switchRole(r, user?.organization_id)}
                className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all ${
                  user?.role === r
                    ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/30'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
              >
                {r === 'SUPPORT_AGENT' ? 'AGENT' : r}
              </button>
            ))}
          </div>
        </div>
      </div>

      {statusMsg && (
        <div className={`p-4 rounded-xl border text-sm flex items-center gap-3 ${
          statusMsg.type === 'success' 
            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' 
            : 'bg-red-500/10 border-red-500/30 text-red-400'
        }`}>
          {statusMsg.type === 'success' ? <CheckCircle className="w-4 h-4 shrink-0" /> : <AlertTriangle className="w-4 h-4 shrink-0" />}
          <span>{statusMsg.text}</span>
        </div>
      )}

      {/* Active Identity Summary Card */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 backdrop-blur-md">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">Authenticated Identity</span>
            <Users className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-lg font-bold text-white truncate">{user?.name}</div>
          <div className="text-xs text-slate-400 truncate">{user?.email}</div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 backdrop-blur-md">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">Active Tenant Organization</span>
            <Building className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-lg font-bold text-white">{user?.organization_id}</div>
          <div className="text-xs text-slate-400">Isolated database boundary</div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 backdrop-blur-md">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">Assigned Role</span>
            <Shield className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-1">{getRoleBadge(user?.role || 'SUPPORT_AGENT')}</div>
          <div className="text-xs text-slate-400 mt-2">{user?.permissions.length || 0} active permissions</div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 backdrop-blur-md">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">Session Security</span>
            <Key className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-lg font-bold text-emerald-400">JWT (HS256)</div>
          <div className="text-xs text-slate-400">PBKDF2-SHA256 Password Hash</div>
        </div>
      </div>

      {/* Tenant Users Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur-md space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Users className="w-5 h-5 text-cyan-400" />
              Tenant User Directory
            </h2>
            <p className="text-xs text-slate-400">
              Users registered within the active {user?.organization_id} organization boundary.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchUsers}
              className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition-all"
              title="Refresh Users"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>

            {hasPermission('users:manage') && (
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold rounded-xl text-xs shadow-lg shadow-cyan-600/20 transition-all"
              >
                <UserPlus className="w-4 h-4" />
                Add Tenant User
              </button>
            )}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-xs font-semibold text-slate-400">
                <th className="py-3 px-4">User</th>
                <th className="py-3 px-4">Role</th>
                <th className="py-3 px-4">Organization</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Created</th>
                {hasPermission('users:manage') && <th className="py-3 px-4 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3.5 px-4">
                    <div className="font-semibold text-white">{u.name}</div>
                    <div className="text-xs text-slate-400">{u.email}</div>
                  </td>
                  <td className="py-3.5 px-4">
                    {getRoleBadge(u.role)}
                  </td>
                  <td className="py-3.5 px-4 text-xs text-slate-300 font-mono">
                    {u.organization_id}
                  </td>
                  <td className="py-3.5 px-4">
                    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${
                      u.is_active ? 'text-emerald-400' : 'text-slate-500'
                    }`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${u.is_active ? 'bg-emerald-400' : 'bg-slate-500'}`} />
                      {u.is_active ? 'Active' : 'Disabled'}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-xs text-slate-400">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                  {hasPermission('users:manage') && (
                    <td className="py-3.5 px-4 text-right">
                      <select
                        value={u.role}
                        onChange={(e) => handleRoleChange(u.id, e.target.value)}
                        className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                      >
                        <option value="CUSTOMER">CUSTOMER</option>
                        <option value="SUPPORT_AGENT">SUPPORT_AGENT</option>
                        <option value="SUPERVISOR">SUPERVISOR</option>
                        <option value="MANAGER">MANAGER</option>
                        <option value="ADMIN">ADMIN</option>
                      </select>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* RBAC Permission Matrix Visualizer */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur-md space-y-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Lock className="w-5 h-5 text-purple-400" />
            RBAC Permission Matrix
          </h2>
          <p className="text-xs text-slate-400">
            Granular access controls enforced at the backend service and API layers.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                <th className="py-3 px-4">Permission</th>
                {matrixRoles.map((r) => (
                  <th key={r} className="py-3 px-4 text-center">
                    {r === 'SUPPORT_AGENT' ? 'AGENT' : r}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {permissionsList.map((p) => (
                <tr key={p.key} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3 px-4">
                    <div className="font-semibold text-slate-200">{p.label}</div>
                    <div className="text-[10px] text-slate-500 font-mono">{p.key}</div>
                  </td>
                  {matrixRoles.map((r) => {
                    const allowed = hasMatrixPermission(r, p.key);
                    return (
                      <td key={r} className="py-3 px-4 text-center">
                        {allowed ? (
                          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                            ✓
                          </span>
                        ) : (
                          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-slate-800 text-slate-600">
                            —
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add User Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <UserPlus className="w-5 h-5 text-cyan-400" />
              Add User to {user?.organization_id}
            </h3>

            <form onSubmit={handleCreateUser} className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 font-medium">Full Name</label>
                <input
                  type="text"
                  required
                  value={newUserName}
                  onChange={(e) => setNewUserName(e.target.value)}
                  placeholder="e.g. Rachel Zane"
                  className="w-full mt-1 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 font-medium">Email Address</label>
                <input
                  type="email"
                  required
                  value={newUserEmail}
                  onChange={(e) => setNewUserEmail(e.target.value)}
                  placeholder="rachel@novacart.com"
                  className="w-full mt-1 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 font-medium">Password</label>
                <input
                  type="password"
                  required
                  value={newUserPassword}
                  onChange={(e) => setNewUserPassword(e.target.value)}
                  className="w-full mt-1 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 font-medium">Role Assignment</label>
                <select
                  value={newUserRole}
                  onChange={(e) => setNewUserRole(e.target.value as UserRole)}
                  className="w-full mt-1 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
                >
                  <option value="CUSTOMER">CUSTOMER</option>
                  <option value="SUPPORT_AGENT">SUPPORT_AGENT</option>
                  <option value="SUPERVISOR">SUPERVISOR</option>
                  <option value="MANAGER">MANAGER</option>
                  <option value="ADMIN">ADMIN</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-xl text-xs shadow-lg shadow-cyan-600/20"
                >
                  Create User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
