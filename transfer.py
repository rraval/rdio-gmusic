# FIXME: monkey patch the track adder to not throw an exception on missing keys
# to test, try adding Tp3e52picsj55ozzmjtxwb5xpwa

import gmusicapi.protocol
@staticmethod
def build_track_add(store_track_info):
    import copy

    track_dict = copy.deepcopy(store_track_info)
    for key in ('kind', 'trackAvailableForPurchase',
        'albumAvailableForPurchase', 'albumArtRef',
        'artistId',
    ):
        if key in track_dict:
            del track_dict[key]

    for key, default in {
        'playCount': 0,
        'rating': '0',
        'genre': '',
        'lastModifiedTimestamp': '0',
        'deleted': False,
        'beatsPerMinute': -1,
        'composer': '',
        'creationTimestamp': '-1',
        'totalDiscCount': 0,
    }.items():
        track_dict.setdefault(key, default)
    # TODO unsure about this
    track_dict['trackType'] = 8
    return {'create': track_dict}

gmusicapi.protocol.mobileclient.BatchMutateTracks.build_track_add = build_track_add

# non fugly code starts here
import os
import urllib
import json

import oauth2
from click import progressbar

from gmusicapi.clients import Mobileclient

# minimum `navigational_confidence` to consider a song to be a match
CONFIDENCE_THRESHOLD = 5

# number of tracks to request from rdio at a time
RDIO_CHUNK_SIZE = 250

class Rdio(object):
    def __init__(self, key, secret):
        self.client = oauth2.Client(oauth2.Consumer(key, secret))

    def request(self, req):
        response = self.client.request(
            'http://api.rdio.com/1/',
            'POST',
            urllib.urlencode(req)
        )

        return json.loads(response[1])['result']

    def genTracks(self, user):
        user = self.request({
            'method': 'findUser',
            'vanityName': user,
        })

        offset = 0
        while True:
            tracks = self.request({
                'method': 'getTracksInCollection',
                'user': user['key'],
                'count': RDIO_CHUNK_SIZE,
                'start': offset,
            })

            if not tracks:
                break

            # no yield from :(
            for t in tracks:
                yield t

            offset += len(tracks)

class GMusic(object):
    def __init__(self, user, password):
        self.client = Mobileclient()
        self.client.login(user, password)

    def genTracks(self):
        for chunk in self.client.get_all_songs(incremental=True):
            for track in chunk:
                yield track

    def findTrack(self, rdio_track):
        results = self.client.search_all_access(' '.join((
            rdio_track['artist'],
            rdio_track['album'],
            rdio_track['name'],
        )))['song_hits']

        if not results:
            return None

        # FIXME: is the best match always first?
        best_match = results[0]

        if best_match.get('navigational_confidence', 0) > CONFIDENCE_THRESHOLD:
            return best_match['track']
        else:
            return None

    def addTrack(self, google_track):
        self.client.add_aa_track(google_track['nid'])

if __name__ == '__main__':
    rdio = Rdio(os.getenv('RDIO_KEY'), os.getenv('RDIO_SECRET'))
    rdio_user = 'rraval'
    gmusic = GMusic(os.getenv('GOOGLE_USER'), os.getenv('GOOGLE_PASSWORD'))

    existing_tracks = set()
    with progressbar(gmusic.genTracks(), label='Existing Google Music', show_pos=True) as bar:
        for track in bar:
            if 'nid' in track:
                existing_tracks.add(track['nid'])

    skip = added = notfound = 0
    with progressbar(rdio.genTracks(rdio_user), label='Rdio -> Google Music', show_pos=True) as bar:
        for track in bar:
            match = gmusic.findTrack(track)
            if match is None:
                notfound += 1
            elif match['nid'] in existing_tracks:
                skip += 1
            else:
                gmusic.addTrack(match)
                added += 1

    total = sum((added, skip, notfound))
    print('{} Added ({:.2f}%)'.format(added, (float(added) / total) * 100))
    print('{} Skipped ({:.2f}%)'.format(skip, (float(skip) / total) * 100))
    print('{} Not Found ({:.2f}%)'.format(notfound, (float(notfound) / total) * 100))
