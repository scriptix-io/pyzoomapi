import warnings
import platform
import json
import os

SSL_VERIFY = True

class ZoomAPI():
    protocol = 'https'
    server = 'api.zoommedia.ai'

    def __init__(self, token, connect_timeout=5.0, read_timeout=15.0):
        self._token = token
        self._connect_timeout = connect_timeout
        self._read_timeout = read_timeout

    @property
    def _timeout(self):
        return (self._connect_timeout, self._read_timeout)

    def new_session(self, *args, **kwargs):
        return(Session(*args, zoom_api=self, **kwargs))

    @property
    def token(self):
        return self._token

    @property
    def apibase(self):
        return '{protocol}://{server}/api/v2'.format(protocol=ZoomAPI.protocol, server=ZoomAPI.server)

    def __repr__(self):
        return '<ZoomAPI:%s>' % self.token

class Session():
    def __init__(self, language, callback_url = None, callback_method = None,
                    callback_format = None, callback_headers = None, punctuation = False, zoom_api = None, zoom_id = None):
        """ Initialize a new Speech to Text session """

        from requests import Session
        self._upload_success = False
        self._zoom_api = zoom_api

        if callback_method and callback_url:
            if callback_method and callback_method.lower() not in [ "put", "post" ]:
                raise ArgumentException("Only permitted callback methods are POST and PUT")

            if callback_url and not ( callback_url.lower().startswith('http://') or callback_url.lower().startswith('https://') ):
                raise ArgumentException("A valid callback URL should start with https://")

            if callback_format and callback_format.lower() not in [ "application/json", "text/vtt" ]:
                raise ArgumentException("Only permitted callback formats are application/json and text/vtt")

        elif (callback_method and not callback_url) or (callback_url and not callback_method):
            raise ArgumentException("Callback method and URL should both be set")


        self.request_session = Session()
        self.request_session.headers.update({
            'X-Zoom-S2T-Key': zoom_api.token,
            'User-Agent': 'ZoomAPI/PythonClient %s/%s' % (platform.system(), platform.python_version())
        })

        session_setup = {
            'language': language
        }

        if callback_url: session_setup['callback_url'] = callback_url
        if callback_method: session_setup['callback_method'] = callback_method
        if callback_format: session_setup['callback_format'] = callback_format
        if callback_headers: session_setup['callback_headers'] = callback_headers
        if punctuation: session_setup['punctuation'] = punctuation

        if not zoom_id:
            post_session = self.POST(self._zoom_api.apibase + '/speech-to-text/session/', json_data=session_setup)

            try:
                self._zoom_session = post_session.json()
            except ValueError:
                raise SessionException("Session error: NO JSON RESPONSE")

            if self._zoom_session.get('error'):
                raise SessionException("Session error: %s" % self._zoom_session.get('error_message', self._zoom_session.get('error', 'Unknown')))

            if not self._zoom_session.get('zoom_id'):
                raise SessionException("Session error: Did not receive a Zoom ID")

            if not self._zoom_session.get('language'):
                raise SessionException("Session error: Did not receive a language code")
        else:
            self._zoom_session = {
                "language": language,
                "sessionId": zoom_id,
                "zoom_id": zoom_id
            }
            self._upload_success = True

    def GET(self, url, accept='application/json'):
        from requests.exceptions import ConnectTimeout, ReadTimeout

        try:
            return self.request_session.get(
                url,
                verify=SSL_VERIFY,
                timeout=self._zoom_api._timeout,
                headers={
                    'Accept': accept
                })
        except ConnectTimeout:
            raise ApiTimeoutException("Unable to connect in time")
        except ReadTimeout:
            raise ApiTimeoutException("Unable to get API response in time, request may be running")

    def POST(self, url, json_data = None, files = None):
        from requests.exceptions import ConnectTimeout, ReadTimeout

        post_args = {}
        post_args['timeout'] = self._zoom_api._timeout

        if json_data: post_args['json'] = json_data
        if files: post_args['files'] = files

        try:
            return self.request_session.post(url, verify=SSL_VERIFY, **post_args)
        except ConnectTimeout:
            raise ApiTimeoutException("Unable to connect in time")
        except ReadTimeout:
            raise ApiTimeoutException("Unable to get API response in time, request may be running")

    def upload(self, filepath, custom_filename = None):
        """ Upload a file to the Zoom API """
        if self._upload_success == True:
            raise AlreadyUploadedException()

        try:
            if not os.path.isfile(filepath):
                raise FileNotFoundError()

            fp = open(filepath, 'rb')
        except FileNotFoundError:
            raise FileDoesNotExist("File to upload does not exist or is not a file")

        if not custom_filename:
            files = {'upload': open(filepath, 'rb')}
        else:
            files = {'upload': (custom_filename, open(filepath, 'rb'))}

        upload = self.POST(self.session_url, files=files)

        try:
            upload_json = upload.json()
        except ValueError:
            raise SessionException("Upload error: NO JSON RESPONSE [%s]" % upload.text)

        if upload_json.get('err'):
            raise SessionException("Upload error: %s" % upload_json.get('err'))

        if upload_json.get('error'):
            raise SessionException("Upload error: %s" % upload_json.get('error'))

        self._upload_success = True

    def get_status(self):
        """ Upload a file to the Zoom API """
        if self._upload_success != True:
            raise NoFileUploadedException()

        state = self.GET(self.session_url)
        try:
            state = state.json()
        except ValueError:
            raise SessionException("Session error: NO JSON RESPONSE")

        return state

    def is_done(self):
        return self.get_status().get('done') is True

    def get_transcript(self):
        status = self.get_status()

        if status.get('done') is not True:
            raise ServiceNotDone()

        if not status.get('results'):
            raise NoResultsReceived()

        return Transcript(status.get('results'))

    def get_subtitle(self, subtitle_type='text/vtt'):
        if self._upload_success != True:
            raise NoFileUploadedException()

        subtitle = self.GET(self.session_url, subtitle_type)
        return subtitle.text

    @property
    def session_url(self):
        return self._zoom_api.apibase + '/speech-to-text/session/' + self.session_id

    @property
    def session_id(self):
        warnings.warn("session_id is going to be deprecated, start using zoom_id", DeprecationWarning, stacklevel=2)
        return self.zoom_id

    @property
    def zoom_id(self):
        return self._zoom_session['zoom_id']

    @property
    def language(self):
        return self._zoom_session['language']

    def __repr__(self):
        return "<ZoomAPISession %s>" % self.session_id

