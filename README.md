# WebsiteWatcherNotifierGmail

Fetch a certain part of a website and check if it changed - on change send an email using the GMail API

## Prerequisites

1. Get [GMail API credentials (`credentials.json`)](https://developers.google.com/gmail/api/quickstart/python) and place them into the repository directory
2. Specify which websites should be scraped with which options
   1. Either by providing a `configuration.json` file that contains this information (copy and update the example [`configuration.example.json`](configuration.example.json))
   2. Or by specifying it in the file [`main.py`](main.py)

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
