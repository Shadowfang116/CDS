"use client";

import { SidebarTrigger } from "@/components/ui/sidebar";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { NotificationBell } from "./NotificationBell";

export function AppHeader() {
  const user = useCurrentUser();

  function handleLogout() {
    // TODO: clear session / token and redirect to login
    window.location.href = "/";
  }

  return (
    <header className="flex h-14 shrink-0 items-center gap-4 border-b px-4">
      <SidebarTrigger className="-ml-1" />
      <div className="flex flex-1 text-sm font-medium">
        Dashboard
      </div>

      <div className="flex items-center gap-3">
        <NotificationBell />
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Avatar className="h-8 w-8 cursor-pointer border">
            <AvatarFallback className="text-xs">
              {user?.email?.[0]?.toUpperCase() ?? "U"}
            </AvatarFallback>
          </Avatar>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuItem disabled className="font-normal">
            <span className="truncate">{user?.email ?? "—"}</span>
          </DropdownMenuItem>
          <DropdownMenuItem onClick={handleLogout}>
            Logout
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
