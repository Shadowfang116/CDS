import { redirect } from "next/navigation";

export default function CdsRedirectPage() {
  redirect("/governance?tab=portfolio");
}
