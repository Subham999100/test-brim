import {
  BadgeCheck,
  Bell,
  Bot,
  Boxes,
  Building2,
  FileText,
  FolderTree,
  Gauge,
  GitMerge,
  KeyRound,
  Layers,
  Lock,
  MessageSquareText,
  MessagesSquare,
  Network,
  Share2,
  ShieldCheck,
  Users,
  UserPlus,
  Wrench,
  Workflow,
  Eye,
  EyeOff,
  Fingerprint,
  Settings2,
  type LucideIcon,
} from 'lucide-react';

// Copy for the Organisation Portal landing page (product-owner approved wording).

export const PORTAL_HEADING = 'Welcome to Your Organisation Workspace';
export const PORTAL_SUBCOPY =
  'Create your organisation, invite your team members, and collaborate in a shared AI-powered knowledge environment.';

export const PORTAL_CAPABILITIES: ReadonlyArray<{ text: string; icon: LucideIcon }> = [
  { text: 'Create and manage your organisation', icon: Building2 },
  { text: 'Add and manage organisation members', icon: UserPlus },
  { text: 'Provide individual login credentials to each member', icon: KeyRound },
  { text: 'Allow team members to interact with the AI chatbot', icon: MessageSquareText },
  { text: 'Share useful AI-generated answers with your organisation', icon: Share2 },
  { text: 'Organise saved answers into topic-based categories', icon: FolderTree },
  { text: 'Comment on saved answers and participate in discussions', icon: MessagesSquare },
  { text: 'View which organisation members liked, saved, or commented on each answer', icon: Eye },
];

export const PORTAL_STEPS: ReadonlyArray<{ title: string; text: string; icon: LucideIcon }> = [
  { title: 'Request', text: 'Tell us about your organisation with the short request form.', icon: Bell },
  { title: 'Super Admin approval', text: 'A Clyptus Super Admin reviews and approves the workspace.', icon: BadgeCheck },
  { title: 'Activation code', text: 'Your administrator receives a single-use, time-limited activation code.', icon: KeyRound },
  { title: 'Set up admin account', text: 'Enter the code, then set the administrator name and password.', icon: ShieldCheck },
  { title: 'Add members', text: 'Create member accounts; each person gets individual credentials.', icon: Users },
  { title: 'Collaborate in the Knowledge Hub', text: 'Share useful answers in one click, organise them by topic and discuss them.', icon: Layers },
];

/** The SAP BRIM topics answers are organised into in the Shared Knowledge Hub. */
export const HUB_TOPICS: ReadonlyArray<{ abbreviation: string; label: string; icon: LucideIcon }> = [
  { abbreviation: 'CC', label: 'Convergent Charging', icon: Gauge },
  { abbreviation: 'CI', label: 'Convergent Invoicing', icon: FileText },
  { abbreviation: 'SOM', label: 'Subscription Order Management', icon: Boxes },
  { abbreviation: 'FI-CA', label: 'Contract Accounting', icon: Layers },
  { abbreviation: 'INT', label: 'SAP BRIM Integration', icon: GitMerge },
  { abbreviation: 'FIX', label: 'Troubleshooting', icon: Wrench },
  { abbreviation: 'ARC', label: 'Architecture and Configuration', icon: Settings2 },
];

export const AGENTIC_DESCRIPTION =
  "We are developing an advanced Agentic AI chatbot that can securely interact with your organisation's authorised portal and perform tasks based on your permissions.";

export const AGENTIC_HIGHLIGHTS: ReadonlyArray<{ text: string; icon: LucideIcon }> = [
  { text: 'Secure portal integration', icon: Network },
  { text: 'Permission-based access', icon: Lock },
  { text: 'Automated workflows through AI agents', icon: Workflow },
  { text: 'Secure handling of organisation data', icon: ShieldCheck },
  { text: 'Authentication and authorisation controls', icon: Fingerprint },
  { text: 'No direct visibility of login credentials to developers', icon: EyeOff },
];

export const AGENTIC_SECURITY_STATEMENT =
  'Credentials will be encrypted or securely tokenised, every agent action will run with least-privilege access, and sensitive information will never be exposed in logs or developer interfaces.';

export const AGENTIC_ICON = Bot;

export const REQUEST_SUCCESS_MESSAGE =
  'Thank you. Your request has been received. If it is approved, a Clyptus administrator will contact you with an activation code for your organisation.';
