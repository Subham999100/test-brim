import { describe, expect, it, vi } from 'vitest';
import { bulkDeleteDocuments } from './bulkDeleteDocuments';

const docs = [
  { id: 'a', filename: 'a.pdf' },
  { id: 'b', filename: 'b.pdf' },
  { id: 'c', filename: 'c.pdf' },
];

describe('bulkDeleteDocuments', () => {
  it('deletes every selected document one at a time and totals the purged chunks', async () => {
    const calls: string[] = [];
    let inFlight = 0;
    const deleteOne = vi.fn(async (id: string) => {
      inFlight += 1;
      expect(inFlight).toBe(1);
      calls.push(id);
      await Promise.resolve();
      inFlight -= 1;
      return { deleted_chunks: 10 };
    });

    const result = await bulkDeleteDocuments(docs, deleteOne);

    expect(calls).toEqual(['a', 'b', 'c']);
    expect(result).toEqual({ deletedIds: ['a', 'b', 'c'], failed: [], deletedChunks: 30 });
  });

  it('keeps going after a failure and reports which documents were not deleted', async () => {
    const deleteOne = vi.fn(async (id: string) => {
      if (id === 'b') throw new Error('Document not found');
      return { deleted_chunks: 4 };
    });

    const result = await bulkDeleteDocuments(docs, deleteOne);

    expect(deleteOne).toHaveBeenCalledTimes(3);
    expect(result.deletedIds).toEqual(['a', 'c']);
    expect(result.failed).toEqual([{ id: 'b', filename: 'b.pdf', error: 'Document not found' }]);
    expect(result.deletedChunks).toBe(8);
  });

  it('does nothing for an empty selection', async () => {
    const deleteOne = vi.fn();
    expect(await bulkDeleteDocuments([], deleteOne)).toEqual({ deletedIds: [], failed: [], deletedChunks: 0 });
    expect(deleteOne).not.toHaveBeenCalled();
  });
});
