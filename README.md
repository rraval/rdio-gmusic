Rdio to Google Music Exporter
=============================

A simple script to export an existing Rdio collection to Google Music All
Access. The script only adds to your Google Music library and keeps track of
which songs already exist, and so should be safe to run multiple times.

The current strategy is to lookup "Artist Album Title", falling back to
"Album Title", and finally "Title" for every song in your Rdio collection. This
strategy has a relatively high hit rate (~90% for my collection), but there are
quite a few false positives that have to be manually cleaned up.

Use the summary screen printed after every execution to ensure sanity and hunt
down the tracks that couldn't be found.

Usage
-----

```
# pip install rdio-gmusic
# rdio-gmusic RDIO_USERNAME GOOGLE_USERNAME
```
