'use client';

import { useState, useEffect } from 'react';
import { devLogin, setToken, getToken, clearToken, listCases, createCase } from '@/lib/api';

export default function Home() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [email, setEmail] = useState('reviewer@orga.com');
  const [orgName, setOrgName] = useState('OrgA');
  const [role, setRole] = useState('Reviewer');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [cases, setCases] = useState<any[]>([]);
  const [newCaseTitle, setNewCaseTitle] = useState('');

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = await getToken();
    if (token) {
      setIsLoggedIn(true);
      loadCases();
    }
  };

  const loadCases = async () => {
    try {
      const data = await listCases();
      setCases(data);
    } catch (e: any) {
      console.error('Failed to load cases:', e);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await devLogin(email, orgName, role);
      await setToken(res.access_token);
      setIsLoggedIn(true);
      loadCases();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await clearToken();
    setIsLoggedIn(false);
    setCases([]);
  };

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCaseTitle.trim()) return;
    try {
      await createCase(newCaseTitle);
      setNewCaseTitle('');
      loadCases();
    } catch (e: any) {
      setError(e.message);
    }
  };

  if (!isLoggedIn) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="card w-full max-w-md">
          <h1 className="text-2xl font-bold text-cyan-400 mb-6">Bank Diligence Platform</h1>
          <h2 className="text-lg text-slate-300 mb-4">Dev Login</h2>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm text-slate-400 mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input w-full"
                required
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Organization</label>
              <input
                type="text"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                className="input w-full"
                required
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Role</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="input w-full"
              >
                <option value="Admin">Admin</option>
                <option value="Reviewer">Reviewer</option>
                <option value="Viewer">Viewer</option>
              </select>
            </div>
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <button type="submit" className="btn btn-primary w-full" disabled={loading}>
              {loading ? 'Logging in...' : 'Login'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6">
      <header className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold text-cyan-400">Bank Diligence Platform</h1>
        <button onClick={handleLogout} className="btn btn-secondary">Logout</button>
      </header>

      <main className="max-w-4xl mx-auto">
        <div className="card mb-6">
          <h2 className="text-lg font-semibold mb-4">Create New Case</h2>
          <form onSubmit={handleCreateCase} className="flex gap-3">
            <input
              type="text"
              value={newCaseTitle}
              onChange={(e) => setNewCaseTitle(e.target.value)}
              placeholder="Case title..."
              className="input flex-1"
            />
            <button type="submit" className="btn btn-primary">Create</button>
          </form>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Cases</h2>
          {cases.length === 0 ? (
            <p className="text-slate-400">No cases yet. Create one above.</p>
          ) : (
            <ul className="space-y-2">
              {cases.map((c) => (
                <li key={c.id}>
                  <a
                    href={`/cases/${c.id}`}
                    className="block p-3 bg-slate-700 rounded hover:bg-slate-600 transition-colors"
                  >
                    <span className="font-medium">{c.title}</span>
                    <span className="text-slate-400 text-sm ml-3">
                      {new Date(c.created_at).toLocaleDateString()}
                    </span>
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}

