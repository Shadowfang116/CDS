import { redirect } from "next/navigation";

export default function GlobalAuditRedirectPage() {
  redirect("/governance?tab=audit");
}
