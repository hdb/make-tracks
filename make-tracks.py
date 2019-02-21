#!/usr/bin/python3

import discogs_client
import argparse
import youtube_dl
import re
import string
import sys
import os
from ffmpy import FFmpeg
import mutagen.id3
import urllib.request
import time

import private

parser = argparse.ArgumentParser(
    description='download audio from youtube and separate into ID3-tagged tracks using data from discogs',
    prog='make-tracks',
    )

parser.add_argument('-u', '--url', nargs='?', help='the url of the video to download', metavar="")
parser.add_argument('-s', '--search', nargs='*', help='search instead of url input. OR if -dd is selected, search discogs catalog and bypass youtube altogether.', metavar="")
parser.add_argument('-d', '--directory', nargs='?', help='specify directory to place new music in', metavar="")
parser.add_argument('-dd', '--dontdownload', action='store_true', help="don't download video. only search title on discogs.")
parser.add_argument('-i', '--interactive', action='store_true', help="interactively select youtube/discogs search results.") # in progress
parser.add_argument('-k', '--keep', action='store_true', help='keep single audio file after processing is completed')
parser.add_argument('-v', '--version', action='version', version='%(prog)s 0.1')

args = parser.parse_args()

if args.url is None and args.search is None:
    print("need URL or search term. exiting.")
    sys.exit()

client = discogs_client.Client('TrackTimesFinder/0.1', user_token=private.token)


class MyLogger(object):
    def debug(self, msg):
        pass
    def warning(self, msg):
        pass
    def error(self, msg):
        print(msg)

def my_hook(d):
    if d['status'] == 'finished':
        print('Done downloading, now converting ...')
    if d['status'] == 'downloading':
        print(d['filename'], d['_percent_str'], d['_eta_str'], '\r', end='')



# raw_input returns the empty string for "enter"
yes = {'yes','y', 'ye', ''}
no = {'no','n'}

def getInput(string):
    print('Do you want ' + string + '? (y/n/-...)')
    choice = input().lower()
    if choice in yes:
       return [True, string]
    elif choice in no:
       return [False, string]
    elif choice.startswith('-'):
        return [True, string.replace(choice[1:],'')]
    else:
       sys.stdout.write("Please respond with 'yes' or 'no'")

def get_sec(time_str):
    if time_str.count(':') is 2:
        h, m, s = time_str.split(':')
        return int(h) * 3600 + int(m) * 60 + int(s)
    elif time_str.count(':') is 1:
        m, s = time_str.split(':')
        return int(m) * 60 + int(s)
    else:
        print("Duration [" + time_str + "] is not in (hh:)mm:ss format. Cannot parse track times. Exiting.")
        sys.exit()
    

def convertTrackTimeToCumulative(raw):
    cumulative = []
    cumulative.append(0)
    for index, tt in enumerate(raw[:-1]):
        cumulative.append(cumulative[index]+get_sec(raw[index]))
    return cumulative

# download videos using youtube-dl
def getTitle(u,i):  
    meta_opts = {'extract_flat': True, 'quiet': True}
    print('reading url...')
    vidlength=0
    with youtube_dl.YoutubeDL(meta_opts) as ydl:
        meta = ydl.extract_info(u, download=False)

    try: # recursively catch searches / playlists...
        cond = True
        index = 0

        while True:
            yt_title=((meta['entries'][0]['title']))
            u = 'https://www.youtube.com/watch?v='+((meta['entries'][index]['url']))
            recurse = getTitle(u, i)
            if recurse is not None: return recurse
            index = index + 1

    except:
        # do nothing
        print()
    yt_title = meta['title'].lower().replace('full album','')
    yt_title = re.sub('[^A-Za-z0-9 À-ž]+', '', yt_title) # exclude punctuation, but include non-English and accented letters
    
    if i:
        inp = getInput(yt_title)
        if inp[0]:
            return [inp[1], u, vidlength]
        else:
            return None

    return [yt_title, u, vidlength]

