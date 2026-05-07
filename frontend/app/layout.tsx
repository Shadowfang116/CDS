import './globals.css';
import { ConditionalAppShell } from '@/components/layout/conditional-app-shell';
import { ToastProvider } from '@/components/ui/toast';
import { BRAND } from '@/lib/brand';

export const metadata = {
  title: BRAND.short,
  description: BRAND.full,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('bdp_theme');if(t==='light'){document.documentElement.classList.remove('dark');document.documentElement.classList.add('light');}else{document.documentElement.classList.add('dark');}}catch(e){}})();`,
          }}
        />
      </head>
      <body className="min-h-screen bg-[var(--bg-primary)] font-sans antialiased">
        <ToastProvider>
          <ConditionalAppShell>
            {children}
          </ConditionalAppShell>
        </ToastProvider>
      </body>
    </html>
  );
}
