#!/usr/bin/env python3

from typing import Optional, List, Tuple, Dict

import sys
import requests
import base64
from bs4 import BeautifulSoup, ResultSet, Comment
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.mime.text import MIMEText
from lxml.html.diff import htmldiff
import json
from dataclasses import dataclass
import time
import datetime

# If modifying these scopes, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

Attribute = str
AttributeValueWhitelist = List[str]
AttributeInfo = Tuple[Attribute, AttributeValueWhitelist]
Tag = str
TagInfo = Tuple[Tag, List[AttributeInfo]]
TagNewName = str
TagRenameInfo = Tuple[Tag, TagNewName]


@dataclass
class Configuration:
    add_website_link: Optional[bool]
    whole_website: Optional[bool]
    """Check the whole website"""
    element_tag: str
    element_tag_specifier: Dict[str, str]
    fix_links_with_base_url: Optional[str]
    tags_to_drop: Optional[List[TagInfo]]
    tags_to_rename: Optional[List[TagRenameInfo]]
    url: str
    recipients: List[str]
    sender: str
    title: str
    name: str


def get_web_page_content(
    url: str,
    element_tag: str,
    element_tag_specifier: dict,
    tags_to_drop: Optional[List[TagInfo]] = None,
    tags_to_rename: Optional[List[TagInfo]] = None,
    attributes_to_drop: Optional[List[str]] = None,
    fix_links_with_base_url: Optional[str] = None,
    whole_website: Optional[bool] = None,
    add_website_link: Optional[bool] = None,
    debug=False,
) -> str:
    """Scrape web page for a certain part.

    Args:
        url: Web page address.
        element_tag: HTML element tag that should be looked for.
        element_tag_specifier: Specifier for certain id ({id: '...'}) or class ({class: '...'}).
        tags_to_drop: Optional list of HTML tags that should be dropped from the web page output.
                      Optionally a whitelist for certain attributes with optional a whitelist of values can be added)
        tags_to_rename: Optional list of HTML tags that should be renamed from the web page output.
                        Optionally a whitelist for certain attributes with optional a whitelist of values can be added)
        attributes_to_drop: Optional list of HTML tag attributes that should be dropped from the web page output.
        fix_links_with_base_url: Optional base url correction for links.
        whole_website: Scrap the whole website without considering a special element tag.
        add_website_link: Add a link to the scraped website.
        debug: Enable debug comments.

    Returns:
        A string that contains a certain part of the website while missing unnecessary style or other information.
    """
    if attributes_to_drop is None:
        attributes_to_drop = ["class", "id", "name", "style", "align"]
    if tags_to_drop is None:
        tags_to_drop = [("script", []), ("form", [])]

    page = requests.get(url)

    # Validate that page is valid HTML (no xml errors) to prevent crashes/loops
    # TODO

    soup = BeautifulSoup(page.content, "html.parser")
    # Extract content that should be checked
    found_elements = soup.findAll(element_tag, element_tag_specifier)
    if len(found_elements) != 1:
        raise Exception(
            "{}s (with {}) are either not found or too many ({})!".format(
                element_tag, element_tag_specifier, len(found_elements)
            )
        )
    element = soup if whole_website else found_elements[0]

    if debug:
        with open("page.html", "w") as file:
            file.write(str(page.content))
            print(f"Write scraped website data to '{file.name}'")

        with open("page_found_elements.json", "w") as file:
            file.write(str(found_elements))
            print(f"Write found elements data to '{file.name}'")

        with open("page_element.html", "w") as file:
            file.write(str(element.prettify()))
            print(f"Write scraped website data element to '{file.name}'")

    # Remove specified tags
    helper_remove_tags(element, tags_to_drop, debug=debug)
    # Rename specified tags
    helper_rename_tags(element, tags_to_rename, debug=debug)
    # Remove comments
    for html_element in element(text=lambda text: isinstance(text, Comment)):
        html_element.extract()
    # Remove specified attributes from tags
    helper_remove_attributes(element, attributes_to_drop, fix_links_with_base_url, debug=debug)

    if add_website_link:
        br_tag_1 = soup.new_tag("br")
        soup.insert(len(soup.contents), br_tag_1)
        br_tag_2 = soup.new_tag("br")
        soup.insert(len(soup.contents), br_tag_2)
        new_tag = soup.new_tag("a", href=url)
        new_tag.string = "Link to original website"
        soup.insert(len(soup.contents), new_tag)

    if debug:
        with open("page_element_updated.html", "w") as file:
            file.write(str(element.prettify()))
            print(f"Write updated website data for email to '{file.name}'")

    return str(element.prettify())


