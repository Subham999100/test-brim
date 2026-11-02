import type { Message, MessageFeedback, User } from '../../types';
import { isOrgUser } from '../../layouts/accountRouting';
import { isStoredMessage } from './messageUtils';

export type OrgShareState = 'hidden' | 'share' | 'shared';

// Answers that are not real SAP answers are never offered for sharing.
const NOT_SHAREABLE = new Set<Message['source_type']>(['error', 'interrupted', 'refusal', 'security_policy']);

/**
 * "Share to organisation" rules (docs/ORGANISATION_PORTAL.md): organisation users only, stored assistant
 * answers only, offered after the answer is liked; answers already in the hub show "Shared".
 */
export const orgShareState = ({
  user,
  message,
  feedback,
  sharedIds,
  isStreaming = false,
}: {
  user: Pick<User, 'account_type'> | null | undefined;
  message: Message;
  feedback: MessageFeedback | null;
  sharedIds?: ReadonlySet<string>;
  isStreaming?: boolean;
}): OrgShareState => {
  if (!isOrgUser(user) || message.role !== 'assistant' || isStreaming || !isStoredMessage(message)) return 'hidden';
  if (sharedIds?.has(message.id)) return 'shared';
  if (NOT_SHAREABLE.has(message.source_type)) return 'hidden';
  return feedback === 'up' ? 'share' : 'hidden';
};
