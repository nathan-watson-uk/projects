class BaseError(Exception):
    pass


class NotInDistance(BaseError):
    """Raised when the given distance is not in the list:
            2, 5, 10, 15, 20, 25, 50, 75, 100, 150, 200

    Not sure if it is necessary to create a custom exception?
    """

    def __init__(self, distance, message=": Distance is not in -->"):
        self.distance = distance
        self.allowed = [2, 5, 10, 15, 20, 25, 50, 75, 100, 150, 200]
        self.message = message

    def __str__(self):
        return f"{self.distance} {self.message} {self.allowed} Ref. 1"


class WrongNumberOfResults(BaseError):
    """Raised when the given numbers are results is not in the list:
            25, 50, 100 ,200

    """

    def __init__(self, number, message=": Number of results is not in -->"):
        self.number = number
        self.allowed = [25, 50, 100, 200]
        self.message = message

    def __str__(self):
        return f"{self.number} {self.message} {self.allowed} Ref. 1"


class SetupNotComplete(BaseError):
    """Raised if the user hasn't called the scrape_setup method.

       The scrape_setup method validates/compiles all the inputted data.
    """

    def __init__(self, message="You need to call scrape_setup before running the scraper. Ref. 2"):
        self.message = message
        super().__init__(self.message)


class InvalidChromeDriverPath(BaseError):
    """Raised when the user has provided an invalid chrome extension.
    For selenium to work a valid chromedriver.exe path must be provided.

    If you're running into problems make sure your chromedriver and chrome application are on the same version.
    """

    def __init__(self, path, message="| Invalid chromedriver.exe path, make sure you call 'set_chromedriver. Ref. 3'"):
        self.path = path
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"{self.path} {self.message}"


class FailedToFindContent(BaseError):
    """This error occurs when page content doesn't load properly.
    (Determined when 20% of content doesn't return expected data)

    Try changing/refining the search query.
    """

    def __init__(self, li, message="| Unable to locate list item content."
                                   " Maybe trying changing/refining the search query."):
        self.li = li
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"{self.li } {self.message}"


from currency_converter import CurrencyConverter
import time
from datetime import datetime
from math import floor
import pickle

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.proxy import Proxy, ProxyType

from bs4 import BeautifulSoup

from ebay_exceptions import NotInDistance, SetupNotComplete, InvalidChromeDriverPath,\
    WrongNumberOfResults, FailedToFindContent

from get_proxy import get_free_proxies



class EbayItem:

    def __init__(self, item_id, title, price, postage, item_link):
        self.item_id = item_id
        self.title = title
        self.price = price
        self.postage = postage
        # self.time_left = time_left
        self.item_link = item_link

    def __str__(self):
        return vars(self)


