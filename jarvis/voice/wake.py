"""Wake-word detection using openWakeWord — fully local, no API key.

Loads ONLY the 'hey_jarvis' model (not the other 5 bundled wake words),
which means ~6× less CPU per audio frame than loading all defaults.
"""
from pathlib import Path

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
FRAME_LENGTH = 1280            # 80 ms @ 16 kHz — openWakeWord's expected chunk size
DETECTION_THRESHOLD = 0.4      # 0.0-1.0; higher = fewer false positives
DEBUG_PRINT_SCORES = True      # Set False once wake word is reliable.
DEBUG_PRINT_FLOOR = 0.15       # Print scores above this so you can see "almost" hits.


def _find_hey_jarvis_onnx() -> str:
    """Locate the bundled hey_jarvis ONNX model file inside the openwakeword package."""
    import openwakeword
    pkg_dir = Path(openwakeword.__file__).parent
    for candidate in (
        pkg_dir / "resources" / "models" / "hey_jarvis_v0.1.onnx",
        pkg_dir / "models" / "hey_jarvis_v0.1.onnx",
    ):
        if candidate.exists():
            return str(candidate)
    # Search fallback in case the layout changes.
    for path in pkg_dir.rglob("hey_jarvis*.onnx"):
        return str(path)
    raise FileNotFoundError(
        "Could not locate hey_jarvis_v0.1.onnx inside the openwakeword package. "
        "Run: python -c \"import openwakeword.utils; openwakeword.utils.download_models()\""
    )


class WakeWordListener:
    def __init__(self, keyword: str | None = None) -> None:
        # `keyword` accepted for API compatibility; this listener is hardcoded to hey_jarvis.
        _ = keyword
        try:
            import openwakeword
            import openwakeword.utils
            from openwakeword.model import Model
        except ImportError as e:
            raise RuntimeError(
                "openwakeword not installed. Run: pip install openwakeword onnxruntime"
            ) from e

        # Ensure models are downloaded once (cached afterward).
        try:
            openwakeword.utils.download_models()
        except Exception as e:
            print(f"[wake] model download note: {e}")

        model_path = _find_hey_jarvis_onnx()
        try:
            # Load ONLY hey_jarvis. Massive speed win vs. loading all 6 defaults.
            self.model = Model(wakeword_models=[model_path], inference_framework="onnx")
        except Exception as e:
            raise RuntimeError(f"Failed to load wake-word model from {model_path}: {e}") from e

        self.target_key = next(iter(self.model.models.keys()))
        print(f"[wake] listening for: '{self.target_key}' (1 model loaded)")

    def wait_for_wake(self) -> None:
        """Block until the wake word is detected."""
        peak = 0.0
        with sd.InputStream(
            channels=1,
            samplerate=SAMPLE_RATE,
            dtype="int16",
            blocksize=FRAME_LENGTH,
        ) as stream:
            while True:
                pcm, _overflow = stream.read(FRAME_LENGTH)
                samples = np.asarray(pcm, dtype=np.int16).flatten()
                scores = self.model.predict(samples)
                score = scores.get(self.target_key, 0.0)
                if DEBUG_PRINT_SCORES and score >= DEBUG_PRINT_FLOOR:
                    if score > peak:
                        peak = score
                        print(f"[wake-debug] score={score:.2f} (peak={peak:.2f}, threshold={DETECTION_THRESHOLD})")
                if score >= DETECTION_THRESHOLD:
                    return

    def close(self) -> None:
        return
