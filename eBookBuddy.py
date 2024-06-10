import json
import time
import logging
import os
import random
import threading
import concurrent.futures
from flask import Flask, render_template, request
from flask_socketio import SocketIO
import requests
from thefuzz import fuzz
from unidecode import unidecode
import _scrapers


class DataHandler:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        self.diagnostic_logger = logging.getLogger()
        self.search_in_progress_flag = False
        self.search_exhausted_flag = True
        self.clients_connected_counter = 0
        self.config_folder = "config"
        self.recommended_books = []
        self.readarr_items = []
        self.cleaned_readarr_items = []
        self.stop_event = threading.Event()
        self.stop_event.set()
        if not os.path.exists(self.config_folder):
            os.makedirs(self.config_folder)
        self.load_environ_or_config_settings()
        self.goodreads_scraper = _scrapers.Goodreads_Scraper(self.diagnostic_logger, self.minimum_rating, self.minimum_votes, self.goodreads_wait_delay)
        if self.auto_start:
            try:
                auto_start_thread = threading.Timer(self.auto_start_delay, self.automated_startup)
                auto_start_thread.daemon = True
                auto_start_thread.start()

            except Exception as e:
                self.diagnostic_logger.error(f"Auto Start Error: {str(e)}")

    def load_environ_or_config_settings(self):
        # Defaults
        default_settings = {
            "readarr_address": "http://192.168.1.2:8787",
            "readarr_api_key": "",
            "root_folder_path": "/data/media/books",
            "google_books_api_key": "",
            "readarr_api_timeout": 120.0,
            "quality_profile_id": 1,
            "metadata_profile_id": 1,
            "search_for_missing_book": False,
            "minimum_rating": 3.5,
            "minimum_votes": 500,
            "goodreads_wait_delay": 12.5,
            "readarr_wait_delay": 7.5,
            "thread_limit": 1,
            "auto_start": False,
            "auto_start_delay": 60,
        }

        # Load settings from environmental variables (which take precedence) over the configuration file.
        self.readarr_address = os.environ.get("readarr_address", "")
        self.readarr_api_key = os.environ.get("readarr_api_key", "")
        self.root_folder_path = os.environ.get("root_folder_path", "")
        self.google_books_api_key = os.environ.get("google_books_api_key", "")
        readarr_api_timeout = os.environ.get("readarr_api_timeout", "")
        self.readarr_api_timeout = float(readarr_api_timeout) if readarr_api_timeout else ""
        quality_profile_id = os.environ.get("quality_profile_id", "")
        self.quality_profile_id = int(quality_profile_id) if quality_profile_id else ""
        metadata_profile_id = os.environ.get("metadata_profile_id", "")
        self.metadata_profile_id = int(metadata_profile_id) if metadata_profile_id else ""
        search_for_missing_book = os.environ.get("search_for_missing_book", "")
        self.search_for_missing_book = search_for_missing_book.lower() == "true" if search_for_missing_book != "" else ""
        minimum_rating = os.environ.get("minimum_rating", "")
        self.minimum_rating = float(minimum_rating) if minimum_rating else ""
        minimum_votes = os.environ.get("minimum_votes", "")
        self.minimum_votes = int(minimum_votes) if minimum_votes else ""
        goodreads_wait_delay = os.environ.get("goodreads_wait_delay", "")
        self.goodreads_wait_delay = float(goodreads_wait_delay) if goodreads_wait_delay else ""
        readarr_wait_delay = os.environ.get("readarr_wait_delay", "")
        self.readarr_wait_delay = float(readarr_wait_delay) if readarr_wait_delay else ""
        thread_limit = os.environ.get("thread_limit", "")
        self.thread_limit = int(thread_limit) if thread_limit else ""
        auto_start = os.environ.get("auto_start", "")
        self.auto_start = auto_start.lower() == "true" if auto_start != "" else ""
        auto_start_delay = os.environ.get("auto_start_delay", "")
        self.auto_start_delay = float(auto_start_delay) if auto_start_delay else ""

        # Load variables from the configuration file if not set by environmental variables.
        try:
            self.settings_config_file = os.path.join(self.config_folder, "settings_config.json")
            if os.path.exists(self.settings_config_file):
                self.diagnostic_logger.info(f"Loading Config via file")
                with open(self.settings_config_file, "r") as json_file:
                    ret = json.load(json_file)
                    for key in ret:
                        if getattr(self, key) == "":
                            setattr(self, key, ret[key])
        except Exception as e:
            self.diagnostic_logger.error(f"Error Loading Config: {str(e)}")

        # Load defaults if not set by an environmental variable or configuration file.
        for key, value in default_settings.items():
            if getattr(self, key) == "":
                setattr(self, key, value)

        # Save config.
        self.save_config_to_file()

    def automated_startup(self):
        self.request_books_from_readarr(checked=True)
        items = [x["name"] for x in self.readarr_items]
        self.start(items)

    def connection(self):
        if self.recommended_books:
            if self.clients_connected_counter == 0:
                if len(self.recommended_books) > 25:
                    self.recommended_books = random.sample(self.recommended_books, 25)
                else:
                    self.diagnostic_logger.info(f"Shuffling Books")
                    random.shuffle(self.recommended_books)
            socketio.emit("more_books_loaded", self.recommended_books)

        self.clients_connected_counter += 1

    def disconnection(self):
        self.clients_connected_counter = max(0, self.clients_connected_counter - 1)

    def start(self, data):
        try:
            socketio.emit("clear")
            self.search_exhausted_flag = False
            self.books_to_use_in_search = []
            self.recommended_books = []

            for item in self.readarr_items:
                item_name = item["name"]
                if item_name in data:
                    item["checked"] = True
                    self.books_to_use_in_search.append(item_name)
                else:
                    item["checked"] = False

            if self.books_to_use_in_search:
                self.stop_event.clear()
            else:
                self.stop_event.set()
                raise Exception("No Readarr Books Selected")

        except Exception as e:
            self.diagnostic_logger.error(f"Startup Error: {str(e)}")
            self.stop_event.set()
            ret = {"Status": "Error", "Code": str(e), "Data": self.readarr_items, "Running": not self.stop_event.is_set()}
            socketio.emit("readarr_sidebar_update", ret)

        else:
            thread = threading.Thread(target=data_handler.find_similar_books, name="Start_Finding_Thread")
            thread.daemon = True
            thread.start()

    def request_books_from_readarr(self, checked=False):
        try:
            self.diagnostic_logger.info(f"Getting Books from Readarr")
            self.readarr_books_in_library = []
            endpoint_authors = f"{self.readarr_address}/api/v1/author"
            headers = {"Accept": "application/json", "X-Api-Key": self.readarr_api_key}
            response_authors = requests.get(endpoint_authors, headers=headers, timeout=self.readarr_api_timeout)
            if response_authors.status_code != 200:
                raise Exception(f"Failed to fetch authors from Readarr: {response_authors.text}")

            authors = response_authors.json()

            for author in authors:
                author_id = author["id"]
                author_name = author["authorName"]

                # Fetch books by author from Readarr
                endpoint_books = f"{self.readarr_address}/api/v1/book?authorId={author_id}"
                response_books = requests.get(endpoint_books, headers=headers, timeout=self.readarr_api_timeout)
                if response_books.status_code != 200:
                    raise Exception(f"Failed to fetch books by author '{author_name}' from Readarr: {response_books.text}")

                books = response_books.json()

                # Filter books with files
                for book in books:
                    if book.get("statistics", {}).get("bookFileCount", 0) > 0:
                        self.readarr_books_in_library.append({"author": author_name, "title": book.get("title")})
                        book_author_and_title = f'{author_name} - {book.get("title")}'
                        cleaned_book = unidecode(book_author_and_title).lower()
                        self.cleaned_readarr_items.append(cleaned_book)

            self.readarr_items = [{"name": f"{book['author']} - {book['title']}", "checked": checked} for book in self.readarr_books_in_library]

            status = "Success"
            self.readarr_items = sorted(self.readarr_items, key=lambda x: x["name"])

            ret = {"Status": status, "Code": response_books.status_code if status == "Error" else None, "Data": self.readarr_items, "Running": not self.stop_event.is_set()}

        except Exception as e:
            self.diagnostic_logger.error(f"Error Getting Book list from Readarr: {str(e)}")
            ret = {"Status": "Error", "Code": 500, "Data": str(e), "Running": not self.stop_event.is_set()}

        finally:
            socketio.emit("readarr_sidebar_update", ret)

    def find_similar_books(self):
        if self.stop_event.is_set() or self.search_in_progress_flag:
            if self.search_in_progress_flag:
                self.diagnostic_logger.info(f"Searching already in progress")
                socketio.emit("new_toast_msg", {"title": "Search in progress", "message": f"It's just slow...."})
            return
        elif not self.search_exhausted_flag:
            try:
                self.diagnostic_logger.info(f"Searching for new books")
                socketio.emit("new_toast_msg", {"title": "Searching for new books", "message": f"Please be patient...."})

                self.search_exhausted_flag = True
                self.search_in_progress_flag = True
                minimum_count = self.thread_limit if self.thread_limit > 1 and self.thread_limit < 8 else 4
                sample_count = min(minimum_count, len(self.books_to_use_in_search))
                random_books = random.sample(self.books_to_use_in_search, sample_count)
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.thread_limit) as executor:
                    futures = [executor.submit(self.goodreads_scraper.goodreads_recommendations, book_name) for book_name in random_books]
                    for future in concurrent.futures.as_completed(futures):
                        related_books = future.result()
                        new_book_count = 0
                        for book_item in related_books:
                            if self.stop_event.is_set():
                                for f in futures:
                                    f.cancel()
                                break
                            book_author_and_title = f"{book_item['Author']} - {book_item['Name']}"
                            cleaned_book = unidecode(book_author_and_title).lower()
                            if cleaned_book not in self.cleaned_readarr_items:
                                for item in self.recommended_books:
                                    match_ratio = fuzz.ratio(book_author_and_title, f"{item['Author']} - {item['Name']}")
                                    if match_ratio > 95:
                                        break
                                else:
                                    self.recommended_books.append(book_item)
                                    socketio.emit("more_books_loaded", [book_item])
                                    self.search_exhausted_flag = False
                                    new_book_count += 1

                    if new_book_count > 0:
                        self.diagnostic_logger.info(f"Found {new_book_count} new suggestions that are not already in Readarr")

                if self.search_exhausted_flag:
                    self.diagnostic_logger.info("Search Exhausted - Try selecting more books from existing Readarr library")
                    socketio.emit("new_toast_msg", {"title": "Search Exhausted", "message": "Try selecting more books from existing Readarr library"})

            except Exception as e:
                self.diagnostic_logger.error(f"Failure Scraping Goodreads: {str(e)}")
                socketio.emit("new_toast_msg", {"title": "Search Failed", "message": "Check Logs...."})

            finally:
                self.search_in_progress_flag = False
                self.diagnostic_logger.info(f"Finished Searching")

        elif self.search_exhausted_flag:
            try:
                self.search_in_progress_flag = True
                self.diagnostic_logger.info("Search Exhausted - Try selecting more books from existing Readarr library")
                socketio.emit("new_toast_msg", {"title": "Search Exhausted", "message": "Try selecting more books from existing Readarr library"})
                time.sleep(2)

            except Exception as e:
                self.diagnostic_logger.error(f"Search Exhausted Error: {str(e)}")

            finally:
                self.search_in_progress_flag = False
                self.diagnostic_logger.info(f"Finished Searching")

    def add_to_readarr(self, book_data):
        try:
            book_name = book_data["Name"]
            author_name = book_data["Author"]
            book_author_and_title = f"{author_name} - {book_name}"
            author_data = self._readarr_author_lookup(author_name)
            status = self._readarr_book_lookup(author_data, book_name)

            if status == "Success":
                self.readarr_items.append({"name": book_author_and_title, "checked": False})
                cleaned_book = unidecode(book_author_and_title).lower()
                self.cleaned_readarr_items.append(cleaned_book)
                self.diagnostic_logger.info(f"Book: {book_author_and_title} successfully added to Readarr.")
                status = "Added"
            else:
                status = "Failed to Add"
                self.diagnostic_logger.info(f"Failed to add to Readarr as no matching book for: {book_author_and_title}.")
                socketio.emit("new_toast_msg", {"title": "Failed to add Book", "message": f"No Matching Book for: {book_author_and_title}"})

            for item in self.recommended_books:
                if item["Name"] == book_name and item["Author"] == author_name:
                    item["Status"] = status
                    socketio.emit("refresh_book", item)
                    break
            else:
                self.diagnostic_logger.info(f"{item['Author']} - {item['Name']} not found in Similar Book List")

        except Exception as e:
            self.diagnostic_logger.error(f"Error Adding Book to Readarr: {str(e)}")

    def _readarr_book_lookup(self, author_data, book_name):
        try:
            time.sleep(self.readarr_wait_delay)
            headers = {"Content-Type": "application/json", "X-Api-Key": self.readarr_api_key}
            readarr_book_url = f"{self.readarr_address}/api/v1/book"
            readarr_book_monitor_url = f"{self.readarr_address}/api/v1/book/monitor"

            author_books_response = requests.get(f"{readarr_book_url}?authorId={author_data.get('id')}", headers=headers)
            if author_books_response.status_code != 200:
                raise Exception(f"Failed to get books from author: {author_books_response.content.decode('utf-8')}")

            # Find a match for the requested book
            author_books_data = author_books_response.json()
            for book_item in author_books_data:
                match_ratio = fuzz.ratio(book_item["title"], book_name)
                if match_ratio > 90:
                    book_data = book_item
                    break
            else:
                raise Exception(f"Book: {book_name} not found in Readarr under author: {author_data.get('authorName')}.")

            payload = {"bookIds": [book_data.get("id")], "monitored": True}
            response = requests.put(readarr_book_monitor_url, headers=headers, json=payload)
            if response.status_code == 202:
                self.diagnostic_logger.info(f"Book: {book_name} monitoring status updated successfully.")
                return "Success"
            else:
                self.diagnostic_logger.error(f"Failed to update monitoring status for Book: {book_name}. Error: {response.content.decode('utf-8')}")
                return "Failure"

        except Exception as e:
            self.diagnostic_logger.error(f"Book not added Readarr: {str(e)}")
            return "Failure"

    def _readarr_author_lookup(self, author_name):
        readarr_author_lookup_url = f"{self.readarr_address}/api/v1/author/lookup"
        readarr_author_url = f"{self.readarr_address}/api/v1/author"
        params = {"term": author_name}
        headers = {"Content-Type": "application/json", "X-Api-Key": self.readarr_api_key}

        # Check if the author exists in Readarr
        author_response = requests.get(readarr_author_url, headers=headers)
        authors = author_response.json()

        if author_response.status_code == 200:
            for author in authors:
                match_ratio = fuzz.ratio(author["authorName"], author_name)
                if match_ratio > 95:
                    author_data = author
                    break
            else:
                author_data = None

        if not author_data:
            # Search for Author
            author_lookup = requests.get(readarr_author_lookup_url, params=params, headers=headers)
            if author_lookup.status_code != 200:
                raise Exception(f"Readarr Lookup failed: {author_lookup.content.decode('utf-8')}")

            search_results = author_lookup.json()
            for result in search_results:
                match_ratio = fuzz.ratio(result["authorName"], author_name)
                if match_ratio > 95:
                    author_data = result
                    break
            else:
                raise Exception(f"No match for: {author_name}")

            # Add Author as not in Readdar
            author_payload = {
                "authorName": author_data.get("authorName"),
                "metadataProfileId": self.metadata_profile_id,
                "qualityProfileId": self.quality_profile_id,
                "rootFolderPath": self.root_folder_path,
                "path": os.path.join(self.root_folder_path, author_data.get("authorName")),
                "foreignAuthorId": author_data.get("foreignAuthorId"),
                "monitored": True,
                "monitorNewItems": "none",
                "addOptions": {
                    "monitor": "future",
                    "searchForMissingBooks": self.search_for_missing_book,
                    "monitored": True,
                },
            }
            author_response = requests.post(readarr_author_url, headers=headers, json=author_payload)
            author_data = author_response.json()
            if author_response.status_code != 201:
                raise Exception(f"Failed to add author: {author_response.content.decode('utf-8')}")

        return author_data

    def load_settings(self):
        try:
            data = {
                "readarr_address": self.readarr_address,
                "readarr_api_key": self.readarr_api_key,
                "root_folder_path": self.root_folder_path,
                "google_books_api_key": self.google_books_api_key,
            }
            socketio.emit("settings_loaded", data)
        except Exception as e:
            self.diagnostic_logger.error(f"Failed to load settings: {str(e)}")

    def update_settings(self, data):
        try:
            self.readarr_address = data["readarr_address"]
            self.readarr_api_key = data["readarr_api_key"]
            self.root_folder_path = data["root_folder_path"]
            self.google_books_api_key = data["google_books_api_key"]
        except Exception as e:
            self.diagnostic_logger.error(f"Failed to update settings: {str(e)}")

    def save_config_to_file(self):
        try:
            with open(self.settings_config_file, "w") as json_file:
                json.dump(
                    {
                        "readarr_address": self.readarr_address,
                        "readarr_api_key": self.readarr_api_key,
                        "root_folder_path": self.root_folder_path,
                        "google_books_api_key": self.google_books_api_key,
                        "readarr_api_timeout": float(self.readarr_api_timeout),
                        "quality_profile_id": self.quality_profile_id,
                        "metadata_profile_id": self.metadata_profile_id,
                        "search_for_missing_book": self.search_for_missing_book,
                        "minimum_rating": self.minimum_rating,
                        "minimum_votes": self.minimum_votes,
                        "goodreads_wait_delay": self.goodreads_wait_delay,
                        "readarr_wait_delay": self.readarr_wait_delay,
                        "thread_limit": self.thread_limit,
                        "auto_start": self.auto_start,
                        "auto_start_delay": self.auto_start_delay,
                    },
                    json_file,
                    indent=4,
                )

        except Exception as e:
            self.diagnostic_logger.error(f"Error Saving Config: {str(e)}")

    def query_google_books(self, book):
        try:
            book_info = {}
            url = "https://www.googleapis.com/books/v1/volumes"
            query = f'{book["Author"]} - {book["Name"]}'
            params = {"q": query.replace(" ", "+"), "key": self.google_books_api_key}
            response = requests.get(url, params=params)
            data = response.json()
            if "items" in data:
                for book_item in data["items"]:
                    book_info = book_item["volumeInfo"]
                    title = book_info.get("title", "Title not available")
                    author = book_info.get("authors", ["No Author Found"])[0]

                    book_string = f"{author} - {title}"
                    match_ratio = fuzz.ratio(book_string, query)
                    if match_ratio > 90 or query in book_string:
                        break

        except Exception as e:
            self.diagnostic_logger.error(f"Error retrieving book Data from Google Books API: {str(e)}")

        finally:
            return book_info

    def overview(self, book):
        try:
            book_info = self.query_google_books(book)
            book["Overview"] = book_info.get("description", "")
            book["Published_Date"] = book_info.get("publishedDate")
            book["Page_Count"] = book_info.get("pageCount")

        except Exception as e:
            self.diagnostic_logger.error(f"Error retrieving book overview: {str(e)}")

        finally:
            socketio.emit("overview", book, room=request.sid)