class EbayScrape:

    def __init__(self, url_query, distance, postcode):
        try:
            self.distance = int(distance)
        except TypeError:
            raise NotInDistance(distance)

        # Chromedriver/Selenium Settings
        self.proxy = False
        self.chrome_path = ""
        self.user_agent = r"Mozilla/5.0 (Windows NT 10.0; Win64; x64)" \
                          r" AppleWebKit/537.36 (KHTML, like Gecko)" \
                          r" Chrome/87.0.4280.88 Safari/537.36"
        # Ebay Url
        self.url = None
        self.postcode = str(postcode).upper()
        self.url_query = url_query
        self.per_page = 50

        # Other
        self.status = "Inactive"
        self.setup = False
        self.item_list = []

    def __str__(self):
        return f"Status: {self.status} | {self.url}"

    def set_useragent(self, agent):  # Sets the object user_agent
        if isinstance(agent, str):
            self.user_agent = agent
        else:
            raise ValueError(f"Got {type(agent)}, expected str.")

    def set_chromedriver(self, directory):  # Sets the object chromedriver
        import os

        if not os.path.exists(os.path.dirname(directory)):
            raise InvalidChromeDriverPath(directory)

        if isinstance(directory, str) and os.path.exists(os.path.dirname(directory)):
            self.chrome_path = directory

        else:
            raise TypeError(f"'{directory}' must be a String and Valid Directory")

    def scrape_setup(self):
        self.postcode = self.postcode.replace(" ", "")

        distances = [2, 5, 10, 15, 20, 25, 50, 75, 100, 150, 200]  # Valid distances offered by Ebay in miles.
        try:
            if self.distance in distances:
                pass

            else:
                raise NotInDistance(self.distance)

        except TypeError:
            raise TypeError(f"Variable 'distance' must be an integer, instead got '{type(self.distance)}'")

        if not isinstance(self.url_query, list):
            raise TypeError(self.url_query)

        for query in range(len(self.url_query)):

            self.url_query[query] = "%20".join(str(self.url_query[query]).split(" "))
            # Splits the query and makes it url friendly. (%20)

        if isinstance(self.per_page, int):
            if self.per_page in [25, 50, 100, 200]:

                self.url = f"https://www.ebay.co.uk/sch/i.html?_from=R40&_nkw={self.url_query[0]}&_sacat=0&_sadis=" \
                           f"{self.distance}&_stpos={self.postcode}&_rt=nc&_ipg={self.per_page}&_pgn={1}&LH_BIN=1"

                self.setup = True
                return None

            else:
                raise WrongNumberOfResults

        else:
            raise TypeError(f"Got {type(self.per_page)} but expect an int for 'per_page'.")

    def update_url(self, num, q):
        self.url = f"https://www.ebay.co.uk/sch/i.html?_from=R40&_nkw={q}&_sacat=0&_sadis={self.distance}&_stpos=" \
                   f"{self.postcode}&_rt=nc&_ipg={self.per_page}&_pgn={num}&LH_BIN=1"

    def execute_scraper(self):

        if self.setup:  # Checks if the user has run scrape_setup.

            # Set a counter for the proxy outside the main loop.
            # proxy_counter = 0

            for query in range(len(self.url_query)):  # +1 or else it will break out too early

                self.update_url(1, self.url_query[query])  # sets page 1 and query from the list of queries

                chrome_options = Options()

                # Creates selenium driver object
                driver = webdriver.Chrome(self.chrome_path, options=chrome_options)

                # Proxy
                # if self.proxy:
                #
                #     with open("proxy.txt", "r") as proxies:
                #         proxy_counter += 1
                #
                #         proxy_list = proxies.readlines()
                #         total_num_of_proxies = len(proxy_list)
                #
                #         proxy = Proxy()
                #         proxy.proxy_type = ProxyType.MANUAL
                #         proxy.http_proxy = f"{proxy_list[proxy_counter]}"
                #
                #         capabilities = webdriver.DesiredCapabilities.CHROME
                #         proxy.add_to_capabilities(capabilities)
                #
                #         driver = webdriver.Chrome(self.chrome_path, options=chrome_options,
                #                                   desired_capabilities=capabilities)
                #
                # # If all the proxies are used, get a fresh list
                # if total_num_of_proxies == proxy_counter:
                #     get_free_proxies()

                self.status = f"Currently Active | Started @ {datetime.now().strftime('%H:%M:%S')}"

                driver.get(self.url)

                page = driver.execute_script("return document.getElementsByTagName('html')[0].innerHTML")
                soup = BeautifulSoup(page, 'lxml')  # Using lxml instead of html.parser to increase performance.

                number_of_results = int(soup.find("h1", class_="srp-controls__count-heading").find("span").getText().replace
                                        (",", ""))  # Gets the number of results and converts from str to int

                # Ebay only shows up to 9000 results
                if number_of_results > 9000:
                    number_of_results = 9000

                total_pages = floor(number_of_results / self.per_page)  # Calculates the number of pages and rounds down

                id_increment = 0  # Used to generate ID from ebay ID
                content_failure_count = 0  # Used to track

                print(self.status)
                completion_count = 0

                for page_num in range(1, total_pages+1):
                    if page_num >= 32:
                        break

                    # Updates with scraper progress in percentage.
                    if page_num == 1:
                        print("Starting Scraper...", end="")

                    else:
                        print("", end="\r", flush=True)  # Flushes and overwrties previous line
                        print(f"Scraper is {(completion_count/number_of_results)*100:.2f}% Complete..."
                              f" ({completion_count}/{number_of_results-self.per_page})", end="")

                    self.update_url(page_num, self.url_query[query])  # Updates url to new page number

                    driver.get(self.url)  # Gets new URL

                    current_page = driver.page_source  # No need to wait for JS as it has already loaded on first page.

                    page_soup = BeautifulSoup(current_page, 'lxml')

                    if page_num > 1:
                        id_increment += self.per_page

                    for list_item in page_soup.findAll("li", class_="s-item s-item--watch-at-corner"):
                        try:
                            # Creates EbayItem objects and appends it to the EbayScrape "item_list"
                            self.item_list.append(
                                vars(
                                    EbayItem(
                                        # Generates ID
                                        int(str(list_item.get("data-view")).split("iid:")[1]) + id_increment,
                                        # Title
                                        list_item.find("h3", class_="s-item__title").getText().lower(),
                                        # Price
                                        list_item.find("span", class_="s-item__price").getText(),
                                        # Post
                                        list_item.find("span", class_="s-item__shipping s-item__logisticsCost").getText(),
                                        # Time Left (auction only)
                                        # list_item.find("span", class_="s-item__time-left").getText(),
                                        # Link
                                        list_item.find("a").get("href")
                                    )
                                )
                            )
                            completion_count += 1

                        except AttributeError as e:  # If a value can't be found an AttributeError will come from NoneType.
                            content_failure_count += 1  # Counts an additional failure.

                            # The following states that if more than 20% of results are failures there is something
                            # systematically wrong with the scraping and must raise the FailedToFindContent error.

                            if content_failure_count > ((number_of_results-self.per_page) / 5):
                                raise FailedToFindContent(list_item)  # Used to handle when data isn't located

                            else:
                                continue

                self.status = f"Inactive | Last Active @ {datetime.now().strftime('%H:%M:%S')}"

                driver.close()  # Even in headless mode the driver must close() or risk using system resources.
                # However, please note that the headless driver seems to cause problems with content loading.

                # Displays valueable information for the user to see.
                print(f"\n\nNumber of Results: {number_of_results}"
                      f"\nTotal Pages: {total_pages}"
                      f"\nExpected Results: ~{number_of_results-self.per_page}"
                      f"\nActual Results: {len(self.item_list)}"
                      f"\n{self.__str__()}\n")

            with open("dict_data.pkl", "wb") as file:
                for di in self.item_list:
                    pickle.dump(di, file)
        else:
            # Raised if scrape_setup is not called, it is essential for functionality.
            raise SetupNotComplete

