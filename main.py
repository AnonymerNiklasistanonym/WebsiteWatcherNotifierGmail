import requests
import base64
from bs4 import BeautifulSoup
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import mimetypes


# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def get_page_content(url, element_tag, element_tag_specifier,
                     tags_to_drop = ["script", "form"],
                     attributes_to_drop = ["class", "id", "name", "style", "align"]):
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    # Extract content that should be checked
    mydivs = soup.findAll(element_tag, element_tag_specifier)
    if len(mydivs) != 1:
        raise Exception("{}s (with {}) are either not found or too many ({})!".format(element_tag, element_tag_specifier, len(mydivs)))
    div = mydivs[0]
    # Clean script tags and forms from content
    for tag_to_drop in tags_to_drop:
        for s in div.select(tag_to_drop):
            s.decompose()
    for tag in div():
        for attribute in attributes_to_drop:
            del tag[attribute]
    return str(div)

def create_message(sender, to, subject, message_text):
    """Create a message for an email.

    Args:
        sender: Email address of the sender.
        to: Email address of the receiver.
        subject: The subject of the email message.
        message_text: The text of the email message.

    Returns:
        An object containing a base64url encoded email object.
    """
    message = MIMEText(message_text, 'html')
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    return {'raw': base64.urlsafe_b64encode(message.as_string().encode()).decode()}

def send_message(service, user_id, message):
    try:
        message = service.users().messages().send(userId=user_id, body=message).execute()
        print('Message Id: %s' % message['id'])
        return message
    except Exception as e:
        print('An error occurred: %s' % e)
        return None

def get_service():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

if __name__ == '__main__':
    # Download credentials.json from https://developers.google.com/gmail/api/quickstart/python
    new_content = get_page_content(url="https://www.nubert.de/stative-halter/38/",
                                   element_tag="div",
                                   element_tag_specifier={"class": "main-column"})
    content_file_name = 'content.html'
    if os.path.isfile(content_file_name):
        with open(content_file_name, 'r') as file:
            old_content = file.read()
            if old_content == new_content:
                print("no change")
                exit(0)
            else:
                print("change detected")
                print(old_content, new_content)
    with open(content_file_name, 'w') as file:
        file.write(new_content)
    service = get_service()
    message = create_message(sender='your.email@gmail.com',
                             to='your.email@gmail.com',
                             subject='Nubert speaker stands were updated',
                             message_text=new_content)
    send_message(service, 'me', message)
