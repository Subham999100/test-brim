import type { Project } from '../types';
import {
  ApiError,
  apiCreateProject,
  apiDeleteProject,
  apiGetProjects,
  apiUpdateProject,
  type ServerProject,
} from './api';
import { userStorageKey } from './userStorage';

// Projects are stored on the server (2026-11-04). Earlier builds kept them only in this browser's
// localStorage; those are copied to the server once (see importLocalProjects) and then removed here.

/** Fired after a project is created, changed or deleted, so the sidebar and the project page stay in step. */
export const PROJECTS_CHANGED = 'clyptus:projects-changed';

const NAME_MAX = 100;
const DESCRIPTION_MAX = 500;

const toProject = (project: ServerProject): Project => ({
  id: project.id,
  name: project.name,
  description: project.description ?? undefined,
  isPinned: project.is_pinned,
  createdAt: project.created_at,
  updatedAt: project.updated_at,
  chatCount: project.chat_count,
});

const announce = () => {
  try {
    window.dispatchEvent(new Event(PROJECTS_CHANGED));
  } catch {
    // No window (tests, server rendering): nothing to keep in step.
  }
};

// ---------------------------------------------------------------- one-time copy from this browser

interface LocalProject {
  id: string;
  name: string;
  description?: string;
  isPinned?: boolean;
}

// Older builds inserted this pinned sample into every account; it is not copied.
const isUnchangedSample = (project: LocalProject): boolean =>
  project.id === 'proj_brim_core'
  && project.name === 'SAP BRIM Architecture'
  && project.description === 'BRIM Billing, Invoicing and Charging integration flows.';

const localKey = (userId: string) => userStorageKey(userId, 'projects');

const readLocal = (userId: string): LocalProject[] => {
  try {
    const data = localStorage.getItem(localKey(userId));
    const projects: LocalProject[] = data ? JSON.parse(data) : [];
    return Array.isArray(projects) ? projects.filter((project) => project && !isUnchangedSample(project)) : [];
  } catch {
    return [];
  }
};

const writeLocal = (userId: string, projects: LocalProject[]) => {
  try {
    if (projects.length) localStorage.setItem(localKey(userId), JSON.stringify(projects));
    else localStorage.removeItem(localKey(userId));
  } catch {
    // Storage unavailable: the copy is retried next time.
  }
};

const imports = new Map<string, Promise<void>>();

/**
 * Copies the projects this browser saved before projects moved to the server, oldest first (the server lists
 * newest first, as the browser did), removing each one here as soon as it is stored, so a failure is retried
 * later without creating duplicates. A project the server refuses as invalid is dropped.
 */
const importLocalProjects = (userId: string): Promise<void> => {
  const inFlight = imports.get(userId);
  if (inFlight) return inFlight;
  const job = (async () => {
    const pending = readLocal(userId); // newest first
    while (pending.length) {
      const oldest = pending[pending.length - 1];
      try {
        await apiCreateProject({
          name: String(oldest.name ?? '').slice(0, NAME_MAX),
          description: oldest.description ? oldest.description.slice(0, DESCRIPTION_MAX) : undefined,
          is_pinned: Boolean(oldest.isPinned),
        });
      } catch (error) {
        if (!(error instanceof ApiError && error.status === 422)) throw error;
      }
      pending.pop();
      writeLocal(userId, pending);
    }
    writeLocal(userId, pending);
  })().finally(() => imports.delete(userId));
  imports.set(userId, job);
  return job;
};

// ---------------------------------------------------------------- the service

export const projectService = {
  /** The signed-in user's projects, newest first. Copies this browser's old projects first, once. */
  async list(userId: string): Promise<Project[]> {
    try {
      await importLocalProjects(userId);
    } catch {
      // Offline or server error: keep the browser copy and try again on the next load.
    }
    return (await apiGetProjects()).map(toProject);
  },

  async create(values: { name: string; description?: string }): Promise<Project> {
    const project = toProject(await apiCreateProject({ name: values.name, description: values.description }));
    announce();
    return project;
  },

  async update(id: string, updates: { name?: string; description?: string; isPinned?: boolean }): Promise<Project> {
    const changes: { name?: string; description?: string; is_pinned?: boolean } = {};
    if (updates.name !== undefined) changes.name = updates.name;
    if (updates.description !== undefined) changes.description = updates.description;
    if (updates.isPinned !== undefined) changes.is_pinned = updates.isPinned;
    const project = toProject(await apiUpdateProject(id, changes));
    announce();
    return project;
  },

  /** Deletes the project; its chats stay in the chat list. */
  async remove(id: string): Promise<void> {
    await apiDeleteProject(id);
    announce();
  },
};
