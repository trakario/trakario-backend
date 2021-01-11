# Trakario Backend

*Backend for Trakario, an automatic job applicant tracking system*

This is the backend for [Trakario](https://github.com/trakario/trakario-frontend).

## Setup

This is a standard Python package and can be set up with:

```bash
./setup.sh
```

In addition, you must install the following dependencies:

 - `libreoffice` (for docx to pdf conversion)
 - `postgresql` (for the database)

### Setup Database

You can setup the database with `trakario init-db`:

```bash
source .venv/bin/activate
trakario init-db
```

**Note:** If you've already set up the database and would like to reset it, use `trakario drop-db`.

### Configuring Environment

After running `setup.sh`, edit the variables in your `.env` files as follows:

 - Add your email credentials (for instance, a gmail account)
   - Set `imap_folder` to the folder it will process. It will delete emails from this folder as it processes them. If you are using gmail, you can set up a filter to forward certain emails to a folder.
 - Set your frontend url. When running locally, this will be `http://localhost:3000`
 - Set your `auth_token` to a new random value using the command shown in its comment in `.env`. **Note:** You will use this token the first time you launch the frontend.

## Running

First, source the virtual environment created under `.venv`:

```bash
source .venv/bin/activate
```

Now, to run the backend, there are two services that need to be started:

 - `trakario monitor-mail`: Monitors incoming emails and inserts them into the database
 - `trakario run`: Starts the backend using `uvicorn`
