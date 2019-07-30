# pyzoomapi

Zoom Media Speech to Text API python implementation

## Installation
```sh

git clone https://github.com/zoom-media/pyzoomapi.git
cd pyzoomapi
./setup.py install

# or
pip install git+https://github.com/zoom-media/pyzoomapi
```

## Usage
```python

import pyzoomapi
from time import sleep

# Initialize Zoom Media PI
zoomapi = pyzoomapi.ZoomAPI('zoom-batch-token')

# Start new dutch transcript session
session = zoomapi.new_session(language='nl-nl')

# Upload file
session.upload('/tmp/news_broadcast.mp3')

# Poll for result
while True:
  if session.is_done():
    break
  sleep(1)

# Retrieve transcript
transcript = session.get_transcript()

# Print transcript to console
transcript.pprint()
```

## Examples

For examples see `examples` directory.
