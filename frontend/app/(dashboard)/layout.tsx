// AppShell is applied by ConditionalAppShell (root layout) for all non-auth routes.
// This group only wraps dashboard route segments; no duplicate shell here.
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
