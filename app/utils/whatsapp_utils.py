import logging
from flask import current_app, jsonify
import json
import requests
import openai
# from app.services.openai_service import generate_response
import re
import google.generativeai as genai
import urllib.request 
from io import BytesIO
from PIL import Image

import json

genai.configure(api_key='AIzaSyCVSPwfCwvG7U-oMzWg8glv0oZt5-A1mjY')

# Initialize the model
# model = genai.GenerativeModel('gemini-pro')
model = genai.GenerativeModel('gemini-1.5-flash')

def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )

def gemini(response):

   
    img = Image.open(BytesIO(response.content))


    # Generate content
    response = model.generate_content(img)

    # Print the response
    print(response.text)
    return response.text


def generate_response(response):
    # Return text in uppercase
    # completion = openai.chat.completions.create(
    #     model="gpt-4",
    #     messages=[
    #         {
    #             "role": "user",
    #             "content": response
    #         },
    #     ],
    # )
    # print(completion.choices[0].message.content)
    # return completion.choices[0].message.content

    resp = model.generate_content(response)

    return resp.text


def process_image(id):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    ai_answer=''

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{id}?{current_app.config['PHONE_NUMBER_ID']}"

    try:
        response = requests.get(
            url, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        # Process the response as normal
        suc_message=response.text
        print(type(suc_message))
        json_object = json.loads(suc_message)

        # Print the resulting dictionary
        print(json_object)
        print()
        imageurl = json_object['url']

        try:

            fetchImage = requests.get(
                imageurl, headers=headers, timeout=10
            )

            ai_answer= gemini(fetchImage)
            
        except (
            requests.RequestException
        ) as e:  # This will catch any general request exception
            logging.error(f"Request failed due to: {e}")
            return jsonify({"status": "error", "message": "Failed to send message"}), 500

        # log_http_response(response)
        return ai_answer


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        # Process the response as normal
        log_http_response(response)
        return response


def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text


def process_whatsapp_message(body):
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]

    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    print("from utils")
    receipent= message['from']
    print(message['from'])

    if message['type']=='image':

        # TODO: implement custom function here

        response = process_image(message['image']['id'])
        print(response)
    else:
        # OpenAI Integration
        message_body = message["text"]["body"]
        response = generate_response(message_body)  
        response = process_text_for_whatsapp(response)

    data = get_text_message_input(receipent, response)
    send_message(data)


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )
