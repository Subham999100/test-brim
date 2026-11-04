import React from 'react';
import { ArrowUpRight, MessageSquarePlus } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { Chat } from '../../types';
import { newChatInProjectPath } from './projectPaths';

const lastActivity = (iso: string): string => {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? ''
    : date.toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
};

/** The chats saved in a project, newest activity first, or the way to start the first one. */
export const ProjectChatList: React.FC<{ projectId: string; chats: Chat[] | null; error?: string | null }> = ({
  projectId,
  chats,
  error,
}) => {
  if (error) {
    return (
      <div className="project-chat-list">
        <p className="form-error" role="alert">{error}</p>
      </div>
    );
  }
  if (chats === null) {
    return (
      <div className="project-chat-list">
        <p className="project-empty" role="status">Loading chats…</p>
      </div>
    );
  }
  if (chats.length === 0) {
    return (
      <div className="project-chat-list">
        <div className="project-empty">
          <MessageSquarePlus size={24} className="text-orange-500 mb-2" aria-hidden="true" />
          <strong>Start a new conversation in this project</strong>
          <span>Chats you start here are saved in this project.</span>
          <Link className="button button-dark button-small mt-3" to={newChatInProjectPath(projectId)}>
            Start Chat <ArrowUpRight size={14} aria-hidden="true" />
          </Link>
        </div>
      </div>
    );
  }
  return (
    <ul className="project-chat-list" aria-label="Chats in this project">
      {chats.map((chat) => (
        <li className="project-chat-row" key={chat.id}>
          <Link to={`/app/chat/${chat.id}`}>
            <strong>{chat.title}</strong>
            <span>{lastActivity(chat.updated_at)}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
};