def dl_audio(u, path):
    out = path + 'yt.mp3'
    if not os.path.isfile(out):
        #add audio extractor
        ydl_opts = {
            'logger': MyLogger(),
            'progress_hooks': [my_hook],
            'outtmpl': path + 'yt.%(ext)s',
            'ignoreerrors': True,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',    
                }],
            }

        print('starting download...')
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([u])
    else:
        print("not downloading. " + out + " is already a file...")
        print()
    return out

def dl_cover(u, path):
    out = path + 'cover.jpg'
    urllib.request.urlretrieve(u, out)
    return out 

def getData(discogs_search_str, interactive):
    
    results = client.search(discogs_search_str, type='release')

    found = False
    hits = len(results)
    if hits is 0:
        print('searched for '+ discogs_search_str)
        print('album not found. exiting...')
        sys.exit()
    elif hits is 1 or not interactive:
        print('searched for '+ discogs_search_str)
        print('found '+ str(hits) +' album(s)...')
        album = results[0]
        print('using album: ' + album.title)
        print("https://www.discogs.com" + album.url)

    else:
        print('searched for '+ discogs_search_str)

        result_num = 0
        while not found:
            album = results[result_num]
            found = getInput(album.title)[0]
            if not found: result_num = result_num + 1

    artists_list = []
    for a in album.artists:
        artists_list.append(re.sub(' \([0-9]\)$','',a.name)) # remove numbers used to distinguish artists on discogs
    artist=", ".join(artists_list)

    discogs_track_list = album.tracklist
    raw_times = []
    track_titles = []

    # some releases don't have track time durations, keep checking to identify one that does
    if len(discogs_track_list[0].duration) is 0:
        print("no times listed in this release... trying another...")
        no_time = True
        for r in album.master.versions:
            if len(r.tracklist[0].duration) is not 0:
                discogs_track_list = r.tracklist
                print("found new tracklist..." + str(r))
                no_time = False
                break
        if no_time:
            print("no releases have track duration... exiting.")
            sys.exit()

    for i, track in enumerate(discogs_track_list):

        # remove multi-track movements that register as tracks,
        if len(track.position) is not 0: 

            # keep titles from single tracks that are composed of two pieces from different composers, but don't add a second (blank) duration entry
            if not bool(re.search('^.*?[^B-Zb-z]$', track.position)):
                print(track.position)
                track_titles[-1] = track_titles [-1] + '/' + discogs_track_list[i].title
            
            else:
                raw_times.append(discogs_track_list[i].duration)
                track_titles.append(discogs_track_list[i].title)

    track_times = convertTrackTimeToCumulative(raw_times)

    master = False
   
    try:
        image = album.master.images[0]['uri'] # master release tends to have more consistent image quality, when it exists
        master = True
    except:
        image = album.images[0]['uri']
    #label = album.labels
    if master:
        if len(album.master.versions) < 10:
            first_release = 9999
            for r in album.master.versions:
                time.sleep(.5) # if there are many versions, can throw 'discogs_client.exceptions.HTTPError: 429: You are making requests too quickly.'
                if r.year < first_release and r.year is not 0:
                    first_release = r.year
                    label_list = r.labels
        else:
            first_release = album.master.main_release.year
            label_list = album.master.main_release.labels

    else:
        label_list = album.labels
        first_release = album.year

    # concatenate labels into string if multiple are given
    if len(label_list) is 1:
        label = label_list[0].name
    else:
        label_name_list = []
        for l in label_list:
            label_name_list.append(l.name)
        label = ", ".join(label_name_list)

    return([album.title,artist,first_release,track_titles,track_times, image, label]) # structured data for directory path and metadata tagging

def setDLPath(directory, data):
    path = directory + data[1] + '/' + data[0] + ' (' + str(data[2]) + ')/'
    return path