def remove_outliers(price_list):
    from numpy import percentile
    from statistics import median

    # Calculates the interquartile ranger
    iqr = percentile(price_list, [75, 25])[0] - percentile(price_list, [75, 25])[1]

    # +-1.5 times the interquartile range is considered an outlier
    upper_bound, lower_bound = median(price_list) + (iqr * 1.5), median(price_list) - (iqr * 1.5)

    for price in price_list:
        if lower_bound > price or price > upper_bound:
            price_list.remove(price)

        # This else statement isn't needed but sometimes can be beneficial adding for readability
        else:
            continue

    return price_list


def match_name_variant(pokemon_name):  # Checks a name to see if it is a variant.

    # Even though names should already be lowercase I've added .lower just to be sure.

    # The following contains all the name variations.
    name_dict = {"jangmo o": "jangmo-o", "jangmoo": "jangmo-o", "hakamo o": "hakamo-o", "hakamoo": "hakamo-o",
                 "kommo o": "kommo-o", "kommoo": "kommo-o", "sirfetchd": "sirfetch'd",  "sirfetch d": "sirfetch'd",
                 "ho oh": "ho-oh",  "mr rime": "mr. rime", "farfetch d": "farfetch'd",  "farfetchd": "farfetch'd",
                 "mr mime": "mr. mime",  "porygon z": "porygon-z",  "mime jr": "mime jr.", "porygonz": "porygon-z",
                 "mew": "mewtwo", "mew two": "mewtwo"}

    # To add more variants put use "-variant name-": "-original-"

    # First letters of all the names that have variants
    if pokemon_name[0].lower() not in ["j", "h", "k", "s", "m", "f", "p"]:
        return pokemon_name.lower()  # Returns original names, no changes needed

    else:
        try:
            return name_dict[pokemon_name.lower()]  # Returns actual name, not variant

        except KeyError:
            return pokemon_name.lower()

