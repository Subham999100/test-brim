import type { Project } from '../types';
import { userStorageKey } from './userStorage';

// Older builds inserted this pinned sample into every account. Hide only the
// unchanged sample; retain projects an account has renamed or customised.
const isUnchangedSample = (project: Project): boolean =>
  project.id === 'proj_brim_core'
  && project.name === 'SAP BRIM Architecture'
  && project.description === 'BRIM Billing, Invoicing and Charging integration flows.';

const storageKey = (userId: string) => userStorageKey(userId, 'projects');

export const projectService = {
  getProjects(userId: string): Project[] {
    try {
      const data = localStorage.getItem(storageKey(userId));
      const projects: Project[] = data ? JSON.parse(data) : [];
      return projects.filter((project) => !isUnchangedSample(project));
    } catch {
      return [];
    }
  },

  createProject(userId: string, name: string, description?: string): Project {
    const projects = this.getProjects(userId);
    const newProj: Project = {
      id: 'proj_' + Date.now().toString(36),
      name,
      description,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      isPinned: false,
    };
    localStorage.setItem(storageKey(userId), JSON.stringify([newProj, ...projects]));
    return newProj;
  },

  updateProject(userId: string, id: string, updates: Partial<Pick<Project, 'name' | 'description' | 'isPinned'>>): Project {
    const projects = this.getProjects(userId);
    let updatedProj: Project | null = null;
    const updated = projects.map((project) => {
      if (project.id !== id) return project;
      updatedProj = { ...project, ...updates, updatedAt: new Date().toISOString() };
      return updatedProj;
    });
    localStorage.setItem(storageKey(userId), JSON.stringify(updated));
    if (!updatedProj) throw new Error('Project not found');
    return updatedProj;
  },

  deleteProject(userId: string, id: string): void {
    const projects = this.getProjects(userId).filter((project) => project.id !== id);
    localStorage.setItem(storageKey(userId), JSON.stringify(projects));
  },
};