def splitTracks(file, path, tracks, times):
    trackpaths = []
    for n, track in enumerate(tracks):
        tracknum = "{0:0=2d}".format(n+1) # format as 01, 02... 09, 10, 11, ... etc.
        outputtrack = path+tracknum+'-'+track+'.mp3'
        if not os.path.isfile(outputtrack): # if track already exists, skip. can be helpful for debugging or if correcting previous incorrect metadata
            if n is len(tracks)-1: # last track don't include 'trim' argument
                ff = FFmpeg(
                    inputs = {file: None},
                    outputs = {outputtrack: '-ss '+ str(times[n]) +' -c copy -hide_banner -loglevel panic'} # ffmpeg's "quiet mode"
                )
            else:
                ff = FFmpeg(
                    inputs = {file: None},
                    outputs = {outputtrack: '-ss '+ str(times[n]) +' -to '+ str(times[n+1]) +' -c copy -hide_banner -loglevel panic'}
                )
            ff.run()
        else:
            print(outputtrack+' is already a file.')
        trackpaths.append(outputtrack)
    return trackpaths


def setMetadata (data, filelist, image):

    for i, f in enumerate(filelist):
        m = mutagen.id3.ID3(f)
        m.add(mutagen.id3.TIT2(encoding=3, text=data[3][i])) # track title
        m.add(mutagen.id3.TALB(encoding=3, text=data[0])) # album title
        m.add(mutagen.id3.TPE1(encoding=3, text=data[1])) # artist
        m.add(mutagen.id3.TDRC(encoding=3, text=str(data[2]))) # year
        m.add(mutagen.id3.TRCK(encoding=3, text=str(i+1))) # track number
        m.add(mutagen.id3.TPUB(encoding=3, text=data[6])) # record label
        m.add(mutagen.id3.APIC(encoding=3, mime = 'image/jpeg', type=3, desc=u'Cover', data=open(image, 'rb').read())) # embed album art
        m.save()

def removeVideo(path):
    print("deleting " + path + "...")
    os.remove(path)



# --- MAIN ---

if args.directory is not None:
    directory = args.directory
elif private.directory is not None:
    directory = private.directory # default directory, USER, yes you, you must set this in `private.py`
elif not args.dontdownload:
    print("no music library directory specified. either specify a directory with -d or set default in private.py")
    sys.exit()
else:
    directory = None

if not directory.endswith('/'):
    directory = directory + '/'

if args.search is not None: # using search and not url
    search_str = " ".join(args.search)

    if args.dontdownload: # if searching and not downloading video, pass search directly to discogs and print data
        data = getData(search_str, args.interactive)
        print("data from discogs...")
        print(data)


    else:
        yt_search = 'https://www.youtube.com/results?search_query=' + re.sub(' ','+', search_str + ' full album') # yt search url

        youtube_info = getTitle(yt_search, args.interactive) # fetch youtube metadata first so that we can use artist / album info to determine path to download to
        yt_title = youtube_info[0]
        yt_url = youtube_info[1]

        data = getData(yt_title, args.interactive)
        print("data from discogs...")
        print(data)

        dlpath = setDLPath(directory, data)

        bigfile = dl_audio(yt_url,dlpath) # download mp3

        filelist = splitTracks(bigfile, dlpath, data[3], data[4])

        image = dl_cover(data[5],dlpath)

        setMetadata(data, filelist, image)

        if not args.keep:
            removeVideo(bigfile)

else: # use url and not search
    yt_url = args.url
    youtube_info = getTitle(yt_url, False)
    yt_title = youtube_info[0]

    data = getData(yt_title, args.interactive)
    print("data from discogs...")
    print(data)

    if not args.dontdownload:
        dlpath = setDLPath(directory, data)

        bigfile = dl_audio(yt_url,dlpath)

        filelist = splitTracks(bigfile, dlpath, data[3], data[4])

        image = dl_cover(data[5],dlpath)

        setMetadata(data, filelist, image)

        if not args.keep:
            removeVideo(bigfile)


