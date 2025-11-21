# app.py
from flask import Flask, request, jsonify, send_from_directory, abort
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse
import os
from datetime import datetime

app = Flask(__name__, static_folder='static')

# In-memory store (volatile)
MESSAGES = []  # newest last
MAX_MESSAGES = 1000

# Read token from environment. If empty or missing, we will skip strict validation
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
if not TWILIO_AUTH_TOKEN:
    # Print a clear warning to logs; server will still run but skip validation
    print('Warning: TWILIO_AUTH_TOKEN not set or empty. Request validation will be SKIPPED.')

# Serve the frontend single-file
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

# Twilio will POST SMS params here
@app.route('/sms', methods=['POST'])
def sms_inbound():
    # Grab params and signature
    params = request.form.to_dict()
    signature = request.headers.get('X-Twilio-Signature', '')
    url = request.url

    # Validate Twilio signature if a token is configured
    if TWILIO_AUTH_TOKEN:
        validator = RequestValidator(TWILIO_AUTH_TOKEN)
        if not validator.validate(url, params, signature):
            # log for debugging
            app.logger.warning('Twilio signature validation failed. URL=%s, params=%s', url, {k: (v[:100] + '...' if len(v) > 100 else v) for k,v in params.items()})
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
        # remove oldest
        del MESSAGES[0: len(MESSAGES) - MAX_MESSAGES]

    # Return an empty TwiML response (no outbound SMS). Change if you want auto-reply.
    resp = MessagingResponse()
    return str(resp), 200, {'Content-Type': 'text/xml'}

# Endpoint used by the frontend to get all messages
@app.route('/messages', methods=['GET'])
def get_messages():
    # Return newest-first for UI convenience
    return jsonify(list(reversed(MESSAGES)))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # bind to 0.0.0.0 so Render can reach it
    app.run(host='0.0.0.0', port=port)