import pokemon_tcg
from card_info_extraction import parse_card_data, tcg_market_price_search
from currency_converter import CurrencyConverter
import string
import socket
import time

scraper = pokemon_tcg.EbayScrape(["pokemon tcg card mint", "pokemon card"], 200, "LE2")


# Gets the correct chromedriver for 
if str(socket.gethostname()) == "DESKTOP-2M0L686":
    scraper.set_chromedriver(r"C:\Users\natej\PycharmProjects\pokemon-tcg\chromedriver.exe")

if str(socket.gethostname()) == "DESKTOP-2GCE5MC":
    scraper.set_chromedriver(r"C:\Users\Trey\Documents\Projects\PythonProjects\chromedriver.exe")

if str(socket.gethostname()) not in ["DESKTOP-2M0L686", "DESKTOP-2GCE5MC"]:
    exit(print("System name not matched. Please update it with socket.gethostname()."))

# Updates dict_data.pkl file and scraper.item_list with new results
scraper.per_page = 200
scraper.scrape_setup()
scraper.execute_scraper()

# Parse card data into an object list to access
card_obj_list = parse_card_data(scraper.item_list)

total_number_to_compare = len(card_obj_list)
progress = 0

with open("output.txt", "a") as output_file:

    for card_obj in card_obj_list:
        progress += 1

        if progress == 1:
            print("Starting Profit Calculator...", end="")

        else:
            print("", end="\r", flush=True)  # Flushes and overwrties previous line
            print(f"Profit Calculator is {(progress / total_number_to_compare) * 100:.2f}% Complete...", end="")

        time.sleep(2)  # Makes sure too many requests aren't sent

        rel_tcg_price = tcg_market_price_search(card_obj.card_name, card_obj.set_number, card_obj.basename, card_obj.card_type)

        try:
            if "Failed" in rel_tcg_price:
                continue
        except TypeError:
            pass

        try:
            rel_tcg_price = CurrencyConverter().convert(int(rel_tcg_price), "USD", "GBP")
        except TypeError:
            continue
        # print(f"TCG: {rel_tcg_price} Ebay: {card_obj.card_cost} Margin: f{((int(rel_tcg_price)
        # / card_obj.card_cost) - 1) * 100}%")
        try:
            profit_margin = ((int(rel_tcg_price) / card_obj.card_cost) - 1) * 100
        except ZeroDivisionError:
            continue

        if profit_margin > 0.2:
            output_file.write(f"{string.capwords(card_obj.card_name)} Ebay Price: £{card_obj.card_cost:.2f}"
                              f" TCG Market Price: £{rel_tcg_price:.2f} Profit Margin: + {profit_margin:.2f}%"
                              f" Link: {card_obj.card_link}\n")
        else:
            continue


from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
import time, socket

options = Options()
options.add_argument("window-size=1920,1080")


url = r"https://www.pokemon.com/uk/pokedex/"
path = ""

if str(socket.gethostname()) == "DESKTOP-2M0L686":
    path = r"C:\Users\natej\PycharmProjects\pokemon-tcg\chromedriver.exe"

if str(socket.gethostname()) == "DESKTOP-2GCE5MC":
    path = r"C:\Users\Trey\Documents\Projects\PythonProjects\chromedriver.exe"

if str(socket.gethostname()) not in ["DESKTOP-2M0L686", "DESKTOP-2GCE5MC"]:
    exit(print("System name not matched. Please update it with socket.gethostname()."))

