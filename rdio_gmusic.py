from __future__ import unicode_literals

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
import itertools
import json
import os
import urllib
from collections import defaultdict

import click
import oauth2

from gmusicapi.clients import Mobileclient

# number of tracks to request from rdio at a time
RDIO_CHUNK_SIZE = 250

# oauth client identification
RDIO_KEY = '3nq3y49bhhbwexffd5fym3mz'
RDIO_SECRET = 'PdVBSRsXQv'

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

    def findTrack(self, rdio_track, keys=('artist', 'album', 'name',)):
        if not keys:
            return

        results = self.client.search_all_access(' '.join(rdio_track[k] for k in keys))['song_hits']
        if not results:
            return self.findTrack(rdio_track, keys[1:])

        # FIXME: is the best match always first?
        best_match = results[0]
        return best_match['track']

    def addTrack(self, google_track):
        self.client.add_aa_track(google_track['nid'])

class ChangeTracker(object):
    def __init__(self, tag):
        self.tag = tag
        self.items = defaultdict(list)
        self.item_count = 0

    def add(self, rdio_track, google_track):
        self.item_count += 1

        item = {'rdio': rdio_track['name']}
        if google_track:
            item['google'] = google_track['title']

        key = '{} [{}]'.format(rdio_track['album'], rdio_track['artist'])
        self.items[key].append(item)

    def summary(self, total):
        lines = ['']

        lines.append('----- {} {} ({:.2f}%) -----'.format(
            self.item_count,
            self.tag,
            (float(self.item_count) / total) * 100,
        ))

        lines.append('')

        for key, tracks in self.items.iteritems():
            lines.append('+ {}'.format(key))

            for track in tracks:
                lines.append('|-> {}'.format(track['rdio']))
                if 'google' in track:
                    lines.append('|   +=> {}'.format(track['google']))
                    lines.append('|')

            lines.append('')

        return lines

@click.command()
@click.argument('rdio_user')
@click.argument('google_user')
def main(rdio_user, google_user):
    click.echo('Create an App Specific Password to use with your Google Account')
    click.echo('See https://support.google.com/accounts/answer/185833')

    click.echo()
    google_password = click.prompt('{} Password'.format(google_user), hide_input=True)
    click.echo()

    rdio = Rdio(RDIO_KEY, RDIO_SECRET)
    gmusic = GMusic(google_user, google_password)

    existing_tracks = {}
    with click.progressbar(
        gmusic.genTracks(),
        label='Existing Google Music',
        show_pos=True
    ) as bar:
        for track in bar:
            if 'nid' in track:
                existing_tracks[track['nid']] = track

    skip = ChangeTracker('Skipped')
    added = ChangeTracker('Added')
    notfound = ChangeTracker('Not Found')

    with click.progressbar(
        rdio.genTracks(rdio_user),
        label='Rdio -> Google Music',
        show_pos=True
    ) as bar:
        for track in bar:
            match = gmusic.findTrack(track)
            if match is None:
                notfound.add(track, None)
            elif match['nid'] in existing_tracks:
                skip.add(track, match)
            else:
                gmusic.addTrack(match)
                added.add(track, match)

    total = sum((added.item_count, skip.item_count, notfound.item_count))
    click.echo_via_pager('\n'.join(itertools.chain(
        notfound.summary(total),
        added.summary(total),
        skip.summary(total),
    )))

if __name__ == '__main__':
    main()
