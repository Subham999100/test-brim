import { describe, expect, it } from 'vitest';
import { markdownToPlainText } from './orgFormat';

describe('markdownToPlainText', () => {
  it('strips Markdown syntax from answer previews but keeps the words', () => {
    expect(markdownToPlainText('Check the billing documents in **FKKINV_MON** first.')).toBe(
      'Check the billing documents in FKKINV_MON first.',
    );
    expect(markdownToPlainText('## Steps\n1. Open `FPL9`\n- See [SAP Help](https://help.sap.com)')).toBe(
      'Steps Open FPL9 See SAP Help',
    );
    expect(markdownToPlainText('Keep snake_case_names and 2*3 intact')).toBe('Keep snake_case_names and 2*3 intact');
  });
});
