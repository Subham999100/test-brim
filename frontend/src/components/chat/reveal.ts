/**
 * Characters the typewriter reveals per 20 ms tick, given how far it is behind the received text.
 * In a background tab browsers run timers once a second (or once a minute after a while), which made answers
 * look stuck; there is nobody to watch the animation, so everything received is shown at once.
 */
export const revealStep = (behind: number, hidden: boolean): number => {
  if (hidden) return behind;
  if (behind > 120) return Math.ceil(behind / 4);
  if (behind > 40) return 6;
  if (behind > 15) return 3;
  if (behind > 4) return 2;
  return 1;
};
