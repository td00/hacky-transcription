import os
import queue
import threading
import sounddevice as sd
from websocket_server import WebsocketServer
from vosk import Model, KaldiRecognizer
import json

SAMPLE_RATE = 16000 ## switch to 8000 for large model
MODEL_PATH = "small"
PORT = 1234

if not os.path.exists(MODEL_PATH):
    print(f"Error: Path '{MODEL_PATH}' not found!")
    exit(1)

model = Model(MODEL_PATH)
recognizer = KaldiRecognizer(model, SAMPLE_RATE)
audio_queue = queue.Queue()

def audio_callback(indata, frames, time, status):
    if status:
        print(f"Error: Audio Error: {status}")
    audio_queue.put(indata.copy())

def transcribe_audio(server):
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=audio_callback):
    #with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=audio_callback, blocksize=8000): ## needed for large model
        print("Starting...")
        while True:
            data = audio_queue.get()
            if recognizer.AcceptWaveform(data.tobytes()):
                result = json.loads(recognizer.Result())
                print(f"Transcribed: {result['text']}") #debug-console
                server.send_message_to_all(json.dumps({"text": result["text"]}))
            else:
                partial = json.loads(recognizer.PartialResult())
                print(f"Transcribing: {partial['partial']}") #debug-console
                server.send_message_to_all(json.dumps({"text": partial["partial"]}))

def new_client(client, server):
    print(f"New Websocket Client: {client['id']}")

server = WebsocketServer(host="0.0.0.0", port=PORT)
server.set_fn_new_client(new_client)

thread = threading.Thread(target=transcribe_audio, args=(server,))
thread.daemon = True
thread.start()

print(f"Websocket Running ws://0.0.0.0:{PORT}")
server.run_forever()
