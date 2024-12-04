import os
import queue
import threading
import sounddevice as sd
from websocket_server import WebsocketServer
from vosk import Model, KaldiRecognizer
import json

import sys
import os

__DEBUG_LOGS = "DEBUG_LOGS" in os.environ

def audio_callback(indata, frames, time, status):
    if status:
        print(f"Error: Audio Error: {status}")
    audio_queue.put(indata.copy())

def transcribe_audio(server, recognizer, audio_queue, samplerate, blocksize):
    with sd.InputStream(samplerate=sample_rate, channels=1, dtype="int16", callback=audio_callback, blocksize=blocksize):
        if __DEBUG_LOGS:
            print("Starting...")

        while True:
            data = audio_queue.get()
            if recognizer.AcceptWaveform(data.tobytes()):
                result = json.loads(recognizer.Result())
                server.send_message_to_all(json.dumps({"text": result["text"], "partial": False}))

                if __DEBUG_LOGS:
                    print(f"Transcribed: {result['text']}")
            else:
                partial = json.loads(recognizer.PartialResult())
                server.send_message_to_all(json.dumps({"text": partial["partial"], "partial": True}))

                if __DEBUG_LOGS:
                    print(f"Transcribing: {partial['partial']}")

def new_client(client, server):
    if __DEBUG_LOGS:
        print(f"New Websocket Client: {client['id']}")

def __exit_usage():
    print("Usage: transcribe.py {small|large} {model_path}", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        __exit_usage()

    if sys.argv[1] in ("help", "-h", "--help"):
        __exit_usage()

    model = sys.argv[1]

    if model not in ("small", "large"):
        printf(f"Invalid model: {model}", file=sys.stderr)
        __exit_usage()

    model_path = sys.argv[2]

    if not os.path.exists(model_path):
        printf(f"Model not found: {model_path}", file=sys.stderr)
        __exit_usage()

    if model == "small":
        sample_rate = 16000
        blocksize = None
    else:
        sample_rate = 8000
        blocksize = 8000

    model = Model(model_path)
    recognizer = KaldiRecognizer(model, sample_rate)
    audio_queue = queue.Queue()

    port = 1234
    server = WebsocketServer(host="0.0.0.0", port=port)
    server.set_fn_new_client(new_client)

    thread = threading.Thread(target=transcribe_audio, args=(server, recognizer, audio_queue, sample_rate, blocksize))
    thread.daemon = True
    thread.start()

    print(f"Websocket Running ws://0.0.0.0:{port}")
    server.run_forever()
