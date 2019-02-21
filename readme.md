# make-tracks

**make-tracks** is a Python script for downloading full albums from Youtube. It uses [youtube-dl](https://github.com/rg3/youtube-dl) and [ffmpeg](https://ffmpeg.org/) to get an mp3 from the web, the [Discogs API](https://github.com/discogs/discogs_client) to figure out how to dissect and organize it, and [Mutagen](https://mutagen.readthedocs.io/en/latest/) to tag the tracks. The goal is to make Youtube's vast music library accessible in more listening formats and to make it easier to move your music consumption away from online streaming platforms. 

## Usage

```
usage: make-tracks [-h] [-u ] [-s [[...]]] [-d ] [-dd] [-i] [-k] [-v]

download audio from youtube and separate into ID3-tagged tracks using data
from discogs

optional arguments:
  -h, --help            show this help message and exit
  -u [], --url []       the url of the video to download
  -s [ [ ...]], --search [ [ ...]]
                        search instead of url input. OR if -dd is selected,
                        search discogs catalog and bypass youtube altogether.
  -d [], --directory []
                        specify directory to place new music in
  -dd, --dontdownload   don't download video. only search title on discogs.
  -i, --interactive     interactively select youtube/discogs search results.
  -k, --keep            keep single audio file after processing is completed
  -v, --version         show program's version number and exit


```


## Setup

Install required python packages: `pip install -r /path/to/make-tracks/requirements.txt`

You need to have a Discogs account in order to get a Discogs API token. You can generate or access your user token [here](https://www.discogs.com/settings/developers).

Add your Discogs API user-token and your music library directory to a file `private.py`:

```
cd /path/to/make-tracks/
touch private.py
echo "token='TOKEN'" > private.py
echo "directory='/path/to/music/lib/'" >> private.py
echo "private.py" >> .gitignore
```

## Contributing

Please report issues or make a pull request if you encounter something not working and which is unrelated to youtube-dl. There is pretty wide variation in Discogs data formatting so there are bound to be albums which throw errors. 

## License

MIT