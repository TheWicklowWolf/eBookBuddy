![Build Status](https://github.com/TheWicklowWolf/ebookbuddy/actions/workflows/main.yml/badge.svg)
![Docker Pulls](https://img.shields.io/docker/pulls/thewicklowwolf/ebookbuddy.svg)



<img src="/src/static/ebookbuddy.png" alt="image">


Book discovery tool that provides recommendations based on selected Readarr books. 


## Run using docker-compose

```yaml
services:
  ebookbuddy:
    image: thewicklowwolf/ebookbuddy:latest
    container_name: ebookbuddy
    volumes:
      - /path/to/config:/ebookbuddy/config
      - /etc/localtime:/etc/localtime:ro
    ports:
      - 5000:5000
    restart: unless-stopped
```

## Configuration via environment variables

Certain values can be set via environment variables:

* __PUID__: The user ID to run the app with. Defaults to `1000`. 
* __PGID__: The group ID to run the app with. Defaults to `1000`.
* __readarr_address__: The URL for Readarr. Defaults to `http://192.168.1.2:8787`.
* __readarr_api_key__: The API key for Readarr. Defaults to ``.
* __root_folder_path__: The root folder path for Books. Defaults to `/data/media/books/`.
* __google_books_api_key__: The API key for Google Books. Defaults to ``.
* __readarr_api_timeout__: Timeout duration for Readarr API calls. Defaults to `120`.
* __quality_profile_id__: Quality Profile ID in Readarr. Defaults to `1`.
* __metadata_profile_id__: Metadata Profile ID in Readarr. Defaults to `1`
* __search_for_missing_book__: Whether to start searching for book when adding. Defaults to `False`
* __minimum_rating__: Minimum Movie Rating. Defaults to `3.5`.
* __minimum_votes__: Minimum Vote Count. Defaults to `500`.
* __goodreads_wait_delay__: Delay to allow for slow data retrieval from GoodReads. Defaults to `12.5`.
* __readarr_wait_delay__: Delay to allow for slow data retrieval from GoodReads. Defaults to `7.5`.
* __thread_limit__: Max number of concurrent threads to use for data retrieval. Defaults to `1`.
* __auto_start__: Whether to run automatically at startup. Defaults to `False`.
* __auto_start_delay__: Delay duration for Auto Start in Seconds (if enabled). Defaults to `60`.

---


<img src="/src/static/light.png" alt="image">



<img src="/src/static/dark.png" alt="image">

---

https://hub.docker.com/r/thewicklowwolf/ebookbuddy
