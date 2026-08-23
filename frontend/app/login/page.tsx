'use client';

import { FormEvent, Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ArrowRight } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { BRAND } from '@/lib/brand';
import { ApiError, getMe, login } from '@/lib/api';
import { Atmosphere } from '@/components/cds/atmosphere';

const LOGIN_FIELD_CLASS =
  'h-11 rounded-[2px] border-border bg-transparent shadow-none transition-[border-color] duration-[180ms] ease-out focus-visible:border-foreground focus-visible:ring-0 focus-visible:ring-offset-0';

const LOGIN_BUTTON_CLASS =
  'cds-login-cta h-11 w-full rounded-[2px] bg-primary text-primary-foreground shadow-none transition-[filter,border-color,outline-color] duration-[180ms] ease-out hover:bg-primary hover:brightness-[1.06] hover:shadow-none hover:translate-y-0 active:translate-y-0 focus-visible:ring-0';

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
    <div className="relative min-h-screen bg-background text-foreground" data-page="login" data-surface="atmosphere">
      <Atmosphere enabled behind />
      <div className="relative z-10 mx-auto flex min-h-screen max-w-[1440px] flex-col px-8 py-8 sm:px-10 lg:px-16 lg:py-10">
        <header className="flex items-baseline justify-between gap-6">
          <p className="cds-meta text-muted-foreground">{BRAND.short}</p>
          <p className="cds-meta tabular text-muted-foreground">01 / Secure access</p>
        </header>

        <main className="cds-login-stack mt-8 flex flex-col lg:mt-10">
          <div className="space-y-4">
            <h1 className="cds-login-display">
              <span className="block whitespace-nowrap">Covenant Diligence</span>
              <span className="block">Systems</span>
            </h1>
            <p className="cds-login-subtitle max-w-md text-sm leading-6">
              Property diligence infrastructure for secured banking.
            </p>
          </div>

          <form onSubmit={handleLogin} className="w-full max-w-[420px] space-y-4">
            <div className="space-y-2">
              <label className="cds-meta text-muted-foreground" htmlFor="email">
                Email
              </label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="name@firm.com"
                required
                className={LOGIN_FIELD_CLASS}
              />
            </div>
            <div className="space-y-2">
              <div className="flex items-baseline justify-between gap-4">
                <label className="cds-meta text-muted-foreground" htmlFor="password">
                  Password
                </label>
                <button
                  type="button"
                  className="cds-login-quiet text-xs tracking-wide transition-colors duration-[180ms] hover:text-foreground"
                  onClick={() => setForgotPasswordMessage('Contact your administrator to reset your password.')}
                >
                  Recover access
                </button>
              </div>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                className={LOGIN_FIELD_CLASS}
              />
            </div>
            {error ? <p className="text-sm text-primary">{error}</p> : null}
            {lockMessage ? <p className="text-sm text-muted-foreground">{lockMessage}</p> : null}
            {forgotPasswordMessage ? <p className="text-sm text-muted-foreground">{forgotPasswordMessage}</p> : null}
            <Button type="submit" className={LOGIN_BUTTON_CLASS} loading={loading}>
              <span>{loading ? 'Signing in' : 'Sign in'}</span>
              {loading ? null : <ArrowRight className="cds-login-cta-arrow" />}
            </Button>
          </form>
        </main>

        <aside className="cds-login-anchor pointer-events-none absolute bottom-14 right-16 hidden text-right lg:bottom-16 lg:right-24 sm:block">
          <p className="cds-meta leading-5">Private system</p>
          <p className="cds-meta leading-5">Role controlled</p>
          <p className="cds-meta leading-5">Audit logged</p>
        </aside>
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
