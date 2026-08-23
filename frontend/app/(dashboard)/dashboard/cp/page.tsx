import { redirect } from "next/navigation";

export default function GlobalCpRedirectPage() {
  redirect("/dashboard");
}
