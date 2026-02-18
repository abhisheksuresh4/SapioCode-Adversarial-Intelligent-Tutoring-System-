const WINDOW_SIZE = 10;

let buffer = [];

export function smoothCognitiveState(currentState) {
  buffer.push(currentState);

  if (buffer.length > WINDOW_SIZE) {
    buffer.shift();
  }

  const smoothed = {
    engagement: 0,
    confusion: 0,
    frustration: 0,
    boredom: 0
  };

  buffer.forEach(state => {
    smoothed.engagement += state.engagement;
    smoothed.confusion += state.confusion;
    smoothed.frustration += state.frustration;
    smoothed.boredom += state.boredom;
  });

  Object.keys(smoothed).forEach(key => {
    smoothed[key] /= buffer.length;
  });

  return smoothed;
}
