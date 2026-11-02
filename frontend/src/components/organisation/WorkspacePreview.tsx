import { Building2, Heart, MessageCircle, Search, Users } from 'lucide-react';
import { HUB_TOPICS } from './portalContent';

// Decorative product preview for the Organisation Portal hero. Illustrative content only.
const sampleAnswers = [
  {
    topic: 'Convergent Invoicing (CI)',
    question: 'Why are billable items stuck in status "billable" after the billing run?',
    by: 'Priya S.',
    likes: 6,
    comments: 3,
    likers: ['PS', 'DK', 'AM'],
  },
  {
    topic: 'SAP BRIM Integration',
    question: 'How does a SOM provider contract reach Convergent Charging?',
    by: 'Daniel K.',
    likes: 4,
    comments: 2,
    likers: ['DK', 'LR'],
  },
];

export function WorkspacePreview() {
  return (
    <figure className="org-preview" aria-label="Preview of an organisation workspace with the Shared Knowledge Hub">
      <div className="org-preview-top">
        <span className="org-preview-org">
          <span className="org-preview-org-icon" aria-hidden="true">
            <Building2 size={15} />
          </span>
          <span>
            <strong>Your organisation</strong>
            <small>
              <Users size={11} aria-hidden="true" /> 24 members · Knowledge Hub
            </small>
          </span>
        </span>
        <span className="org-preview-live">
          <span className="live-dot" /> SHARED
        </span>
      </div>
      <div className="org-preview-search" aria-hidden="true">
        <Search size={13} />
        <span>Search your team's saved answers…</span>
      </div>
      <div className="org-preview-chips" aria-hidden="true">
        <span className="active">All topics</span>
        {HUB_TOPICS.slice(0, 4).map((topic) => (
          <span key={topic.abbreviation}>{topic.abbreviation}</span>
        ))}
      </div>
      <div className="org-preview-cards">
        {sampleAnswers.map((answer) => (
          <div className="org-preview-card" key={answer.question}>
            <span className="org-preview-topic">{answer.topic}</span>
            <p>{answer.question}</p>
            <div className="org-preview-meta">
              <span className="org-preview-avatars" aria-hidden="true">
                {answer.likers.map((initials) => (
                  <span key={initials}>{initials}</span>
                ))}
              </span>
              <span>Shared by {answer.by}</span>
              <span className="org-preview-counts">
                <Heart size={12} aria-hidden="true" /> {answer.likes}
                <MessageCircle size={12} aria-hidden="true" /> {answer.comments}
              </span>
            </div>
          </div>
        ))}
      </div>
      <figcaption className="org-preview-caption">Illustrative preview</figcaption>
    </figure>
  );
}
