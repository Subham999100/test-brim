import { useCallback, useEffect, useState } from 'react';
import { apiOrgGetSharedMessageIds } from '../services/api';

/**
 * The caller's answers that are already in the organisation knowledge hub, loaded once per page for
 * organisation users so the chat can show "Shared" instead of "Share to organisation".
 */
export function useOrgSharedMessageIds(enabled: boolean) {
  const [sharedIds, setSharedIds] = useState<ReadonlySet<string>>(() => new Set());

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    apiOrgGetSharedMessageIds()
      .then(({ message_ids }) => {
        if (!cancelled) setSharedIds((prev) => new Set([...prev, ...(message_ids ?? [])]));
      })
      // Without the list the chat still offers sharing; the server answers 409 for duplicates.
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [enabled]);

  const markShared = useCallback((messageId: string) => {
    setSharedIds((prev) => (prev.has(messageId) ? prev : new Set([...prev, messageId])));
  }, []);

  return { sharedIds, markShared };
}
