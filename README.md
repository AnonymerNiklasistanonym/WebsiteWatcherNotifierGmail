# WebsiteWatcherNotifierGmail

Fetch a certain part of a website and check if it changed - on change send an email using the GMail API

## Prerequisites

- Get [GMail API credentials (`credentials.json`)](https://developers.google.com/gmail/api/quickstart/python) and place them into the repository directory
- Specify in the file [`main.py`](main.py) what
  - url and which element of the site should be fetched
  - who the recipient/content/subject of the email on a detected change should be

## Run

- Create ron job by running:

  ```sh
  crontab -e
  ```

  Add the following line to the file:

  ```text
  0 */5 * * * cd Path/from/home/directory/WebsiteWatcherNotifierGmail && ./run.sh >> log.log
  ```

  (This will run the job [all 5 hours at minute 0](https://crontab.guru/#0_*/5_*_*_*))
- Run it via command line with:

  ```sh
  # Easy and no global package pollution
  ./run.sh
  # Normal way
  pip3 install -r requirements.txt
  python3 -m main
  ```