app = Flask(__name__)
app.secret_key = "secret_key"
socketio = SocketIO(app)
data_handler = DataHandler()


@app.route("/")
def home():
    return render_template("base.html")


@socketio.on("side_bar_opened")
def side_bar_opened():
    if data_handler.readarr_items:
        ret = {"Status": "Success", "Data": data_handler.readarr_items, "Running": not data_handler.stop_event.is_set()}
        socketio.emit("readarr_sidebar_update", ret)


@socketio.on("get_readarr_books")
def get_readarr_books():
    thread = threading.Thread(target=data_handler.request_books_from_readarr, name="Readarr_Thread")
    thread.daemon = True
    thread.start()


@socketio.on("adder")
def add_to_readarr(book):
    thread = threading.Thread(target=data_handler.add_to_readarr, args=(book,), name="Add_Book_Thread")
    thread.daemon = True
    thread.start()


@socketio.on("connect")
def connection():
    thread = threading.Thread(target=data_handler.connection, name="Connect")
    thread.daemon = True
    thread.start()


@socketio.on("disconnect")
def disconnection():
    data_handler.disconnection()


@socketio.on("load_settings")
def load_settings():
    data_handler.load_settings()


@socketio.on("update_settings")
def update_settings(data):
    data_handler.update_settings(data)
    data_handler.save_config_to_file()


@socketio.on("start_req")
def starter(data):
    data_handler.start(data)


@socketio.on("stop_req")
def stopper():
    data_handler.stop_event.set()


@socketio.on("load_more_books")
def load_more_books():
    thread = threading.Thread(target=data_handler.find_similar_books, name="Find_Similar")
    thread.daemon = True
    thread.start()


@socketio.on("overview_req")
def overview(book):
    data_handler.overview(book)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
