import asyncio
import os
import re
import shutil
from argparse import ArgumentParser
from base64 import b64encode
from collections import Counter
from os import chdir
from os.path import splitext
from subprocess import call
from tempfile import NamedTemporaryFile
from typing import List

import en_core_web_sm
import uvicorn
from imap_tools import MailBox, A
from loguru import logger
from tortoise import run_async, Tortoise

from trakario.config import config
from trakario.misc import run_uvicorn
from trakario.models import ApplicantDB


class PeopleFinder:
    def __init__(self):
        self.nlp = en_core_web_sm.load()
    def get_people(self, text: str) -> List[str]:
        doc = self.nlp(text)
        return [
            i.text for i in doc.ents if i.label_ == 'PERSON'
        ]


def normalize_name(name):
    return ' '.join(i.title() for i in re.findall(r'\w+', name))


def parse_email(finder: PeopleFinder, body):
    body = re.sub(r'\r\n', '\n', body)
    *_, body = re.split(r'-{3,}\s*[fF]orwarded\s+[mM]essage\s*-{3,}', body)
    *_, body = re.split(r'Begin forwarded message:', body)
    body = re.sub(r'^[> ]+', '', body, flags=re.MULTILINE)
    from_match = (list(re.finditer(
        r'^\*?From:\*?\s*(.*?)\s+<(\S+@\S+\.\S+)>', body, flags=re.MULTILINE
    )) or [''])[-1]

    if from_match:
        from_name_raw = from_match.group(1)
        from_name = from_name_raw
        from_name = re.sub(r'\(.*\)', '', from_name)
        if ',' in from_name:
            last, first = from_name.split(',')
            from_name = '{} {}'.format(first, last)
        from_name = normalize_name(from_name)
        prefix = "Hi, I'm {}. ".format(from_name)
    else:
        prefix = ''
    *_, body = re.split(r'\n(\*?(From|To|Date|Subject):\*?[^\n]*\n)+', body,
                        re.MULTILINE)
    body = body.encode('ascii', 'ignore').decode()
    body = re.sub(r'^\W+$', r'', body, re.MULTILINE)
    body = re.sub(r'\n\n+', r'\n\n', body).strip()
    people = finder.get_people(prefix + body)
    counts = Counter(map(normalize_name, people))
    name = counts.most_common(1)[0][0] if counts else from_name
    from_email = from_match.group(2).lower()
    github = re.search(r'github.com/[^\s/]+', body)
    if github:
        github = 'https://{}'.format(github.group(0))
    return name, from_email, github, body


async def convert_to_pdf(data: bytes, ext: str) -> bytes:
    logger.debug('Converting to pdf...')
    with NamedTemporaryFile(suffix=ext) as nf:
        with open(nf.name, 'wb') as f:
            f.write(data)
        proc = await asyncio.create_subprocess_shell(
            'libreoffice --headless --invisible --convert-to pdf "{}" --outdir /tmp'.format(
                nf.name
            ),
        )
        stdout, stderr = await proc.communicate()
        logger.debug('Conversion output: {} {}', stdout, stderr)
        out_file = nf.name[:-len(ext)] + '.pdf'
        with open(out_file, 'rb') as f:
            data = f.read()
        os.remove(out_file)
        return data


async def email_monitor(once=False):
    await Tortoise.init(
        db_url=config.db_url,
        modules={"models": ["trakario.models"]},
    )
    await Tortoise.generate_schemas()
    finder = PeopleFinder()
    logger.info('Monitoring mail...')
    while True:
        with MailBox(config.imap_server).login(
                config.imap_email, config.imap_password,
                initial_folder=config.imap_folder
        ) as mailbox:
            for message in mailbox.fetch(A(seen=False), mark_seen=False):
                logger.info('New email...')
                name, email, github, body = parse_email(finder, message.text)
                duplicates = await ApplicantDB.filter(email=email)
                if duplicates:
                    logger.info('Skipping duplicate for: {}', email)
                    continue
                logger.info("Applicant name: {}", name)
                logger.info("Applicant email: {}", email)
                logger.info("Applicant GitHub: {}", github)
                logger.info('Email text:\n{}', body)
                logger.info('Attachments: {}',
                            [i.filename for i in message.attachments])

                if message.attachments:
                    attachment = message.attachments[0]
                    logger.info('Content Type: {}', attachment.content_type)
                    resume_data = attachment.payload
                    _, ext = splitext(attachment.filename)
                    if ext.lower() != '.pdf':
                        logger.info('Converting...')
                        resume_data = await convert_to_pdf(resume_data, ext)
                else:
                    resume_data = ''
                applicant_db = await ApplicantDB.create(
                    name=name,
                    email=email,
                    attributes=dict(
                        githubUrl=github,
                        emailText=body,
                        resume=b64encode(resume_data).decode() if resume_data else '',
                        ratings=[],
                        stage='unprocessed'
                    )
                )
                logger.info('Applicant created.')
                logger.debug('Applicant object: {}', applicant_db)
                mailbox.seen(message.uid, True)
            if once:
                return
            logger.debug('Waiting 30 seconds...')
        await asyncio.sleep(30.0)


def main():
    parser = ArgumentParser(description='Automatic job applicant tracking system')
    sp = parser.add_subparsers(dest="action")
    sp.required = True
    p = sp.add_parser("mail-monitor")
    p.add_argument('--once', action='store_true', help='Only run once')
    sp.add_parser("init-db")
    sp.add_parser("drop-db")
    p = sp.add_parser("run")
    p.add_argument(
        "-p", "--port", help="Port to run on. Default: 7110", type=int, default=7110
    )
    args = parser.parse_args()
    if args.action == 'run':
        run_uvicorn(
            uvicorn.Config(
                "trakario.app:app",
                host="0.0.0.0",
                port=args.port,
                log_level=["info", "debug"][config.debug],
                reload=config.debug,
            )
        )
    elif args.action == 'mail-monitor':
        run_async(email_monitor(args.once))
    elif args.action == 'init-db':
        chdir('/')
        call(['sudo', '-u', 'postgres', shutil.which('createuser'), 'trakario'])
        call(['sudo', '-u', 'postgres', shutil.which('createdb'), 'trakario'])
        call([
            'sudo', '-u', 'postgres', shutil.which('psql'), '-c',
            'alter user trakario with encrypted password \'trakario\''
        ])
        print('Initialized DB.')
    elif args.action == 'drop-db':
        chdir('/')
        call([
            'sudo', '-u', 'postgres', shutil.which('psql'), '-c',
            'DROP DATABASE trakario'
        ])
        call([
            'sudo', '-u', 'postgres', shutil.which('psql'), '-c',
            'DROP USER trakario'
        ])
        print('Dropped DB.')
    else:
        raise ValueError


if __name__ == '__main__':
    main()
