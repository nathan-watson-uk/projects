from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
import re

urls = []


def get_links(url):
    header = {
        'User-Agent': r"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      r"(KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
    }
    req = Request(f"http://{url}", headers=header)
    html = urlopen(req)
    print(html)
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.findAll('a'):
        # print(link.get('href'))
        urls.append(link.get('href'))

    target_url = url.replace("http://", "").replace(".", "\.")
    print(target_url)
    reg_express = f"((?=.*\=)(https|http):\/\/({target_url})(\/|\?)([a-zA-Z]|\w+|\/)\S*(\?|\=|[a-zA-Z][0-9])\s*([a-zA-Z0-9])*$)"
    print(urls)
    for url in urls:
        try:
            print(re.search(reg_express, url)[0])
        # TypeError if match is NoneType i.e. the url doesn't match
        except TypeError:
            pass


# urllib puts www. at the start, so you must include this in the supplied URL or else regex will not match!
get_links("www.testurl.com")