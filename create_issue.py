#!/usr/bin/env python
"""
Checks a Maildir folder for messages and creates new issues
in your gitea instance. Moves the mail to a Trash folder.
If attachments are found they are uploaded to the issue created.
Email Headers in use:

Subject:    Title of the issue
Assign:     (optional) Commaseperated list of users on 
            gitea instance which are assigned to the issue.

If multipart message the first usefull text/plain part is
the issue content. If plain email the payload is used.

Needs a config.ini, see config.ini.example
"""


from pathlib import Path
import configparser


config = configparser.ConfigParser()
config.read('config.ini')

token = config.get('general', 'token')
instance = config.get('general', 'instance')
user, repo = config.get('general', 'repo').split('/')
email_path = config.get('general', 'email_path')
email_inbox = config.get('general', 'email_inbox')
email_trash = config.get('general', 'email_trash')

inbox_folder = Path(email_path + email_inbox + '/new/')
trash_folder = Path(email_path + email_trash + '/cur/')

# quit if shit
if not inbox_folder.exists() and not trash_folder.exists():
    print(f'Folders {email_inbox} and {email_trash} dont exists')
    exit(1)


import requests
import email
import subprocess
import tempfile
tempfolder = Path(tempfile.mkdtemp())


class MailData:
    """
    Missusing a class as a replacement for dict dot notation and some ez typing hints...
    """
    def __init__(self):
        self.body: str = ''
        self.title: str = ''
        self.assignees: list = []
        self.attachments: list = []
        self.issue: None | int = None
        self.repo: str = repo
        self.user: str = user
        self.token: str = token
        self.instance: str = instance


def post_attachements(d: MailData):

    # baaad solution but requests wouldn't behave :*(
    def _post(a):
        response = subprocess.run(f"""
        curl -X 'POST' \
          'https://{d.instance}/api/v1/repos/{d.user}/{d.repo}/issues/{d.issue}/assets?name={a.get('name')}&token={d.token}' \
          -H 'accept: application/json' \
          -H 'Content-Type: multipart/form-data' \
          -F 'attachment=@{a.get('path')};type={a.get('content_type')}'
        """, shell=True, stdout=subprocess.DEVNULL)
        return response

    for a in d.attachments:
        try:
            _post(a)
            print(f'Attachment {a.get("name")} posted')
        except:
            print(f'failure: uploading attachment {a.get("name")}')
            continue


def post_issue(d: MailData):

    url = f'https://{d.instance}/api/v1/repos/{d.user}/{d.repo}/issues'
    headers = {'accept': 'application/json', 'Content-Type': 'application/json'}
    data = { 
        "title": d.title,
        "body": d.body,
        "assignees": d.assignees
    }
    params = { 'token': d.token }
    response = requests.post(url, headers=headers, json=data, params=params)
    return response


def get_attachments(mailpart, content_type: str, mail_data: MailData) -> dict:
    """
    Get attachments from mailpart, write to disk and attach to MailData.attachments object
    """

    allowed_content_types = ['image/png', 'image/jpeg']

    if content_type in allowed_content_types:
        path = Path(tempfolder / mailpart.get_filename())
        path.write_bytes(mailpart.get_payload(decode=True))
        attachment = {'path':path, 'content_type':content_type, 'name': mailpart.get_filename()}
        mail_data.attachments.append(attachment)


for file in inbox_folder.iterdir():

    # sanity
    if file.is_dir(): continue

    mail: email.message.EmailMessage = email.message_from_bytes(file.read_bytes(), _class=email.message.EmailMessage)

    # Get data from mail. In the future might also get an auth token, user and repo or even taget instance from it.

    mail_data = MailData()
    mail_data.title = mail.get('Subject')

    if mail.get('Assign', False):
        mail_data.assignees = [a.strip() for a in mail.get('Assign').split(',')]

    if mail.is_multipart():

        for part in mail.walk():

            content_type = part.get_content_type()
            get_attachments(part, content_type, mail_data)
            content_disposition = str(part.get('Content-Disposition'))
            if mail_data.body != '' and content_type == 'text/plain' and 'attachment' not in content_disposition:
                mail_data.body = part.get_payload(decode=True)
    else:
        mail_data.body = mail.get_payload(decode=True).decode('utf-8')


    try:
        response = post_issue(mail_data)
        if response.status_code == 201:
            print(f'Issue #{response.json().get("number")} created: {mail_data.title}')
            mail_data.issue = response.json().get('number')
    except:
        continue

    try:
        post_attachements(mail_data)
    except:
        continue

# because we are polite we clean up after ourselves
[f.unlink() for f in tempfolder.iterdir()]
