import { redirect } from "next/navigation";

export default function GlobalDocumentsRedirectPage() {
  redirect("/dashboard");
}
