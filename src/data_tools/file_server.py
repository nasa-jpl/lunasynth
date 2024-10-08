#  Copyright (c) 2024. Jet Propulsion Laboratory. All rights reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

# Use this server to serve locally files for the web apps
# Usage: python file_server.py --port 5006 --directory /path/to/directory

import argparse
import http.server
import socketserver


class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serve files over HTTP")
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to serve on. Default is 8000.",
    )
    parser.add_argument(
        "--directory",
        type=str,
        default=".",
        help="Directory to serve. Default is the current directory.",
    )
    args = parser.parse_args()

    PORT = args.port
    DIRECTORY = args.directory

    with socketserver.TCPServer(("", PORT), MyHttpRequestHandler) as httpd:
        print(f"Serving {DIRECTORY} at port {PORT}")
        httpd.serve_forever()
