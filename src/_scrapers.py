import time
import random
import platform
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FireFoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from thefuzz import fuzz
from pyvirtualdisplay import Display
from webdriver_manager.firefox import GeckoDriverManager


class Goodreads_Scraper:
    def __init__(self, logger, minimum_rating, minimum_votes, goodreads_wait_delay):
        self.diagnostic_logger = logger
        self.minimum_votes = minimum_votes
        self.minimum_rating = minimum_rating
        self.goodreads_wait_delay = goodreads_wait_delay
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 Edg/111.0.1661.62",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
        ]
        self.firexfox_options = webdriver.FirefoxOptions()
        self.firexfox_options.add_argument("--no-sandbox")
        self.firexfox_options.add_argument("--disable-dev-shm-usage")
        self.firexfox_options.add_argument("--window-size=1280,768")
        if "linux" in platform.platform().lower():
            display = Display(backend="xvfb", visible=False, size=(1280, 768))
            display.start()
        else:
            self.firexfox_options.add_argument("--headless")

    def get_firexfox_driver(self):
        firexfox_options = self.firexfox_options
        firexfox_options.add_argument(f"--user-agent={random.choice(self.user_agents)}")
        if "linux" in platform.platform().lower():
            return webdriver.Firefox(options=firexfox_options, service=FireFoxService(GeckoDriverManager().install()))
        else:
            return webdriver.Firefox(options=firexfox_options)

    def goodreads_recommendations(self, query):
        try:
            similar_books = []
            book_link = None
            try:
                self.diagnostic_logger.error(f"Creating New Driver...")
                driver = self.get_firexfox_driver()
                url = f"https://www.goodreads.com/search?q={query.replace(' ', '+')}"
                driver.get(url)

            except Exception as e:
                self.diagnostic_logger.error(f"Failed to create driver: {str(e)}")
                raise Exception("Failed to create driver...")

            try:
                wait = WebDriverWait(driver, self.goodreads_wait_delay)
                self.diagnostic_logger.info(f"Waiting to see if Overlay is displayed...")
                overlay = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "Overlay__window")))

            except Exception as e:
                self.diagnostic_logger.info(f"No Overlay displayed, continuing...")
                overlay = None

            try:
                if overlay:
                    self.diagnostic_logger.info(f"Overlay displayed on search, attempting to close it...")
                    close_div = overlay.find_element(By.CLASS_NAME, "modal__close")
                    close_button = close_div.find_element(By.CSS_SELECTOR, "img[alt='Dismiss']")
                    close_button.click()
            except Exception as e:
                self.diagnostic_logger.error(f"Failed to close overlay: {str(e)}")
                self.diagnostic_logger.info(f"Trying to continue")

            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN, Keys.PAGE_DOWN)
                table = driver.find_element(By.CLASS_NAME, "tableList")
                search_results = table.find_elements(By.CSS_SELECTOR, "tr")

                for result in search_results:
                    item_title_element = result.find_element(By.CSS_SELECTOR, "span[itemprop='name']")
                    item_title = item_title_element.text.strip()

                    author_tag = result.find_element(By.CSS_SELECTOR, "span[itemprop='author']")
                    item_author = author_tag.find_element(By.CSS_SELECTOR, "span[itemprop='name']").text.strip()

                    book_string = f"{item_author} - {item_title}"
                    match_ratio = fuzz.ratio(book_string, query)
                    if match_ratio > 90 or query in book_string:
                        self.diagnostic_logger.error(f"Found: {item_title} by {item_author} as {match_ratio}% match for {query}")
                        book_link_element = result.find_element(By.CSS_SELECTOR, "a.bookTitle")
                        book_link = book_link_element.get_attribute("href")
                        break
                else:
                    self.diagnostic_logger.info(f"No Matching book for {query}")

            except Exception as e:
                self.diagnostic_logger.error(f"Error trying to get link: {str(e)}")

            try:
                if not book_link:
                    raise Exception(f"Could not Find a link for book: {query}")
                if not all([urlparse(book_link).scheme, urlparse(book_link).netloc]):
                    raise Exception(f"Invalid URL: {book_link}")

                driver.get(book_link)
                try:
                    wait = WebDriverWait(driver, self.goodreads_wait_delay)
                    self.diagnostic_logger.info(f"Waiting to see if Overlay is displayed...")
                    overlay = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "Overlay__window")))
                except Exception as e:
                    self.diagnostic_logger.info(f"No Overlay displayed, continuing...")
                    overlay = None

                if overlay:
                    try:
                        self.diagnostic_logger.info(f"Overlay displayed on book link, attempting to close it...")
                        overlay.click()
                        close_button = overlay.find_element(By.CLASS_NAME, "Button__container")
                        close_button.click()
                    except Exception as e:
                        self.diagnostic_logger.error(f"Failed to close overlay: {str(e)}")
                        self.diagnostic_logger.info(f"Attempting to Continue")

                try:
                    element = driver.find_element(By.CLASS_NAME, "BookPage__relatedTopContent")
                    driver.execute_script("arguments[0].scrollIntoView();", element)
                    wait = WebDriverWait(driver, self.goodreads_wait_delay)
                    self.diagnostic_logger.info(f"Waiting until Carousel is displayed...")
                    carousel = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "Carousel")))
                except:
                    try:
                        self.diagnostic_logger.info(f"Could not find Carousel on first attempt trying again...")
                        wait = WebDriverWait(driver, self.goodreads_wait_delay)
                        self.diagnostic_logger.info(f"Waiting until Carousel is displayed...")
                        carousel = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "Carousel")))
                    except Exception as e:
                        self.diagnostic_logger.error(f"Failed to get book info: {str(e)}")
                        raise Exception("No Valid Carousel")

                next_button = driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Carousel, Next page"]')
                book_cards = carousel.find_elements(By.CLASS_NAME, "BookCard")

                total_cards = len(book_cards)
                for i in range(0, total_cards, 4):
                    book_cards = carousel.find_elements(By.CLASS_NAME, "BookCard")
                    for card in book_cards[i : i + 4]:
                        try:
                            title = card.find_element(By.CSS_SELECTOR, '[data-testid="title"]').text
                            author = card.find_element(By.CSS_SELECTOR, '[data-testid="author"]').text
                            rating = card.find_element(By.CLASS_NAME, "AverageRating__ratingValue").text
                            votes = card.find_element(By.CSS_SELECTOR, '[data-testid="ratingsCount"]').text.strip()
                            image = card.find_element(By.CSS_SELECTOR, "img.ResponsiveImage")
                            image_url = image.get_attribute("src")
                            if "m" in votes:
                                vote_count = int(float(votes.replace("m", "").replace(",", "")) * 1000000)
                            elif "k" in votes:
                                vote_count = int(float(votes.replace("k", "").replace(",", "")) * 1000)
                            else:
                                vote_count = int(0 if votes.replace(",", "") == "" else votes.replace(",", ""))
                            ratings_value = 0.0 if rating == "" else float(rating)
                            if ratings_value > self.minimum_rating and vote_count > self.minimum_votes:
                                new_book_detail = {
                                    "Name": title,
                                    "Author": author,
                                    "Rating": f"Rating: {rating}",
                                    "Votes": f"Votes: {votes}",
                                    "Overview": "",
                                    "Image_Link": image_url,
                                    "Base_Book": query,
                                    "Status": "",
                                    "Page_Count": "",
                                    "Published_Date": "",
                                }
                                similar_books.append(new_book_detail)

                        except Exception as e:
                            self.diagnostic_logger.error(f"Failed to get book info: {str(e)}")

                    if i + 4 < total_cards and next_button.is_enabled():
                        next_button.click()
                        self.diagnostic_logger.info(f"Checking Next Batch...")
                        time.sleep(1)

            except Exception as e:
                self.diagnostic_logger.error(f"Error extracting data: {str(e)}")

        except Exception as e:
            self.diagnostic_logger.error(f"Failed to get similar books: {str(e)}")

        finally:
            self.diagnostic_logger.info(f"Discovered {len(similar_books)} potential books")
            driver.quit()
            return similar_books
