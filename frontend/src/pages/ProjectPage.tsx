import React, { useEffect, useState } from 'react';
import { ArrowUpRight, MessageSquarePlus, Pin, PinOff, Settings2, Trash2 } from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ProjectChatList } from '../components/projects/ProjectChatList';
import { newChatInProjectPath } from '../components/projects/projectPaths';
import { ProjectModal } from '../components/projects/ProjectModal';
import { apiGetChats } from '../services/api';
import { projectService } from '../services/projectService';
import type { Chat, Project } from '../types';
import { useAuth } from '../context/AuthContext';

const message = (cause: unknown, fallback: string) => (cause instanceof Error ? cause.message : fallback);

export const ProjectPage: React.FC = () => {
  const { projectId = '' } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  // undefined: loading; null: not found (or not this account's).
  const [project, setProject] = useState<Project | null | undefined>(undefined);
  const [chats, setChats] = useState<Chat[] | null>(null);
  const [chatsError, setChatsError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setProject(undefined);
    setChats(null);
    setChatsError(null);
    if (!user?.id) return;
    projectService
      .list(user.id)
      .then((projects) => {
        if (!cancelled) setProject(projects.find((item) => item.id === projectId) ?? null);
      })
      .catch((cause) => {
        if (!cancelled) {
          setProject(null);
          setError(message(cause, 'Could not load the project.'));
        }
      });
    apiGetChats(undefined, projectId)
      .then((data) => {
        if (!cancelled) setChats(data);
      })
      .catch((cause) => {
        if (!cancelled) setChatsError(message(cause, 'Could not load the chats in this project.'));
      });
    return () => {
      cancelled = true;
    };
  }, [user?.id, projectId]);

  if (project === undefined) {
    return (
      <section className="workspace-page project-page">
        <p className="project-empty" role="status">Loading project…</p>
      </section>
    );
  }

  if (project === null) {
    return (
      <section className="workspace-page">
        <div className="workspace-heading">
          <div>
            <span className="eyebrow">PROJECT NOT FOUND</span>
            <h1>This project isn't available.</h1>
            <p>{error ?? 'It may have been removed or updated.'}</p>
          </div>
        </div>
        <Link className="text-link" to="/app">
          Back to chats <ArrowUpRight size={15} />
        </Link>
      </section>
    );
  }

  const renameProject = async (values: { name: string; description?: string }) => {
    setError(null);
    try {
      setProject(await projectService.update(project.id, { name: values.name, description: values.description ?? '' }));
      setEditing(false);
    } catch (cause) {
      setError(message(cause, 'Could not update project.'));
    }
  };

  const removeProject = async () => {
    if (!window.confirm(`Delete "${project.name}"? Its chats stay in your chat list.`)) return;
    try {
      await projectService.remove(project.id);
      navigate('/app', { replace: true });
    } catch (cause) {
      setError(message(cause, 'Could not delete project.'));
    }
  };

  const togglePin = async () => {
    try {
      setProject(await projectService.update(project.id, { isPinned: !project.isPinned }));
      setError(null);
    } catch (cause) {
      setError(message(cause, 'Could not update project pin.'));
    }
  };

  return (
    <>
      <section className="workspace-page project-page">
        <div className="workspace-heading project-heading">
          <div>
            <span className="eyebrow">PROJECT</span>
            <h1>{project.name}</h1>
            <p>{project.description || 'A workspace folder for related SAP conversations.'}</p>
          </div>
          <div className="project-heading-actions">
            <button className="button button-outline button-small" type="button" onClick={togglePin}>
              {project.isPinned ? <PinOff size={14} /> : <Pin size={14} />}
              {project.isPinned ? 'Unpin' : 'Pin'}
            </button>
            <button className="button button-outline button-small" type="button" onClick={() => setEditing(true)}>
              <Settings2 size={14} />
              Rename
            </button>
            <button
              className="button button-dark button-small"
              type="button"
              onClick={() => navigate(newChatInProjectPath(project.id))}
            >
              <MessageSquarePlus size={14} />
              New chat
            </button>
          </div>
        </div>

        {error && <p className="form-error" role="alert">{error}</p>}

        <div className="project-chat-heading">
          <div>
            <h2>Chats</h2>
            <span>{chats ? `${chats.length} saved in this project` : 'Connected to Clyptusap.ai RAG Knowledge'}</span>
          </div>
        </div>

        <ProjectChatList projectId={project.id} chats={chats} error={chatsError} />

        <button className="project-delete-button cursor-pointer" type="button" onClick={removeProject}>
          <Trash2 size={14} /> Delete project
        </button>
      </section>

      {editing && (
        <ProjectModal
          project={project}
          error={error}
          onClose={() => {
            setEditing(false);
            setError(null);
          }}
          onSave={renameProject}
        />
      )}
    </>
  );
};
