'use client';

import { FormEvent, Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { BRAND } from '@/lib/brand';
import { ApiError, getMe, login } from '@/lib/api';

function LoginPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [lockMessage, setLockMessage] = useState('');
  const [forgotPasswordMessage, setForgotPasswordMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const nextPath = searchParams.get('next') || '/dashboard';
  const trimmedEmail = email.trim();
  const passwordProvided = password.trim().length > 0;

  useEffect(() => {
    let mounted = true;

    const loadSession = async () => {
      try {
        const currentUser = await getMe();
        if (mounted) {
          router.replace(currentUser?.must_change_password ? '/change-password' : nextPath);
        }
      } catch {
        // Stay on the login page when there is no valid session.
      }
    };

    void loadSession();

    return () => {
      mounted = false;
    };
  }, [nextPath, router]);

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedEmail) {
      setError('Enter your assigned email address.');
      return;
    }

    if (!password.trim()) {
      setError('Enter your password.');
      return;
    }

    setLoading(true);
    setError('');
    setLockMessage('');
    setForgotPasswordMessage('');

    try {
      const user = await login(normalizedEmail, password);
      router.replace(user?.must_change_password ? '/change-password' : nextPath);
    } catch (loginError: unknown) {
      setError('Invalid credentials. Please try again.');
      if (loginError instanceof ApiError) {
        const lockedUntil =
          loginError.originalError?.detail?.locked_until
          ?? loginError.originalError?.locked_until;
        if (typeof lockedUntil === 'string') {
          const parsed = new Date(lockedUntil);
          if (!Number.isNaN(parsed.getTime())) {
            setLockMessage(`Account locked until ${parsed.toLocaleString()}.`);
          }
        }
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[rgba(15,18,22,0.98)] text-stone-100">
      <div className="mx-auto grid min-h-screen max-w-[1440px] lg:grid-cols-[0.92fr_1.08fr]">
        <aside className="hidden border-r border-[rgba(127,138,149,0.18)] bg-[rgba(12,15,19,0.96)] lg:flex lg:flex-col lg:justify-between lg:px-12 lg:py-14">
          <div className="space-y-8">
            <div className="flex h-16 w-16 items-center justify-center rounded-xl border border-[rgba(127,138,149,0.24)] bg-[rgba(28,34,38,0.96)] font-display text-[1.75rem] font-semibold tracking-[-0.06em] text-stone-100">
              {BRAND.short}
            </div>
            {/* login-visual-panel: future Spline / three.js 3D showcase — do NOT add 3D code here */}
            <div
              id="login-visual-panel"
              aria-hidden="true"
              className="flex flex-col gap-3"
            >
              <p className="text-sm text-[rgba(167,175,183,0.78)]">{BRAND.subtitle}</p>
              <p className="max-w-md text-sm leading-6 text-[rgba(198,204,210,0.78)]">
                Authenticate once, then work from the review queue, exception timeline, and approval path without switching contexts.
              </p>
            </div>
          </div>

          <div className="space-y-3 text-sm text-[rgba(198,204,210,0.74)]">
            <div className="border-t border-[rgba(127,138,149,0.16)] pt-4">Document intake, OCR review, controls, and audit history in one workspace.</div>
            <div className="border-t border-[rgba(127,138,149,0.16)] pt-4">Use your assigned credentials. Temporary passwords must be changed after first sign-in.</div>
          </div>
        </aside>

        <section className="flex min-h-screen items-center justify-center px-4 py-10 sm:px-6 lg:px-10">
          <div className="w-full max-w-[420px] rounded-2xl border border-[rgba(127,138,149,0.22)] bg-[rgba(22,27,32,0.98)] p-6 shadow-[0_22px_56px_rgba(0,0,0,0.22)] sm:p-8">
            <div className="space-y-6">
              <div className="space-y-2">
                <h1 className="font-display text-[1.9rem] font-semibold tracking-[-0.045em] text-stone-100">
                  Sign in
                </h1>
                <p className="text-sm leading-6 text-[rgba(167,175,183,0.8)]">
                  Enter your assigned email and password to continue.
                </p>
              </div>

              <form onSubmit={handleLogin} className="space-y-5">
                <div className="space-y-2">
                  <label className="text-[11px] font-medium uppercase tracking-[0.18em] text-[rgba(167,175,183,0.72)]">
                    Email
                  </label>
                  <Input
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="h-11 border-[rgba(127,138,149,0.22)] bg-[rgba(15,18,22,0.74)] text-stone-100 placeholder:text-[rgba(167,175,183,0.46)]"
                    placeholder="name@company.com"
                    required
                  />
                  {!trimmedEmail ? (
                    <p className="text-xs text-[rgba(167,175,183,0.66)]">Use the email assigned by your administrator.</p>
                  ) : null}
                </div>

                <div className="space-y-2">
                  <label className="text-[11px] font-medium uppercase tracking-[0.18em] text-[rgba(167,175,183,0.72)]">
                    Password
                  </label>
                  <Input
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="h-11 border-[rgba(127,138,149,0.22)] bg-[rgba(15,18,22,0.74)] text-stone-100 placeholder:text-[rgba(167,175,183,0.46)]"
                    placeholder="Enter your password"
                    required
                  />
                  {!passwordProvided ? (
                    <p className="text-xs text-[rgba(167,175,183,0.66)]">Temporary passwords must be changed after first sign-in.</p>
                  ) : null}
                </div>

                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="text-[rgba(167,175,183,0.72)]">Cookie-based session</span>
                  <button
                    type="button"
                    className="text-[rgba(198,204,210,0.76)] transition-colors hover:text-stone-100"
                    onClick={() => setForgotPasswordMessage('Contact your administrator to reset your password.')}
                  >
                    Forgot password
                  </button>
                </div>

                {error ? (
                  <p className="rounded-lg border border-[rgba(170,88,84,0.42)] bg-[rgba(88,34,33,0.32)] px-3 py-2 text-sm text-[rgba(255,211,208,0.9)]">
                    {error}
                  </p>
                ) : null}

                {lockMessage ? (
                  <p className="rounded-lg border border-[rgba(196,140,79,0.42)] bg-[rgba(90,58,28,0.34)] px-3 py-2 text-sm text-[rgba(255,228,196,0.92)]">
                    {lockMessage}
                  </p>
                ) : null}

                {forgotPasswordMessage ? (
                  <p className="rounded-lg border border-[rgba(127,138,149,0.26)] bg-[rgba(34,39,45,0.52)] px-3 py-2 text-sm text-[rgba(224,228,232,0.84)]">
                    {forgotPasswordMessage}
                  </p>
                ) : null}

                <Button type="submit" className="h-11 w-full text-sm" loading={loading}>
                  {loading ? 'Signing in...' : 'Sign in'}
                </Button>
              </form>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginPageContent />
    </Suspense>
  );
}

