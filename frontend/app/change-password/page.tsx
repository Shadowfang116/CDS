'use client';

import { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { BRAND } from '@/lib/brand';
import { ApiError, changePassword, getMe, logout } from '@/lib/api';

export default function ChangePasswordPage() {
  const router = useRouter();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState('');

  useEffect(() => {
    let mounted = true;

    void (async () => {
      try {
        const user = await getMe();
        if (!mounted) {
          return;
        }
        setEmail(user?.email ?? '');
      } catch {
        router.replace('/login');
      }
    })();

    return () => {
      mounted = false;
    };
  }, [router]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');

    if (!currentPassword.trim()) {
      setError('Enter your current password.');
      return;
    }

    if (newPassword.length < 12) {
      setError('Choose a new password with at least 12 characters.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.');
      return;
    }

    setLoading(true);
    try {
      await changePassword(currentPassword, newPassword);
      router.replace('/dashboard');
      router.refresh();
    } catch (changeError) {
      if (changeError instanceof ApiError) {
        setError(changeError.detail);
      } else {
        setError('Password change failed. Please retry.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[rgba(15,18,22,0.98)] px-4 py-10 text-stone-100 sm:px-6">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-[1100px] items-center justify-center">
        <div className="grid w-full gap-6 lg:grid-cols-[0.95fr_1.05fr]">
          <section className="rounded-[28px] border border-[rgba(127,138,149,0.18)] bg-[linear-gradient(180deg,rgba(19,23,28,0.98),rgba(13,16,20,0.98))] p-8 shadow-[0_26px_70px_rgba(0,0,0,0.24)]">
            <div className="space-y-6">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-[rgba(127,138,149,0.24)] bg-[rgba(28,34,38,0.96)] font-display text-[1.75rem] font-semibold tracking-[-0.06em] text-stone-100">
                {BRAND.short}
              </div>
              <div className="space-y-3">
                <p className="text-xs font-medium uppercase tracking-[0.2em] text-[rgba(167,175,183,0.64)]">
                  Secure Access Reset
                </p>
                <h1 className="font-display text-[2rem] font-semibold tracking-[-0.05em] text-stone-100">
                  Set a permanent password before entering the workspace.
                </h1>
                <p className="max-w-md text-sm leading-6 text-[rgba(198,204,210,0.78)]">
                  Admin-created accounts remain restricted until the temporary password is replaced. Your session will open the dashboard after a successful reset.
                </p>
              </div>
              <div className="rounded-2xl border border-[rgba(127,138,149,0.16)] bg-[rgba(24,28,32,0.72)] p-4 text-sm text-[rgba(198,204,210,0.76)]">
                <p>{email || 'Authenticated account'}</p>
                <p className="mt-2 text-[rgba(167,175,183,0.72)]">
                  Use a unique password reserved for this diligence system.
                </p>
              </div>
            </div>
          </section>

          <section className="rounded-[28px] border border-[rgba(127,138,149,0.18)] bg-[rgba(22,27,32,0.98)] p-8 shadow-[0_26px_70px_rgba(0,0,0,0.24)]">
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <label className="text-[11px] font-medium uppercase tracking-[0.18em] text-[rgba(167,175,183,0.72)]">
                  Current Password
                </label>
                <Input
                  type="password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  className="h-11 border-[rgba(127,138,149,0.22)] bg-[rgba(15,18,22,0.74)] text-stone-100"
                  placeholder="Enter your temporary password"
                  required
                />
              </div>

              <div className="space-y-2">
                <label className="text-[11px] font-medium uppercase tracking-[0.18em] text-[rgba(167,175,183,0.72)]">
                  New Password
                </label>
                <Input
                  type="password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  className="h-11 border-[rgba(127,138,149,0.22)] bg-[rgba(15,18,22,0.74)] text-stone-100"
                  placeholder="Minimum 12 characters"
                  required
                />
              </div>

              <div className="space-y-2">
                <label className="text-[11px] font-medium uppercase tracking-[0.18em] text-[rgba(167,175,183,0.72)]">
                  Confirm New Password
                </label>
                <Input
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  className="h-11 border-[rgba(127,138,149,0.22)] bg-[rgba(15,18,22,0.74)] text-stone-100"
                  placeholder="Re-enter your new password"
                  required
                />
              </div>

              {error ? (
                <p className="rounded-lg border border-[rgba(170,88,84,0.42)] bg-[rgba(88,34,33,0.32)] px-3 py-2 text-sm text-[rgba(255,211,208,0.9)]">
                  {error}
                </p>
              ) : null}

              <div className="flex flex-col gap-3 pt-2 sm:flex-row">
                <Button type="submit" className="h-11 flex-1 text-sm" loading={loading}>
                  {loading ? 'Updating password...' : 'Update password'}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className="h-11 border-[rgba(127,138,149,0.22)] bg-transparent text-sm text-stone-200"
                  onClick={async () => {
                    await logout();
                    router.replace('/login');
                  }}
                >
                  Sign out
                </Button>
              </div>
            </form>
          </section>
        </div>
      </div>
    </div>
  );
}