def helper_remove_tags(
    element: ResultSet, tags_to_drop: Optional[List[TagInfo]] = None, debug=False
):
    for tag_to_drop in tags_to_drop:
        if debug:
            print(f"Drop tag '{tag_to_drop}'")
        for s in element.select(tag_to_drop[0]):
            decomposed = False
            if len(tag_to_drop[1]) > 0:
                for attribute in tag_to_drop[1]:
                    if not s.has_attr(attribute[0]):
                        decomposed = True
                        s.decompose()
                    elif len(attribute[1]) == 0 or s[attribute[0]] not in attribute[1]:
                        decomposed = True
                        s.decompose()
            else:
                decomposed = True
                s.decompose()
            if debug and decomposed:
                print(f"Drop element '{s}' in element '{element}'")
            if not decomposed and len(s.select(tag_to_drop[0])) != 0:
                helper_remove_tags(s, tags_to_drop)


def helper_remove_attributes(
    element: ResultSet,
    attributes_to_drop: Optional[List[str]],
    fix_links_with_base_url: Optional[str],
    debug=False,
):
    for tag in element():
        if debug:
            print(f"Current tag of element: '{tag}'")
        for attribute in attributes_to_drop:
            if debug:
                print(f"Remove attribute '{attribute}'")
            if tag.has_attr(attribute):
                if debug:
                    print(f"Remove attribute '{attribute}' from '{tag}'")
                del tag[attribute]
        if fix_links_with_base_url is not None:
            if debug:
                print(f"Fix link with base url '{fix_links_with_base_url}'")
            if (
                tag.has_attr("href")
                and not tag["href"].startswith(fix_links_with_base_url)
                and not tag["href"].startswith("https://")
            ):
                if debug:
                    print(f"Fix link with base url '{fix_links_with_base_url}' from {tag['href']})")
                tag["href"] = fix_links_with_base_url + tag["href"]
        if len(tag()) != 0:
            helper_remove_attributes(tag, attributes_to_drop, fix_links_with_base_url, debug=debug)


def helper_rename_tags(
    element: ResultSet, tags_to_rename: Optional[List[TagRenameInfo]] = None, debug=False
):
    for tag_to_rename in tags_to_rename:
        for tag in element.find_all(tag_to_rename[0]):
            tag.name = tag_to_rename[1]


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
    message = MIMEText(message_text, "html")
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject
    return {"raw": base64.urlsafe_b64encode(message.as_string().encode()).decode()}


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
        sent_gmail_message_info = (
            service.users().messages().send(userId=user_id, body=message).execute()
        )
        return sent_gmail_message_info
    except Exception as gmail_exception:
        raise gmail_exception


def get_gmail_service(token_pickle_file="token.pickle", credentials_file="credentials.json"):
    """Get the GMail API service."""
    credentials = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_pickle_file):
        with open(token_pickle_file, "rb") as token:
            credentials = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            credentials = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_pickle_file, "wb") as token:
            pickle.dump(credentials, token)

    return build("gmail", "v1", credentials=credentials)


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
        with open(file_name, "r") as file:
            old_content = file.read()
            if old_content != new_content:
                difference_was_detected = True
                change = htmldiff(old_content, new_content)
    else:
        difference_was_detected = True
        change = new_content

    if difference_was_detected:
        with open(file_name, "w") as file:
            file.write(new_content)
    return change


