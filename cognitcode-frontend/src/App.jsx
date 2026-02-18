import './App.css'

import FaceTracker from "./perception/FaceTracker";
import { affectToCognition } from "./cognition/affectToCognition";
import { smoothCognitiveState } from "./cognition/cognitiveSmoother";

function App() {
  const handlePerception = (expressions) => {
    console.log("Raw expressions:", expressions);
    const cognitiveState = affectToCognition(expressions);
    const smoothedState = smoothCognitiveState(cognitiveState);   
    console.log("Cognitive state:", cognitiveState);
    console.log("Smoothed cognitive state:", smoothedState);
  
  };

  return (
    <div>
      <h2>SapioCode - Perception Engine</h2>
      <FaceTracker onPerception={handlePerception} />
    </div>
  );
}
export default App;
