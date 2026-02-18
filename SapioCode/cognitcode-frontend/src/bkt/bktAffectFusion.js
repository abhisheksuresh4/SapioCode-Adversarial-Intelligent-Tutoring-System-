export function modulateBKT(baseParams, cognitiveState) {
  const { engagement, frustration, confusion, boredom } = cognitiveState;

  let { learn, slip, guess } = baseParams;

  // Engagement accelerates learning
  learn *= 1 + engagement * 0.5;

  // Frustration slows learning
  learn *= 1 - frustration * 0.6;

  // Confusion increases slip
  slip *= 1 + confusion * 0.7;

  // Boredom increases guessing, reduces learning
  guess *= 1 + boredom * 0.5;
  learn *= 1 - boredom * 0.4;

  // Clamp values to valid probability range
  learn = Math.min(Math.max(learn, 0.01), 0.9);
  slip = Math.min(Math.max(slip, 0.01), 0.9);
  guess = Math.min(Math.max(guess, 0.01), 0.9);

  return { learn, slip, guess };
}
