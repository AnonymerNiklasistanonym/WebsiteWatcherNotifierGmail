from typing import Optional, List

import requests
import base64
from bs4 import BeautifulSoup
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.mime.text import MIMEText
from lxml.html.diff import htmldiff

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def get_web_page_content(url: str, element_tag: str, element_tag_specifier: dict,
                         tags_to_drop: Optional[List[str]] = None,
                         attributes_to_drop: Optional[List[str]] = None) -> str:
    """Scrape web page for a certain part.

    Args:
        url: Web page address.
        element_tag: HTML element tag that should be looked for.
        element_tag_specifier: Specifier for certain id ({id: '...'}) or class ({class: '...'}).
        tags_to_drop: Optional list of HTML tags that should be dropped from the web page output.
        attributes_to_drop: Optional list of HTML tag attributes that should be dropped from the web page output.

    Returns:
        A string that contains a certain part of the website while missing unnecessary style or other information.
    """
    if attributes_to_drop is None:
        attributes_to_drop = ['class', 'id', 'name', 'style', 'align']
    if tags_to_drop is None:
        tags_to_drop = ['script', 'form']

    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    # Extract content that should be checked
    found_elements = soup.findAll(element_tag, element_tag_specifier)
    if len(found_elements) != 1:
        raise Exception("{}s (with {}) are either not found or too many ({})!".format(element_tag,
                                                                                      element_tag_specifier,
                                                                                      len(found_elements)))
    element = found_elements[0]
    # Remove specified script tags
    for tag_to_drop in tags_to_drop:
        for s in element.select(tag_to_drop):
            s.decompose()
    # Remove specified attributes from tags
    for tag in element():
        for attribute in attributes_to_drop:
            del tag[attribute]
    return str(element)


def create_gmail_email(sender: str, to: str, subject: str, message_text: str):
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


def send_gmail_email(service, user_id: str, message):
    """Send a message using the GMail API service.

    Args:
        service: GMail API service.
        user_id: GMail API service user id.
        message: An GMail API compatible email object.

    Returns:
        Sent email information if successful.
    """
    try:
        sent_message_info = service.users().messages().send(userId=user_id, body=message).execute()
        print('Message Id: %s' % sent_message_info['id'])
        return sent_message_info
    except Exception as e:
        print('An error occurred: %s' % e)
        return None


def get_gmail_service():
    """Get the GMail API service."""
    credentials = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            credentials = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(credentials, token)

    return build('gmail', 'v1', credentials=credentials)


def detect_change(file_name: str, new_content: str) -> Optional[str]:
    """Detect if the content in a file differs from a given string.

    Args:
        file_name: The file that contains the string for comparison.
        new_content: The string that should be compared with the file contained string.

    Returns:
        The difference between the contents if there was a change, else None.
    """
    difference_was_detected = False
    change = None
    if os.path.isfile(file_name):
        with open(file_name, 'r') as file:
            old_content = file.read()
            if old_content != new_content:
                difference_was_detected = True
                change = htmldiff(old_content, new_content)
    else:
        difference_was_detected = True
        change = new_content

    if difference_was_detected:
        with open(file_name, 'w') as file:
            file.write(new_content)
    return change


if __name__ == '__main__':
    # Download credentials.json from https://developers.google.com/gmail/api/quickstart/python
    web_page_content = get_web_page_content(url="https://www.nubert.de/stative-halter/38/",
                                            element_tag="div",
                                            element_tag_specifier={"class": "main-column"})

    detected_change = detect_change(file_name='content.html', new_content=web_page_content)
    if detected_change is not None:
        print("change detected - send email")
        gmail_service = get_gmail_service()
        email = create_gmail_email(sender='sender.email@gmail.com', to='recipient.email@gmail.com',
                                   subject='Nubert speaker stands were updated', message_text=detected_change)
        send_gmail_email(gmail_service, 'me', email)
    else:
        print("no change")
