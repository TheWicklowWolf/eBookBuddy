var return_to_top = document.getElementById("return-to-top");
var readarr_get_books_button = document.getElementById('readarr-get-books-button');
var start_stop_button = document.getElementById('start-stop-button');
var readarr_status = document.getElementById('readarr-status');
var readarr_spinner = document.getElementById('readarr-spinner');
var readarr_item_list = document.getElementById("readarr-item-list");
var readarr_select_all_checkbox = document.getElementById("readarr-select-all");
var readarr_select_all_container = document.getElementById("readarr-select-all-container");
var config_modal = document.getElementById('config-modal');
var readarr_sidebar = document.getElementById('readarr-sidebar');
var save_message = document.getElementById("save-message");
var save_changes_button = document.getElementById("save-changes-button");
const readarr_address = document.getElementById("readarr-address");
const readarr_api_key = document.getElementById("readarr-api-key");
const root_folder_path = document.getElementById("root-folder-path");
const google_books_api_key = document.getElementById("googlebooks-api-key");
var readarr_items = [];
var socket = io();

function check_if_all_selected() {
    var checkboxes = document.querySelectorAll('input[name="readarr-item"]');
    var all_checked = true;
    for (var i = 0; i < checkboxes.length; i++) {
        if (!checkboxes[i].checked) {
            all_checked = false;
            break;
        }
    }
    readarr_select_all_checkbox.checked = all_checked;
}

function load_readarr_data(response) {
    var every_check_box = document.querySelectorAll('input[name="readarr-item"]');
    if (response.Running) {
        start_stop_button.classList.remove('btn-success');
        start_stop_button.classList.add('btn-warning');
        start_stop_button.textContent = "Stop";
        every_check_box.forEach(item => {
            item.disabled = true;
        });
        readarr_select_all_checkbox.disabled = true;
        readarr_get_books_button.disabled = true;
    } else {
        start_stop_button.classList.add('btn-success');
        start_stop_button.classList.remove('btn-warning');
        start_stop_button.textContent = "Start";
        every_check_box.forEach(item => {
            item.disabled = false;
        });
        readarr_select_all_checkbox.disabled = false;
        readarr_get_books_button.disabled = false;
    }
    check_if_all_selected();
}

function append_books(books) {
    var book_row = document.getElementById('book-row');
    var template = document.getElementById('book-template');
    books.forEach(function (book) {
        var clone = document.importNode(template.content, true);
        var book_col = clone.querySelector('#book-column');

        book_col.querySelector('.card-title').textContent = `${book.Name}`;
        if (book.Image_Link) {
            book_col.querySelector('.card-img-top').src = book.Image_Link;
            book_col.querySelector('.card-img-top').alt = book.Name;
        } else {
            book_col.querySelector('.book-img-container').removeChild(book_col.querySelector('.card-img-top'));
        }
        book_col.querySelector('.add-to-readarr-btn').addEventListener('click', function () {
            var add_button = this;
            add_button.disabled = true;
            add_button.textContent = "Adding...";
            add_to_readarr(book);
        });
        book_col.querySelector('.get-overview-btn').addEventListener('click', function () {
            var overview_button = this;
            overview_button.disabled = true;
            overview_req(book, overview_button);
        });
        book_col.querySelector('.votes').textContent = book.Votes;
        book_col.querySelector('.rating').textContent = book.Rating;

        var add_button = book_col.querySelector('.add-to-readarr-btn');
        if (book.Status === "Added" || book.Status === "Already in Readarr") {
            book_col.querySelector('.card-body').classList.add('status-green');
            add_button.classList.remove('btn-primary');
            add_button.classList.add('btn-secondary');
            add_button.disabled = true;
            add_button.textContent = book.Status;
        } else if (book.Status === "Failed to Add" || book.Status === "Invalid Path" || book.Status === "Invalid Book ID") {
            book_col.querySelector('.card-body').classList.add('status-red');
            add_button.classList.remove('btn-primary');
            add_button.classList.add('btn-danger');
            add_button.disabled = true;
            add_button.textContent = book.Status;
        } else {
            book_col.querySelector('.card-body').classList.add('status-blue');
        }
        book_row.appendChild(clone);
    });
}

function add_to_readarr(book) {
    if (socket.connected) {
        socket.emit("adder", book);
    }
    else {
        book_toast("Connection Lost", "Please reload to continue.");
    }
}

