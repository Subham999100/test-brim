/** Opens the chat screen so that the first question starts a chat saved in this project. */
export const newChatInProjectPath = (projectId: string): string => `/app?project=${encodeURIComponent(projectId)}`;
