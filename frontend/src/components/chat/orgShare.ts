import type { Message, User } from '../../types';
import { isOrgUser } from '../../layouts/accountRouting';
import { isStoredMessage } from './messageUtils';

export type OrgShareState = 'hidden' | 'share' | 'shared';

// Answers that are not real SAP answers are never offered for sharing.
const NOT_SHAREABLE = new Set<Message['source_type']>(['error', 'interrupted', 'refusal', 'security_policy']);

/**
 * Organisation sharing rules (docs/ORGANISATION_PORTAL.md): organisation users only, stored assistant
 * answers only, in one click (no like needed); answers already in the hub show "Shared".
 */
export const orgShareState = ({
  user,
  message,
  sharedIds,
  isStreaming = false,
}: {
  user: Pick<User, 'account_type'> | null | undefined;
  message: Message;
  sharedIds?: ReadonlySet<string>;
  isStreaming?: boolean;
}): OrgShareState => {
  if (!isOrgUser(user) || message.role !== 'assistant' || isStreaming || !isStoredMessage(message)) return 'hidden';
  if (sharedIds?.has(message.id)) return 'shared';
  return NOT_SHAREABLE.has(message.source_type) ? 'hidden' : 'share';
};
