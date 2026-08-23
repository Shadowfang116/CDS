import { redirect } from "next/navigation";

export default function AdminRedirectPage() {
  redirect("/governance?tab=users");
}