class Transcript():
    def __init__(self, results):
        self._results = results

    def save(self, filename):
        with open(filename, 'wb') as fp:
            json.dump(self._results, fp)

    @classmethod
    def load(cls, filename):
        with open(filename, 'rb') as fp:
            return cls(json.load(fp))

    @property
    def fulltext(self):
        return " ".join([ result['text'] for result in self._results ])

    @property
    def raw_result(self):
        return self._results

    def make_timestamp(self, ts):
        # Convert from ms to seconds
        hours = ts / 3600000
        ts = ts % 3600000
        minutes = ts / 60000
        ts = ts % 60000
        seconds = ts/1000.0
        timestamp = "%02d:%02d:%05.2f" % (hours, minutes, seconds)
        return timestamp

    def pprint(self, width=80, color=True, speaker=True):
        def printline(line):
            newline = []
            for w in line:
                if color is False or w[1] == 1:
                    newline.append(w[0])
                elif w[1] == 2:
                    newline.append(green(w[0]))
                elif w[1] == 3:
                    newline.append(blue(w[0]))
                elif w[1] < 0.99:
                    newline.append(red(w[0]))
                else:
                    newline.append(yellow(w[0]))
            print(" ".join(newline))

        ## Find largest speaker name
        red    = lambda s: "\033[31m" + s + "\033[0m"
        green  = lambda s: "\033[32m" + s + "\033[0m"
        yellow = lambda s: "\033[33m" + s + "\033[0m"
        blue   = lambda s: "\033[34m" + s + "\033[0m"

        line = []
        _spkr = ''
        for result in self._results:
            _spkr = result['speaker']
            for word in result['result']:
                word, start, stop, acc = word

                if len(" ".join([ w[0] for w in line])) + len(word) + len(_spkr) > width:
                    printline(line)
                    line = []

                if not line:
                    line = [ ( self.make_timestamp(start), 2 ), ( "|", 1 ) ]
                if _spkr and speaker is True:
                    line.append(("<%s>" % _spkr, 3))
                    _spkr = ''

                line.append((word, acc))
        printline(line)

class ZoomApiException(Exception): pass
class ApiTimeoutException(ZoomApiException): pass
class ArgumentException(ZoomApiException): pass
class SessionException(ZoomApiException): pass
class AlreadyUploadedException(ZoomApiException): pass
class NoFileUploadedException(ZoomApiException): pass
class ServiceNotDone(ZoomApiException): pass
class NoResultsReceived(ZoomApiException): pass
class FileDoesNotExist(ZoomApiException): pass

__version__ = "0.5"
