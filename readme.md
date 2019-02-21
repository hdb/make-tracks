# make-tracks

**make-tracks** is a Python script for downloading full albums from Youtube. It uses [youtube-dl](https://github.com/rg3/youtube-dl) and [ffmpeg] to get an mp3 from the web, and the [Discogs API](https://github.com/discogs/discogs_client) to figure out how to dissect and tag it. The goal is to make Youtube's vast music library accessible in more listening formats and to make it easier to move your music consumption away from online streaming platforms. 

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
  -k, --keep            keep single audio file after processing is completed
  -v, --version         show program's version number and exit

```


## Setup

Add your Discogs API user-token and default music library directory to `private.py`

## Contributing

Please report issues or make a pull request if you encounter something not working. There is a pretty wide amount of variation in Discogs data formatting so there are bound to be albums which throw the script off. 

## License

MIT