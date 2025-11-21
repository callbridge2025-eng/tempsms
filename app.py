# twilio-sms-viewer — Minimal project (Flask backend + single HTML frontend)

Minimal files below — copy into a repo and deploy to Render. No database: messages are stored in memory (volatile).

---

## Files

### `app.py`

```python
from flask import Flask, request, jsonify, send_from_directory, abort
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse
import os
from datetime import datetime

app = Flask(__name__, static_folder='static')

# In-memory store (volatile)
MESSAGES = []  # newest last
MAX_MESSAGES = 1000

TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
if not TWILIO_AUTH_TOKEN:
    print('Warning: TWILIO_AUTH_TOKEN not set. Request validation will fail until set.')

# Serve the frontend single-file
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

# Twilio will POST SMS params here
@app.route('/sms', methods=['POST'])
def sms_inbound():
    # Validate Twilio signature if token is present
    signature = request.headers.get('X-Twilio-Signature', '')
    validator = RequestValidator(TWILIO_AUTH_TOKEN)
    # Twilio validates against the full URL
    url = request.url
    params = request.form.to_dict()
    if TWILIO_AUTH_TOKEN:
        if not validator.validate(url, params, signature):
            abort(403, 'Invalid Twilio signature')

    # Extract core fields
    message = {
        'message_sid': params.get('MessageSid'),
        'from': params.get('From'),
        'to': params.get('To'),
        'body': params.get('Body'),
        'num_media': int(params.get('NumMedia') or 0),
        'received_at': datetime.utcnow().isoformat() + 'Z'
    }

    # Keep memory bounded
    MESSAGES.append(message)
    if len(MESSAGES) > MAX_MESSAGES:
        del MESSAGES[0: len(MESSAGES) - MAX_MESSAGES]

    # Optional: return a tiny TwiML reply (comment out if you don't want to auto-reply)
    resp = MessagingResponse()
    # resp.message('Thanks — message received.')

    return str(resp), 200, {'Content-Type': 'text/xml'}

# Endpoint used by the frontend to get all messages
@app.route('/messages', methods=['GET'])
def get_messages():
    # Return newest-first for UI convenience
    return jsonify(list(reversed(MESSAGES)))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
```

---

### `static/index.html`

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Twilio SMS Viewer — Minimal</title>
  <style>
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;max-width:900px;margin:24px auto;padding:0 12px}
    header{display:flex;align-items:center;justify-content:space-between}
    .msg{border:1px solid #ddd;padding:12px;border-radius:8px;margin:8px 0}
    .meta{font-size:12px;color:#666;margin-bottom:6px}
    #status{font-size:13px;color:#333}
    button{padding:8px 12px;border-radius:6px;border:1px solid #bbb;background:#fff}
  </style>
</head>
<body>
  <header>
    <h1>Twilio SMS Viewer</h1>
    <div>
      <span id="status">—</span>
      <button id="refresh">Refresh</button>
    </div>
  </header>

  <p>Incoming SMS to your Twilio numbers will appear below. Messages are stored in memory only; restarting the app clears them.</p>

  <div id="messages"></div>

  <script>
    const messagesEl = document.getElementById('messages');
    const statusEl = document.getElementById('status');
    const refreshBtn = document.getElementById('refresh');

    async function load(){
      try{
        statusEl.textContent = 'Loading...';
        const res = await fetch('/messages');
        if(!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        statusEl.textContent = data.length + ' messages';
        render(data);
      }catch(err){
        statusEl.textContent = 'Error: ' + err.message;
      }
    }

    function render(list){
      messagesEl.innerHTML = '';
      if(list.length === 0){
        messagesEl.innerHTML = '<p><em>No messages yet.</em></p>';
        return;
      }
      list.forEach(m => {
        const div = document.createElement('div');
        div.className = 'msg';
        div.innerHTML = `
          <div class="meta"><strong>From:</strong> ${escapeHtml(m.from || '')} &nbsp; <strong>To:</strong> ${escapeHtml(m.to || '')} &nbsp; <strong>At:</strong> ${escapeHtml(m.received_at || '')}</div>
          <div>${escapeHtml(m.body || '')}</div>
          <div style="margin-top:8px;font-size:12px;color:#888"><strong>SID:</strong> ${escapeHtml(m.message_sid || '')} — <strong>Media:</strong> ${m.num_media}</div>
        `;
        messagesEl.appendChild(div);
      });
    }

    function escapeHtml(s){
      return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"}[c]));
    }

    refreshBtn.addEventListener('click', load);

    // Auto-refresh every 5 seconds
    load();
    setInterval(load, 5000);
  </script>
</body>
</html>
```

---

### `requirements.txt`

```
Flask>=2.0
twilio>=8.0
python-dotenv>=0.20
gunicorn>=20
```

---

### `.env.example`

```
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
PORT=5000
```

---

## Quick Deploy to Render

1. Push this project to a GitHub repo (root files as above, `static/index.html`).
2. In Render dashboard → New → Web Service → Connect your repo.
3. Set the build command: `pip install -r requirements.txt` (Render infers but you can specify).
4. Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`.
5. In Environment, add `TWILIO_AUTH_TOKEN` with your Twilio Auth Token. Render sets `$PORT` automatically.
6. Deploy.

After deploy you'll have a public URL like `https://your-service.onrender.com/`. Configure **both** Twilio phone numbers:

* In Twilio Console → Phone Numbers → Active Numbers → click a number → Messaging → "A MESSAGE COMES IN" → Webhook → POST → `https://your-service.onrender.com/sms`.

Repeat for the second number.

Notes:

* Messages are stored in memory (no DB) — restarting the server clears them.
* The app validates Twilio signatures when `TWILIO_AUTH_TOKEN` is set. If you're testing locally without the token set, validation will warn and you'll need to disable or set the token.
* If you don't want the app to auto-reply, the TwiML reply is empty (commented out). If you enable `resp.message(...)`, Twilio will send an outgoing SMS (costs apply).

---

## Troubleshooting

* **403 from /sms**: Check the `TWILIO_AUTH_TOKEN` in Render matches your account auth token. Twilio signs requests using your auth token.
* **No messages showing**: Ensure Twilio webhook URL is exactly `https://your-service.onrender.com/sms` and uses HTTP POST. Check Render logs for incoming requests.
* **CORS / Static**: Frontend is served by the same Flask app; no CORS needed.

---

If you'd like, I can:

* convert the project into a single ZIP you can download, or
* paste these files directly into this chat as downloadable files, or
* add optional tiny persistent storage (file-based) if you change your mind about DB.

Tell me which of those you'd like next.
