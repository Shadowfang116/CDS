import './globals.css';
import { ConditionalAppShell } from '@/components/layout/conditional-app-shell';
import { ToastProvider } from '@/components/ui/toast';
import { BRAND } from '@/lib/brand';
import { array, notoNastaliqUrdu, sourceSerifDisplay, switzer } from './fonts';
import { cn } from "@/lib/utils";

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
    <html lang="en" className={cn("light", "font-sans", switzer.variable, array.variable, sourceSerifDisplay.variable, notoNastaliqUrdu.variable)} suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
          __html: `(function(){try{var t=localStorage.getItem('bdp_theme');if(t==='dark'){document.documentElement.classList.remove('light');document.documentElement.classList.add('dark');}else{document.documentElement.classList.remove('dark');document.documentElement.classList.add('light');}}catch(e){}})();`,
          }}
        />
      </head>
      <body className="min-h-screen bg-background font-sans antialiased" suppressHydrationWarning>
        <ToastProvider>
          <ConditionalAppShell>
            {children}
          </ConditionalAppShell>
        </ToastProvider>
      </body>
    </html>
  );
}