with webdriver.Chrome(path, options=options) as driver:
    driver.get(url)
    time.sleep(2)  # Delay to load content
    driver.find_element_by_xpath("/html/body/div[1]/div/div[1]/div/div[2]").click()  # Closes cookie prompt
    driver.find_element_by_xpath("/html/body/div[4]/section[5]/div[2]/a/span").click()  # Clicks "Load More"

    for _ in range(80):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

    page_soup = BeautifulSoup(driver.page_source, 'lxml')

    for li in page_soup.findAll("li", class_="animating"):
        print(li.find("h5").getText())

url = r"https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_by_name"

with webdriver.Chrome(path, options=options) as driver:
    driver.get(url)
    time.sleep(2)  # Delay to load content

    for table_count in range(1, 25):

        for tr_count in range(2, 80):
            try:
                print(driver.find_element_by_xpath(f"/html/body/div[1]/div[2]/div/"
                                                   f"div[7]/div/div[1]/div[4]/table[{table_count}]/tbody/tr[{tr_count}]"
                                                   f"/td[2]/a").get_attribute('text'))
            except NoSuchElementException:
                break

url = r"https://bulbapedia.bulbagarden.net/wiki/Owner%27s_Pok%C3%A9mon_(TCG)"

with webdriver.Chrome(path, options=options) as driver:
    driver.get(url)
    time.sleep(2)  # Delay to load content

    for table_count in range(1, 38):

        for tr_count in range(3, 40):
            try:
                print(driver.find_element_by_xpath(f"/html/body/div[1]/div[2]/div/div[7]/div/div[1]/div[4]/"
                                                   f"table[{table_count}]/tbody/tr[{tr_count}]/td[1]"
                                                   f"/a").get_attribute('text'))
            except NoSuchElementException:
                continue

url = r"https://bulbapedia.bulbagarden.net/wiki/Mega_Evolution"

