import { redirect } from "next/navigation";

export default function AnalyticsRedirectPage() {
  redirect("/governance?tab=portfolio");
}
