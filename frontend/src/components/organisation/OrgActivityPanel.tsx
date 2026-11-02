import { useCallback, useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import type { OrgActivity } from '../../types';
import { apiOrgAdminGetActivity } from '../../services/api';
import { formatDateTime } from './orgFormat';

const TOTAL_LABELS: Record<string, string> = {
  members: 'Members',
  active_members: 'Active members',
  chats: 'Chats',
  questions: 'Questions asked',
  shared_answers: 'Shared answers',
  comments: 'Comments',
  likes: 'Likes',
};

/** Per-member usage for organisation admins (GET /org/admin/activity). */
export function OrgActivityPanel() {
  const [activity, setActivity] = useState<OrgActivity | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setActivity(await apiOrgAdminGetActivity());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load activity.');
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    apiOrgAdminGetActivity()
      .then((data) => {
        if (!cancelled) setActivity(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load activity.');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const totals = Object.entries(activity?.totals ?? {}).filter(([, value]) => typeof value === 'number');

  return (
    <section className="org-panel" aria-labelledby="org-activity-title">
      <div className="org-panel-head">
        <div>
          <h2 id="org-activity-title">Activity</h2>
          <p>How each member uses the workspace. Chat content stays private to its author.</p>
        </div>
        <button type="button" className="org-btn" onClick={() => void load()}>
          <RefreshCw size={14} aria-hidden="true" /> Refresh
        </button>
      </div>

      {error && (
        <p className="org-alert" role="alert">
          {error}
        </p>
      )}
      {!activity && !error && (
        <p className="org-form-note" role="status">
          Loading activity…
        </p>
      )}

      {activity && (
        <>
          {totals.length > 0 && (
            <div className="org-stat-grid">
              {totals.map(([key, value]) => (
                <div className="org-stat" key={key}>
                  <strong>{value}</strong>
                  <span>{TOTAL_LABELS[key] ?? key.replace(/_/g, ' ')}</span>
                </div>
              ))}
            </div>
          )}
          <div className="org-table-wrap">
            <table className="org-table">
              <thead>
                <tr>
                  <th scope="col">Member</th>
                  <th scope="col" className="num">Chats</th>
                  <th scope="col" className="num">Questions</th>
                  <th scope="col" className="num">Shared</th>
                  <th scope="col" className="num">Comments</th>
                  <th scope="col" className="num">Likes</th>
                  <th scope="col">Last sign-in</th>
                </tr>
              </thead>
              <tbody>
                {activity.members.length === 0 && (
                  <tr>
                    <td colSpan={7}>No activity yet.</td>
                  </tr>
                )}
                {activity.members.map((member) => (
                  <tr key={member.id}>
                    <td>
                      <strong>{member.name}</strong>
                    </td>
                    <td className="num">{member.chats}</td>
                    <td className="num">{member.questions}</td>
                    <td className="num">{member.shared_answers}</td>
                    <td className="num">{member.comments}</td>
                    <td className="num">{member.likes}</td>
                    <td>{member.last_login_at ? formatDateTime(member.last_login_at) : 'Never'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
