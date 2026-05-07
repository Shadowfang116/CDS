'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  listNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  getUnreadNotificationCount,
  Notification,
} from '@/lib/api';
import { getCaseDetailPath } from '@/lib/routes';

// Format relative time
function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export function NotificationBell() {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  // Fetch unread count on mount and periodically
  const fetchUnreadCount = useCallback(async () => {
    try {
      const result = await getUnreadNotificationCount();
      setUnreadCount(result.unread_count);
    } catch {
      // Silently fail
    }
  }, []);

  // Fetch notifications when panel opens
  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const result = await listNotifications(false, 20);
      setNotifications(result.notifications);
      setUnreadCount(result.unread_count);
    } catch {
      // Silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000); // Every 30s
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

  useEffect(() => {
    if (isOpen) {
      fetchNotifications();
    }
  }, [isOpen, fetchNotifications]);

  // Close panel on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const handleMarkRead = async (id: string) => {
    try {
      await markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {
      // Silently fail
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      // Silently fail
    }
  };

  const handleNotificationClick = (notification: Notification) => {
    handleMarkRead(notification.id);
    setIsOpen(false);

    // Navigate based on entity type
    if (notification.entity_type === 'approval' && notification.entity_id) {
      router.push('/approvals');
    } else if (notification.case_id) {
      router.push(getCaseDetailPath(notification.case_id));
    }
  };

  const severityColors: Record<string, string> = {
    info: 'bg-[rgba(126,133,111,0.16)] text-[rgb(194,200,185)]',
    warning: 'bg-[rgba(184,151,95,0.16)] text-[rgb(219,194,137)]',
    critical: 'bg-[rgba(189,90,86,0.16)] text-[rgb(219,156,153)]',
  };

  return (
    <div className="relative" ref={panelRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative rounded-md border border-transparent p-2 transition-colors hover:border-[rgba(82,90,99,0.35)] hover:bg-[rgba(34,39,45,0.9)]"
        aria-label="Notifications"
      >
        <BellIcon className="h-5 w-5 text-stone-400" />
        {unreadCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-[rgba(151,70,67,0.98)] text-[10px] font-bold text-white">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full z-50 mt-2 w-80 overflow-hidden rounded-lg border border-[rgba(82,90,99,0.5)] bg-[rgba(29,34,39,0.98)] shadow-[0_18px_48px_rgba(0,0,0,0.35)] sm:w-96">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-[rgba(82,90,99,0.38)] bg-[rgba(24,28,32,0.96)] px-4 py-3">
            <h3 className="text-sm font-semibold uppercase tracking-[0.08em] text-stone-200">Notifications</h3>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs font-medium text-stone-400 hover:text-stone-200"
              >
                Mark all read
              </button>
            )}
          </div>

          {/* Notification list */}
          <div className="max-h-96 overflow-y-auto">
            {loading ? (
              <div className="p-4 text-center text-sm text-stone-500">Loading...</div>
            ) : notifications.length === 0 ? (
              <div className="p-8 text-center">
                <BellIcon className="mx-auto mb-2 h-8 w-8 text-stone-600" />
                <p className="text-sm text-stone-500">No notifications yet</p>
              </div>
            ) : (
              <div className="divide-y divide-[rgba(82,90,99,0.3)]">
                {notifications.map((notification) => (
                  <button
                    key={notification.id}
                    onClick={() => handleNotificationClick(notification)}
                    className={`w-full px-4 py-3 text-left transition-colors hover:bg-[rgba(34,39,45,0.9)] ${
                      !notification.is_read ? 'bg-[rgba(34,39,45,0.65)]' : ''
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${
                          notification.is_read ? 'bg-stone-700' : 'bg-[rgba(126,133,111,0.92)]'
                        }`}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span
                            className={`rounded px-1.5 py-0.5 text-[10px] uppercase tracking-[0.08em] ${
                              severityColors[notification.severity] || severityColors.info
                            }`}
                          >
                            {notification.severity}
                          </span>
                          <span className="text-[10px] text-stone-500">
                            {formatRelativeTime(notification.created_at)}
                          </span>
                        </div>
                        <p className="truncate text-sm font-medium text-stone-200">
                          {notification.title}
                        </p>
                        {notification.body && (
                          <p className="mt-0.5 line-clamp-2 text-xs text-stone-500">
                            {notification.body}
                          </p>
                        )}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-[rgba(82,90,99,0.3)] bg-[rgba(24,28,32,0.96)] px-4 py-2">
            <button
              onClick={() => {
                setIsOpen(false);
                router.push('/approvals');
              }}
              className="text-xs font-medium text-stone-400 hover:text-stone-200"
            >
              View all activity
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function BellIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
      />
    </svg>
  );
}

