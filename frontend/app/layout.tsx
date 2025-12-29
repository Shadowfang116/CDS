import './globals.css';

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
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}

