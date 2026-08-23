import { redirect } from "next/navigation";

export default function ReportsRedirectPage() {
  redirect("/governance?tab=portfolio");
}