function book_toast(header, message) {
    var toast_container = document.querySelector('.toast-container');
    var toast_template = document.getElementById('toast-template').cloneNode(true);
    toast_template.classList.remove('d-none');

    toast_template.querySelector('.toast-header strong').textContent = header;
    toast_template.querySelector('.toast-body').textContent = message;
    toast_template.querySelector('.text-muted').textContent = new Date().toLocaleString();

    toast_container.appendChild(toast_template);
    var toast = new bootstrap.Toast(toast_template);
    toast.show();
    toast_template.addEventListener('hidden.bs.toast', function () {
        toast_template.remove();
    });
}

return_to_top.addEventListener("click", function () {
    window.scrollTo({ top: 0, behavior: "smooth" });
});

readarr_select_all_checkbox.addEventListener("change", function () {
    var is_checked = this.checked;
    var checkboxes = document.querySelectorAll('input[name="readarr-item"]');
    checkboxes.forEach(function (checkbox) {
        checkbox.checked = is_checked;
    });
});

readarr_get_books_button.addEventListener('click', function () {
    readarr_get_books_button.disabled = true;
    readarr_spinner.classList.remove('d-none');
    readarr_status.textContent = "Accessing Readarr API";
    readarr_item_list.innerHTML = '';
    socket.emit("get_readarr_books");
});

start_stop_button.addEventListener('click', function () {
    var running_state = start_stop_button.textContent.trim() === "Start" ? true : false;
    if (running_state) {
        start_stop_button.classList.remove('btn-success');
        start_stop_button.classList.add('btn-warning');
        start_stop_button.textContent = "Stop";
        var checked_items = Array.from(document.querySelectorAll('input[name="readarr-item"]:checked'))
            .map(item => item.value);
        document.querySelectorAll('input[name="readarr-item"]').forEach(item => {
            item.disabled = true;
        });
        readarr_get_books_button.disabled = true;
        readarr_select_all_checkbox.disabled = true;
        socket.emit("start_req", checked_items);
    }
    else {
        start_stop_button.classList.add('btn-success');
        start_stop_button.classList.remove('btn-warning');
        start_stop_button.textContent = "Start";
        document.querySelectorAll('input[name="readarr-item"]').forEach(item => {
            item.disabled = false;
        });
        readarr_get_books_button.disabled = false;
        readarr_select_all_checkbox.disabled = false;
        socket.emit("stop_req");
    }
});

save_changes_button.addEventListener("click", () => {
    socket.emit("update_settings", {
        "readarr_address": readarr_address.value,
        "readarr_api_key": readarr_api_key.value,
        "root_folder_path": root_folder_path.value,
        "google_books_api_key": google_books_api_key.value,
    });
    save_message.style.display = "block";
    setTimeout(function () {
        save_message.style.display = "none";
    }, 1000);
});

config_modal.addEventListener('show.bs.modal', function (event) {
    socket.emit("load_settings");

    function handle_settings_loaded(settings) {
        readarr_address.value = settings.readarr_address;
        readarr_api_key.value = settings.readarr_api_key;
        root_folder_path.value = settings.root_folder_path;
        google_books_api_key.value = settings.google_books_api_key;
        socket.off("settings_loaded", handle_settings_loaded);
    }
    socket.on("settings_loaded", handle_settings_loaded);
});

readarr_sidebar.addEventListener('show.bs.offcanvas', function (event) {
    socket.emit("side_bar_opened");
});

window.addEventListener('scroll', function () {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight) {
        load_more_books_req();
    }
});

window.addEventListener('touchmove', function () {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight) {
        load_more_books_req();
    }
});

window.addEventListener('touchend', () => {
    const { scrollHeight, scrollTop, clientHeight } = document.documentElement;
    if (Math.abs(scrollHeight - clientHeight - scrollTop) < 1) {
        load_more_books_req();
    }
});

socket.on("readarr_sidebar_update", (response) => {
    if (response.Status == "Success") {
        readarr_status.textContent = "Readarr List Retrieved";
        readarr_items = response.Data;
        readarr_item_list.innerHTML = '';
        readarr_select_all_container.classList.remove('d-none');

        for (var i = 0; i < readarr_items.length; i++) {
            var item = readarr_items[i];

            var div = document.createElement("div");
            div.className = "form-check";

            var input = document.createElement("input");
            input.type = "checkbox";
            input.className = "form-check-input";
            input.id = "readarr-" + i;
            input.name = "readarr-item";
            input.value = item.name;

            if (item.checked) {
                input.checked = true;
            }

            var label = document.createElement("label");
            label.className = "form-check-label";
            label.htmlFor = "readarr-" + i;
            label.textContent = item.name;

            input.addEventListener("change", function () {
                check_if_all_selected();
            });

            div.appendChild(input);
            div.appendChild(label);

            readarr_item_list.appendChild(div);
        }
    }
    else {
        readarr_status.textContent = response.Code;
    }
    readarr_get_books_button.disabled = false;
    readarr_spinner.classList.add('d-none');
    load_readarr_data(response);
});

