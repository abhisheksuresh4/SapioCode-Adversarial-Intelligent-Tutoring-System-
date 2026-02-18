export function affectToCognition(expressions) {
  const {
    happy = 0,
    sad = 0,
    angry = 0,
    fearful = 0,
    surprised = 0,
    neutral = 0
  } = expressions;

  const engagement =
    happy * 0.6 +
    surprised * 0.4;

  const confusion =
    surprised * 0.6 +
    sad * 0.4;

  const frustration =
    angry * 0.5 +
    fearful * 0.3 +
    sad * 0.2;

  const boredom =
    neutral * 0.8 -
    (happy + surprised) * 0.4;

  return {
    engagement: clamp(engagement),
    confusion: clamp(confusion),
    frustration: clamp(frustration),
    boredom: clamp(boredom)
  };
}

function clamp(value) {
  return Math.max(0, Math.min(1, value));
}