with webdriver.Chrome(path, options=options) as driver:
    driver.get(url)
    time.sleep(2)  # Delay to load content

    for table_count in [2, 3]:
        print(table_count)

        for tr_count in range(3, 31):
            try:
                print(driver.find_element_by_xpath(f"/html/body/div[1]/div[2]/div/div[7]/div/div[1]/div[4]/table[{table_count}]/tbody/tr[{tr_count}]/td[1]/a").get_attribute('text'))
            except NoSuchElementException:
                continue
                import pickle
                import requests
                import re
                import string
                import time
                from config import public_key, private_key, access
                from utility_functions import match_name_variant


                class CardData:

                    def __init__(self, card_name, set_number, card_type, basename, card_link, card_cost):
                        self.card_name = card_name
                        self.set_number = set_number
                        self.card_type = card_type
                        self.basename = basename
                        self.card_link = card_link
                        self.card_cost = card_cost

                    def __str__(self):
                        print(vars(self))


                def parse_card_data(data):
                    print("Parsing Card Data...")

                    card_detail_list = []
                    card_list = []

                    if isinstance(data, list):
                        card_detail_list = data

                    if not data:

                        with (open("dict_data.pkl", "rb")) as file:

                            while True:
                                try:
                                    card_detail_list.append(pickle.load(file))
                                except EOFError:
                                    break

                    with open('name_variants.txt', 'r', encoding='utf-8') as name_file:
                        name_variants = name_file.readlines()  # save file contents as array
                        for i in range(len(name_variants)):
                            name_variants[i] = name_variants[i].rstrip('\n')

                    with open("basename.txt", "r", encoding="utf-8") as basename_file:
                        basenames = basename_file.readlines()  # save file contents as array
                        for i in range(len(basenames)):
                            basenames[i] = basenames[i].rstrip('\n')

                    count = 0
                    temp_name = ''
                    for datapoint in card_detail_list:
                        print(datapoint["title"])

                    for datapoint in card_detail_list:

                        for name in name_variants:
                            apo1 = '’'
                            apo2 = "'"

                            # blacklist = ['unbranded', 'proxy', 'illegitimate', 'un branded', 'third party', '3rd party', 'replica',
                            #              'pretend', 'not official', 'fake', 'ungenuine', 'custom']
                            # # Checks for non-genuine cards
                            # for black in blacklist:
                            #     if black in datapoint["title"]:
                            #         temp_name = "Blacklisted"
                            #
                            # if temp_name == "Blacklisted":
                            #     continue

                            if re.search(f"{name.replace(apo1, apo2)}", datapoint["title"]):
                                # Sets basename to name initally
                                temp_basename = name

                                for basename in basenames:
                                    if re.search(f"{basename}", name):
                                        try:
                                            # Attempts to split to remove first word such as dark or shining.
                                            temp_basename = f"{match_name_variant(name.split(' ')[1])}"

                                        except IndexError:
                                            # No name prefix so just check and set variant
                                            temp_basename = match_name_variant(name)

                                        break

                                # This first section gets all the data to identify the card from the listing title.

                                try:
                                    # Attempts to split to remove first word such as dark or shining.
                                    temp_name = f"{name.split(' ')[0]} {match_name_variant(name.split(' ')[1])}"

                                except IndexError:
                                    temp_name = match_name_variant(name)

                                temp_type = ""

                                for match in [" v max ", " vmax ", " v ", " gx ", " ex "]:
                                    # If re.search finds something, it will return a string
                                    # If it can't find something it will return None

                                    if re.search(match, datapoint["title"]):
                                        temp_name = f"{temp_name} {match.lstrip(' ').rstrip(' ')}"
                                        break

                                for match in ["reverse holo", "holo"]:
                                    if re.search(match, datapoint["title"]):
                                        temp_type = match
                                        break

                                if re.search("secret", datapoint["title"]):
                                    temp_name = f"{temp_name} secret"

                                if re.search("full art", datapoint["title"]):
                                    temp_name = f"{temp_name} full art"

                                try:
                                    temp_set = re.search('(\d{1,3}/\d{1,3})', datapoint["title"]).group().split("/")
                                    temp_set[0], temp_set[1] = temp_set[0].lstrip("0"), temp_set[1].lstrip("0")
                                    temp_set = "/".join(temp_set)

                                except AttributeError:
                                    break

                                # This section calculates the price

                                total_price = 0
                                price = float(re.findall(r"\d+\.\d+", datapoint['price'])[0])
                                total_price += price

                                if "." in datapoint['postage']:
                                    postage = float(re.findall(r"\d+\.\d+", datapoint['postage'])[0])
                                    total_price += postage

                                else:
                                    postage = "Free Postage"

                                count += 1

                                print(f"{temp_name} | {temp_set} | {count}/{len(card_detail_list)}"
                                      f" | Price: £{price:.2f} | Postage: {postage} | Total Cost: £{total_price:.2f}"
                                      f" | Basename: {temp_basename}")

                                card_list.append(
                                    CardData(temp_name, temp_set, temp_type, temp_basename, datapoint["item_link"],
                                             total_price))
                                break

                            else:
                                continue

                        continue

                    return card_list


                def set_name_match(r, i, n, h, ct):
                    clean_name = r.json()["results"][i]["cleanName"]

                    # Searches to match name
                    find_count = 0
                    for s in n.split(" "):
                        if re.search(s, clean_name, re.IGNORECASE):
                            find_count += 1

                    if find_count == len(n.split(" ")):

                        # Get price from skuID
                        url = f"https://api.tcgplayer.com/pricing/product/{r.json()['results'][i]['productId']}"
                        price_response = requests.request("GET", url, headers=h)

                        if ct == "reverse holo":
                            for e in range(len(price_response.json()['results'])):

                                if price_response.json()['results'][e]['subTypeName'] == "Reverse Holofoil":
                                    if not price_response.json()['results'][e]['marketPrice']:
                                        return "Failed"
                                    else:
                                        return price_response.json()['results'][e]['marketPrice']

                        if ct == "holo":
                            for e in range(len(price_response.json()['results'])):

                                if price_response.json()['results'][e]['subTypeName'] == "Holofoil":
                                    if not price_response.json()['results'][e]['marketPrice']:
                                        return "Failed"
                                    else:
                                        return price_response.json()['results'][e]['marketPrice']

                        else:
                            url = f"https://api.tcgplayer.com/pricing/marketprices/{r.json()['results'][i]['skus'][0]['skuId']}"
                            price_response = requests.request("GET", url, headers=h)

                            return price_response.json()['results'][0]['price']

                            # for e in range(len(price_response.json()['results'])):
                            #     print("Getting normal price")
                            #     if price_response.json()['results'][e]['subTypeName'] == "Normal":
                            #         if not price_response.json()['results'][e]['marketPrice']:
                            #             return "Failed"
                            #         else:
                            #             return price_response.json()['results'][e]['marketPrice']

                    return None


                def tcg_market_price_search(name, card_set, basename, card_type):

                    # Finding cards isn't case sensititve due to re.IGNORECASE usage

                    # Used as a precaution as tcgplayer capitalises names
                    name = string.capwords(name)

                    user_agent = r"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)" \
                                 r" Chrome/87.0.4280.88 Safari/537.36 Project: Pokemon University of Portsmouth"

                    # Change header and add access token

                    headers = {"accept": "application/json",
                               "Content-Type": "application/json",
                               "User-Agent": f"{user_agent}",
                               "Authorization": "bearer " + access}

                    url = "https://api.tcgplayer.com/catalog/categories/3/search"

                    payload = {
                        "filters": [
                            {
                                "values": [f"{basename}"],
                                "name": "productName"
                            }
                        ],
                        "limit": 250
                    }

                    search_response = requests.request("POST", url, json=payload, headers=headers)

                    url = f"https://api.tcgplayer.com/catalog/products/{search_response.json()['results']}"

                    query_params = {"getExtendedFields": "true", "includeSkus": "true"}

                    response = requests.request("GET", url, headers=headers, params=query_params)

                    results_length = len(response.json()["results"])

                    if response.json()['errors'][0] == "No valid IDs specified.":
                        # print(f"Search For {name} Failed")
                        return None

                    # Used to fix bugs
                    # print(len(response.json()["results"]))

                    # for i in range(results_length):
                    #     try:
                    #         print(response.json()["results"][i]["cleanName"])
                    #         print(response.json()["results"][i]["extendedData"][0]["value"])
                    #         print("")
                    #     except IndexError:
                    #         continue

                    for i in range(results_length):
                        try:

                            # Format xxx
                            if response.json()["results"][i]["extendedData"][0]["value"].split("/")[0] == \
                                    str(card_set).split("/")[0]:
                                card_match_price = set_name_match(response, i, name, headers, card_type)
                                if card_match_price == "Failed":
                                    return f"Failed To Get Price For {name}"

                                if not card_match_price:
                                    continue

                                else:
                                    return card_match_price

                        except IndexError:
                            continue

                    for i in range(results_length):
                        try:

                            # Format xxx/xxx
                            if str(card_set) in response.json()["results"][i]["extendedData"][0]["value"]:

                                card_match_price = set_name_match(response, i, name, headers, card_type)
                                if card_match_price == "Failed":
                                    return f"Failed To Get Price For {name}"

                                if not card_match_price:
                                    continue

                                else:
                                    return card_match_price

                        except IndexError:
                            continue

                    return f"Failed To Get Price For {name}"

                # print(tcg_market_price_search("pikachu v full art", "44/185", "pikachu v", ""))

                # card_obj_list = parse_card_data(None)
                #
                #
                # for card_obj in card_obj_list:
                #     time.sleep(1.7)  # Makes sure too many requests aren't sent
                #
                #     price = tcg_market_price_search(card_obj.card_name, card_obj.set_number, card_obj.basename, card_obj.card_type)
                #
                #     print(f"Name: {card_obj.card_name} Set: {card_obj.set_number} Price: {price}")
                #
                #     if price == "Failed to match name":
                #         print(f"{card_obj.card_name, card_obj.set_number, card_obj.basename, card_obj.card_type}")