def load_configuration(config_file_name: str, debug=False) -> List[Configuration]:
    configurations = []
    with open(config_file_name, "r") as file:
        data = json.loads(file.read().replace("\n", ""))
        for job in data["jobs"]:
            tags_to_drop = []
            if "tags_to_drop" in job:
                for tag_to_drop in job["tags_to_drop"]:
                    attribute_whitelist = []
                    for attribute_whitelist_element in tag_to_drop[
                        "attribute_whitelist"
                    ]:
                        attribute_whitelist.append(
                            (
                                attribute_whitelist_element["attribute"],
                                attribute_whitelist_element[
                                    "attribute_value_whitelist"
                                ],
                            )
                        )
                    tags_to_drop.append(
                        (tag_to_drop["tag_to_drop"], attribute_whitelist)
                    )
            tags_to_rename = []
            if "tags_to_rename" in job:
                for tag_to_rename in job["tags_to_rename"]:
                    tags_to_rename.append(
                        (tag_to_rename["tag_to_rename"], tag_to_rename["new_tag_name"])
                    )
            configurations.append(
                Configuration(
                    add_website_link=job["add_website_link"]
                    if "add_website_link" in job
                    else False,
                    whole_website=job["whole_website"]
                    if "whole_website" in job
                    else False,
                    element_tag=job["element_tag"],
                    element_tag_specifier=job["element_tag_specifier"],
                    fix_links_with_base_url=job["fix_links_with_base_url"],
                    tags_to_drop=tags_to_drop,
                    tags_to_rename=tags_to_rename,
                    url=job["url"],
                    recipients=job["recipients"],
                    sender=data["sender"],
                    title=job["title"],
                    name=job["name"],
                )
            )
    return configurations


def current_timestamp() -> str:
    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    return st


if __name__ == "__main__":
    # Global args
    global_debug = False

    # Check for command line arguments
    for arg in sys.argv:
        if arg == "--debug":
            global_debug = True
            print("Debugging was activated")

        # Download credentials.json from https://developers.google.com/gmail/api/quickstart/python
    for configuration in load_configuration(config_file_name="configuration.json", debug=global_debug):
        try:
            web_page_content = get_web_page_content(
                url=configuration.url,
                element_tag=configuration.element_tag,
                element_tag_specifier=configuration.element_tag_specifier,
                fix_links_with_base_url=configuration.fix_links_with_base_url,
                tags_to_drop=configuration.tags_to_drop,
                tags_to_rename=configuration.tags_to_rename,
                whole_website=configuration.whole_website,
                add_website_link=configuration.add_website_link,
                debug=global_debug,
            )
        except Exception as e:
            print(
                f"> an error occurred during parsing the website: {configuration.name} ({configuration.url})\n{str(e)}"
            )
            # Skip this configuration but still try the others
            continue

        detected_change = detect_change(
            file_name=f"content_{configuration.name}.html", new_content=web_page_content
        )
        if detected_change is not None:
            print(f"[{current_timestamp()}] change detected: {configuration.name}")
            gmail_service = get_gmail_service()
            for recipient in configuration.recipients:
                email = create_gmail_email(
                    sender=configuration.sender,
                    to=recipient,
                    subject=configuration.title,
                    message_text=detected_change,
                )
                try:
                    sent_message_info = send_gmail_email(gmail_service, "me", email)
                    print(
                        f"> sent email: {configuration.name} ({sent_message_info['id']}|{recipient})"
                    )
                except Exception as e:
                    print(
                        f"> an error occurred during sending the email: {configuration.name} ({recipient})\n{str(e)}"
                    )
        else:
            print(f"[{current_timestamp()}] no change: {configuration.name}")
