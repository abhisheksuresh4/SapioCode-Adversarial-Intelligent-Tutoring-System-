import * as faceapi from "face-api.js";
import { useEffect, useRef } from "react";

export default function FaceTracker({ onPerception }) {
  const videoRef = useRef(null);

  useEffect(() => {
    const loadModels = async () => {
      await faceapi.nets.tinyFaceDetector.loadFromUri("/models");
      await faceapi.nets.faceLandmark68Net.loadFromUri("/models");
      await faceapi.nets.faceExpressionNet.loadFromUri("/models");

      startVideo();
    };

    const startVideo = async () => {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      videoRef.current.srcObject = stream;
    };

    loadModels();
  }, []);

  useEffect(() => {
    const interval = setInterval(async () => {
      if (!videoRef.current) return;

      const detections = await faceapi
        .detectSingleFace(
          videoRef.current,
          new faceapi.TinyFaceDetectorOptions()
        )
        .withFaceExpressions();

      if (detections && detections.expressions) {
        console.log("[Perception]", detections.expressions);

        // pass upward later (App.jsx)
        if (onPerception) {
          onPerception(detections.expressions);
        }
      }
    }, 2000); // every 2 seconds

    return () => clearInterval(interval);
  }, [onPerception]);

  return (
    <div>
      <video ref={videoRef} autoPlay muted width="400" />
    </div>
  );
}
