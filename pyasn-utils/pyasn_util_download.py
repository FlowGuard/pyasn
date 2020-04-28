#!/usr/bin/env python3

# Copyright (c) 2009-2017 Hadi Asghari
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Script to download the latest routeview bgpdata

from __future__ import print_function, division
from html.parser import HTMLParser
import re
from argparse import ArgumentParser

try:
    from pyasn import __version__
except ImportError:
    __version__ = "N/A"
    pass  # not fatal if we can't get version

import urllib.request

# Parse command line options
parser = ArgumentParser(description="Script to download MRT/RIB BGP archives (from RouteViews).")
parser.add_argument('--latestv4', '-4', action='store_true', help='Grab lastest IPV4 data')
parser.add_argument('--latestv6', '-6', action='store_true', help='Grab lastest IPV6 data')
parser.add_argument('--version', action='store_true')

args = parser.parse_args()


# create a subclass and override the handler methods
class BgpSiteHtmlParser(HTMLParser):
    def error(self, message):
        super().error(message)

    def __init__(self, year_month: bool = True):
        super().__init__()
        self.latest_timestamp_pt_1: str = "-1"
        self.latest_timestamp_pt_2: str = "-1"
        if year_month:
            self.regex = re.compile('(\\d{4})\\.(\\d{2})')
        else:
            self.regex = re.compile('rib\\.(\\d{8})\\.(\\d{4}).bz2')

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for (attr, value) in attrs:
                if attr == 'href':
                    match = self.regex.match(value)
                    if match:
                        if int(match.group(1)) > int(self.latest_timestamp_pt_1):
                            self.latest_timestamp_pt_1 = match.group(1)
                            self.latest_timestamp_pt_2 = match.group(2)
                        if int(match.group(1)) == int(self.latest_timestamp_pt_1) and \
                                int(match.group(2)) > int(self.latest_timestamp_pt_2):
                            self.latest_timestamp_pt_2 = match.group(2)

    def get_latest_year_month(self):
        return "{}.{}/RIBS".format(self.latest_timestamp_pt_1, self.latest_timestamp_pt_2)

    def get_latest_file_name(self):
        return "rib.{}.{}.bz2".format(self.latest_timestamp_pt_1, self.latest_timestamp_pt_2)


def get_html(requested_url: str):
    return str(urllib.request.urlopen(requested_url).read(), 'ascii')


def get_latest_year_month_url(requested_url: str):
    bgp_data_parser = BgpSiteHtmlParser()
    bgp_data_parser.feed(get_html(requested_url))
    return "{}/{}".format(requested_url, bgp_data_parser.get_latest_year_month())


def get_latest_file_url(requested_url: str):
    bgp_data_parser = BgpSiteHtmlParser(False)
    bgp_data_parser.feed(get_html(requested_url))
    return "{}/{}".format(requested_url, bgp_data_parser.get_latest_file_name())


def find_latest_in_web(server: str, archive_root: str):
    base_url = "http://{}/{}".format(server, archive_root)
    latest_year_month_url = get_latest_year_month_url(base_url)
    latest_file_url = get_latest_file_url(latest_year_month_url)
    return latest_file_url


def download_report_hook(blocknum, bs, size):
    if blocknum % 10 == 0 or blocknum * bs >= size:
        print('\r %.2f%%' % min(((blocknum * bs) / size) * 100, 100), end='')


def web_download(requested_url: str, ipv: str):
    print("Downloading {} ...".format(requested_url))
    urllib.request.urlretrieve(requested_url, "v{}-{}".format(ipv, requested_url.split("/")[-1]), download_report_hook)
    print("\n ... done")


def find_latest_routeviews(archive_ipv):
    # RouteViews archives are as follows:
    # http://archive.routeviews.org/datapath/YYYYMM/ribs/XXXX
    archive_ipv = str(archive_ipv)
    assert archive_ipv in ('4', '6')
    return find_latest_in_web(server='archive.routeviews.org',
                              archive_root='bgpdata' if archive_ipv == '4' else
                              'route-views6/bgpdata'
                              )


def download_latest_for_version(ipv: str):
    url = find_latest_routeviews(ipv)
    web_download(url, ipv)


if args.version:
    print("MRT/RIB downloader version %s." % __version__)

if args.latestv4:
    # Download latest RouteViews MRT/RIB archive
    download_latest_for_version('4')

if args.latestv6:
    download_latest_for_version('6')
