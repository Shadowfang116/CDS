import { redirect } from "next/navigation";

export default function GlobalExceptionsRedirectPage() {
  redirect("/dashboard");
}
