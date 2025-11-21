from flask import Flask, request, jsonify, send_from_directory, abort
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse
import os
from datetime import datetime


app = Flask(__name__, static_folder='static')


# In-memory store (volatile)
MESSAGES = [] # newest last
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
app.run(host='0.0.0.0', port=port)
