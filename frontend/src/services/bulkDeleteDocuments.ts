export interface BulkDeleteResult {
  deletedIds: string[];
  failed: { id: string; filename: string; error: string }[];
  deletedChunks: number;
}

/**
 * Deletes documents one at a time through the existing single-document endpoint, so each deletion is
 * audited on its own and one failure does not stop the rest.
 */
export const bulkDeleteDocuments = async (
  docs: { id: string; filename: string }[],
  deleteOne: (id: string) => Promise<{ deleted_chunks: number }>,
): Promise<BulkDeleteResult> => {
  const result: BulkDeleteResult = { deletedIds: [], failed: [], deletedChunks: 0 };
  for (const doc of docs) {
    try {
      const res = await deleteOne(doc.id);
      result.deletedIds.push(doc.id);
      result.deletedChunks += res.deleted_chunks || 0;
    } catch (err: any) {
      result.failed.push({ id: doc.id, filename: doc.filename, error: err?.message || 'Failed to delete document' });
    }
  }
  return result;
};
