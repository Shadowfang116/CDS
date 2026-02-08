import './globals.css';
import { ConditionalAppShell } from '@/components/layout/conditional-app-shell';

export const metadata = {
  title: 'Bank Diligence Platform',
  description: 'Document management and due diligence platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-900">
        <ConditionalAppShell>
          {children}
        </ConditionalAppShell>
      </body>
    </html>
  );
}