socket.on("refresh_book", (book) => {
    var book_cards = document.querySelectorAll('#book-column');
    book_cards.forEach(function (card) {
        var card_body = card.querySelector('.card-body');
        var card_book_name = card_body.querySelector('.card-title').textContent.trim();
        card_book_name = card_book_name.replace(/\s*\(\d{4}\)$/, "");
        if (card_book_name === book.Name) {
            card_body.classList.remove('status-green', 'status-red', 'status-blue');

            var add_button = card_body.querySelector('.add-to-readarr-btn');

            if (book.Status === "Added" || book.Status === "Already in Readarr") {
                card_body.classList.add('status-green');
                add_button.classList.remove('btn-primary');
                add_button.classList.add('btn-secondary');
                add_button.disabled = true;
                add_button.textContent = book.Status;
            } else if (book.Status === "Failed to Add" || book.Status === "Invalid Path") {
                card_body.classList.add('status-red');
                add_button.classList.remove('btn-primary');
                add_button.classList.add('btn-danger');
                add_button.disabled = true;
                add_button.textContent = book.Status;
            } else {
                card_body.classList.add('status-blue');
                add_button.disabled = false;
            }
            return;
        }
    });
});

socket.on('more_books_loaded', function (data) {
    append_books(data);
});

socket.on('clear', function () {
    var book_row = document.getElementById('book-row');
    var book_cards = book_row.querySelectorAll('#book-column');
    book_cards.forEach(function (card) {
        card.remove();
    });
});

socket.on("new_toast_msg", function (data) {
    book_toast(data.title, data.message);
});

socket.on("disconnect", function () {
    book_toast("Connection Lost", "Please reconnect to continue.");
});

let overview_request_flag = false;

function overview_req(book, overview_button) {
    if (!overview_request_flag) {
        overview_request_flag = true;
        socket.emit("overview_req", book);
        setTimeout(() => {
            overview_request_flag = false;
            overview_button.disabled = false;
        }, 2000);
    }
}

let load_more_request_flag = false;
function load_more_books_req() {
    if (!load_more_request_flag) {
        load_more_request_flag = true;
        socket.emit("load_more_books");
        setTimeout(() => {
            load_more_request_flag = false;
        }, 1000);
    }
}

function book_overview_modal(book) {
    const scrollbar_width = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.overflow = 'hidden';
    document.body.style.paddingRight = `${scrollbar_width}px`;

    var modal_title = document.getElementById('overview-modal-title');
    var modal_body = document.getElementById('modal-body');

    modal_title.textContent = `${book.Author} - ${book.Name}`;
    modal_body.innerHTML = `${book.Overview}<br><br>Published Date: ${book.Published_Date}<br>Page Count: ${book.Page_Count}<br><br>Recommendation from: ${book.Base_Book}`;

    var overview_modal = new bootstrap.Modal(document.getElementById('overview-modal'));
    overview_modal.show();

    overview_modal._element.addEventListener('hidden.bs.modal', function () {
        document.body.style.overflow = 'auto';
        document.body.style.paddingRight = '0';
    });
}

socket.on("overview", function (book) {
    book_overview_modal(book);
});

const theme_switch = document.getElementById('theme-switch');
const saved_theme = localStorage.getItem('theme');
const saved_switch_position = localStorage.getItem('switch-position');

if (saved_switch_position) {
    theme_switch.checked = saved_switch_position === 'true';
}

if (saved_theme) {
    document.documentElement.setAttribute('data-bs-theme', saved_theme);
}

theme_switch.addEventListener('click', () => {
    if (document.documentElement.getAttribute('data-bs-theme') === 'dark') {
        document.documentElement.setAttribute('data-bs-theme', 'light');
    } else {
        document.documentElement.setAttribute('data-bs-theme', 'dark');
    }
    localStorage.setItem('theme', document.documentElement.getAttribute('data-bs-theme'));
    localStorage.setItem('switch_position', theme_switch.checked);
});
