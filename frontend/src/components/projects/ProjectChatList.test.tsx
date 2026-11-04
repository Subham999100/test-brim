import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import type { Chat } from '../../types';
import { ProjectChatList } from './ProjectChatList';
import { newChatInProjectPath } from './projectPaths';

const render = (chats: Chat[] | null) =>
  renderToStaticMarkup(
    <MemoryRouter>
      <ProjectChatList projectId="p 1" chats={chats} />
    </MemoryRouter>,
  );

describe('ProjectChatList', () => {
  it('starts a new chat inside the project', () => {
    expect(newChatInProjectPath('p 1')).toBe('/app?project=p%201');
    expect(render([])).toContain('href="/app?project=p%201"');
    expect(render([])).toContain('Chats you start here are saved in this project.');
  });

  it("lists the project's chats as links", () => {
    const html = render([
      { id: 'c1', title: 'Invoice run errors', created_at: '2026-11-03T09:00:00Z', updated_at: '2026-11-04T09:00:00Z', project_id: 'p 1' },
    ]);
    expect(html).toMatch(/<a[^>]*href="\/app\/chat\/c1"[^>]*>[\s\S]*Invoice run errors/);
    expect(html).not.toContain('Chats you start here are saved in this project.');
  });

  it('says it is loading before the chats arrive', () => {
    expect(render(null)).toContain('Loading chats');
  });
});
