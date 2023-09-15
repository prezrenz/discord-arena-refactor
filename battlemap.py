import requests
import base64
from bs4 import BeautifulSoup


base_url = "https://otfbm.io/"
token_url = "https://token.otfbm.io/meta/"


def get_url():
	return base_url

def get_shortcode(url):
	url_bytes = url.encode("ascii")
	base64_bytes = base64.b64encode(url_bytes)
	base64_string = base64_bytes.decode("ascii")
	
	page = requests.get(token_url + base64_string)
	
	soup = BeautifulSoup(page.content, "html.parser")
	
	return soup.find("body").text.strip()