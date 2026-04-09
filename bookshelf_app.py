import tkinter as tk
from tkinter import messagebox, filedialog
import random
import os
import json
import shutil

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# =============================================================================
# PATHS
# All paths are built relative to wherever bookshelf_app.py lives on disk.
# The data/ folder and data/covers/ folder sit right next to the script.
# =============================================================================

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
COVERS_DIR = os.path.join(DATA_DIR, "covers")
DB_PATH    = os.path.join(DATA_DIR, "books.json")

os.makedirs(COVERS_DIR, exist_ok=True)

print("Script folder :", BASE_DIR)
print("Database      :", DB_PATH)


# =============================================================================
# DATABASE
# books.json stores each book's title, synopsis, color, and cover filename.
# Cover is stored as JUST the filename (e.g. "Six of Crows.jpg") so the
# database works even if the folder is moved. The app rebuilds the full
# absolute path at runtime by joining it with COVERS_DIR.
# =============================================================================

def load_books():
    """Reads books.json and returns the books dictionary. Each cover value
    is converted from a plain filename into a full absolute path so the
    rest of the app can open the file directly."""
    if not os.path.isfile(DB_PATH):
        print("No database found — starting fresh.")
        return {}

    with open(DB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    for info in data.values():
        filename = info.get("cover")
        if filename:
            # Build the full path: data/covers/Six of Crows.jpg
            info["cover"] = os.path.join(COVERS_DIR, filename)

    print(f"Loaded {len(data)} books from database.")
    return data


def save_books():
    """Writes the books dictionary to books.json. Converts each cover's
    absolute path back to just the filename before saving so the file is
    portable across different computers and folder locations."""
    saveable = {}
    for title, info in books.items():
        entry = dict(info)
        cover = entry.get("cover")
        if cover:
            # Store only the filename, not the full path
            entry["cover"] = os.path.basename(cover)
        saveable[title] = entry

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(saveable, f, indent=4, ensure_ascii=False)

    print(f"Saved {len(saveable)} books to {DB_PATH}")


def copy_cover_to_data(title, src_path):
    """Copies the chosen image file into data/covers/ using the book title
    as the filename. Returns the full absolute path of the saved copy."""
    ext  = os.path.splitext(src_path)[1].lower()
    safe = "".join(c for c in title if c.isalnum() or c in " _-").strip()
    dest = os.path.join(COVERS_DIR, safe + ext)
    shutil.copy2(src_path, dest)
    print(f"Cover saved: {dest}")
    return dest


# =============================================================================
# VISUAL CONSTANTS
# =============================================================================

SPINE_COLORS = [
    "#B5451B", "#1A5276", "#117A65", "#6C3483",
    "#B7770D", "#1A6B5A", "#7B241C", "#1F618D",
    "#884EA0", "#196F3D", "#922B21", "#D35400",
    "#154360", "#6E2F2F", "#0E6655", "#7D6608",
]

BOOKS_PER_ROW   = 10
NUM_SHELVES     = 6
SHELF_H         = 160
SHELF_BOARD     = 18
SPINE_FONT_SIZE = 9
SPINE_BASE_W    = 30
CHARS_PER_LINE  = 10
PADDING_X       = 6
SHELF_PADDING   = 14

# Stores Tkinter PhotoImage objects — they must stay in memory or images vanish
_photo_refs = {}

# Load all books from disk on startup
books = load_books()


# =============================================================================
# COLOR AND SPINE SIZE HELPERS
# =============================================================================

def get_color(title):
    """Returns the saved spine color for this book. If none is saved yet,
    picks a random color that isn't already used and saves it."""
    if not books[title].get("color"):
        used = {books[t].get("color") for t in books}
        pool = [c for c in SPINE_COLORS if c not in used] or SPINE_COLORS
        books[title]["color"] = random.choice(pool)
        save_books()
    return books[title]["color"]


def spine_width(title):
    """Returns the pixel width for a book spine. Short titles get a narrow
    spine; longer titles that need two lines get a wider one."""
    lines = 1 if len(title) <= CHARS_PER_LINE else 2
    return SPINE_BASE_W + (lines - 1) * (SPINE_FONT_SIZE + 10)


def _lighten(color):
    r, g, b = _parse(color)
    return f"#{min(255,r+45):02X}{min(255,g+45):02X}{min(255,b+45):02X}"

def _darken(color):
    r, g, b = _parse(color)
    return f"#{max(0,r-45):02X}{max(0,g-45):02X}{max(0,b-45):02X}"

def _parse(color):
    h = color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# =============================================================================
# FLAT BUTTON
# macOS ignores background colors on regular tk.Button widgets no matter what.
# This class draws a colored rectangle on a Canvas instead — works everywhere.
# =============================================================================

class FlatButton(tk.Canvas):
    """A properly colored clickable button built on Canvas instead of tk.Button."""

    def __init__(self, parent, text, command, bg, hover,
                 fg="white", font=("Georgia", 10, "bold"),
                 padx=20, pady=8, **kwargs):
        super().__init__(parent, highlightthickness=0, bd=0,
                         cursor="hand2", **kwargs)
        self._bg      = bg
        self._command = command

        tmp = tk.Label(font=font, text=text)
        tw  = tmp.winfo_reqwidth()  + padx * 2
        th  = tmp.winfo_reqheight() + pady * 2
        tmp.destroy()

        self.configure(width=tw, height=th, bg=parent["bg"])
        self._rect = self.create_rectangle(0, 0, tw, th, fill=bg,
                                            outline="", tags="b")
        self._lbl  = self.create_text(tw // 2, th // 2, text=text,
                                       fill=fg, font=font, tags="b")

        self.tag_bind("b", "<Enter>",
                      lambda _: self.itemconfig(self._rect, fill=hover))
        self.tag_bind("b", "<Leave>",
                      lambda _: self.itemconfig(self._rect, fill=bg))
        self.tag_bind("b", "<Button-1>",
                      lambda _: command() if command else None)

    def set_text(self, text):
        """Changes the label shown on the button."""
        self.itemconfig(self._lbl, text=text)


# =============================================================================
# BOOK DETAIL WINDOW
# Opens when the user clicks a spine. Shows the cover image (if any),
# synopsis, an upload cover button, and a delete button.
# =============================================================================

def open_book(title):
    """Opens the detail popup for the clicked book."""
    info     = books[title]
    synopsis = info["synopsis"]
    cover    = info.get("cover")   # absolute path or None

    win = tk.Toplevel(root)
    win.title(title)
    win.configure(bg="#2B1B0E")
    win.resizable(False, False)

    # Colored stripe at top matching the spine color
    tk.Frame(win, bg=get_color(title), height=10).pack(fill="x")

    inner = tk.Frame(win, bg="#FFF8EE", padx=32, pady=24)
    inner.pack(fill="both", expand=True)

    tk.Label(inner, text=title, font=("Georgia", 16, "bold"),
             bg="#FFF8EE", fg="#2B1B0E",
             wraplength=420, justify="left").pack(anchor="w", pady=(0, 10))

    tk.Frame(inner, bg="#C8A97E", height=2).pack(fill="x", pady=(0, 16))

    # Centered frame that holds the cover image and upload button
    cover_frame = tk.Frame(inner, bg="#FFF8EE")
    cover_frame.pack(pady=(0, 14))

    img_label_ref = [None]   # will hold the Label widget once created
    btn_ref       = [None]   # will hold the FlatButton once created

    def show_image(abs_path):
        """Loads an image from disk, resizes it, and displays it in the window.
        Updates the button text to 'Change Cover' once shown."""
        try:
            img = Image.open(abs_path)
            img.thumbnail((150, 210), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            _photo_refs[title] = photo   # must keep this or the image disappears
            if img_label_ref[0] is not None:
                img_label_ref[0].configure(image=photo)
            else:
                lbl = tk.Label(cover_frame, image=photo,
                               bg="#FFF8EE", relief="flat", bd=0)
                lbl.pack(pady=(0, 8))
                img_label_ref[0] = lbl
            if btn_ref[0] is not None:
                btn_ref[0].set_text("Change Cover")
        except Exception as e:
            messagebox.showerror("Image error", str(e), parent=win)

    # Show the existing cover right away if one is saved for this book
    if cover and PIL_AVAILABLE and os.path.isfile(cover):
        show_image(cover)

    def upload_cover():
        """Opens a file picker so the user can choose a cover image.
        Copies it into data/covers/, saves the path to books.json,
        and shows the image in the window immediately."""
        path = filedialog.askopenfilename(
            parent=win,
            title="Choose a cover image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif *.bmp *.webp"),
                       ("All files", "*.*")]
        )
        if not path:
            return

        dest = copy_cover_to_data(title, path)   # copies image into data/covers/
        books[title]["cover"] = dest              # update the in-memory dictionary
        save_books()                              # write change to books.json on disk

        if PIL_AVAILABLE:
            show_image(dest)
        elif btn_ref[0]:
            btn_ref[0].set_text("Cover saved!")

    # Create the upload button — label depends on whether a cover already exists
    has_cover = bool(cover and PIL_AVAILABLE and os.path.isfile(cover))
    btn = FlatButton(cover_frame,
                     text="Change Cover" if has_cover else "Upload Cover",
                     command=upload_cover,
                     bg="#7B5C3A", hover="#9C7248",
                     padx=14, pady=6,
                     font=("Georgia", 9, "bold"))
    btn.pack()
    btn_ref[0] = btn   # store reference so show_image can update the label

    tk.Label(inner, text=synopsis, font=("Georgia", 11),
             bg="#FFF8EE", fg="#3D2B1F",
             wraplength=420, justify="left").pack(anchor="w", pady=(14, 0))

    btn_row = tk.Frame(inner, bg="#FFF8EE")
    btn_row.pack(pady=(24, 4), fill="x")

    FlatButton(btn_row, text="Close", command=win.destroy,
               bg="#5D4037", hover="#3E2723",
               padx=20, pady=7).pack(side="left", padx=(0, 10))

    def delete_book():
        """Asks for confirmation then removes the book from memory and disk."""
        if messagebox.askyesno("Delete book",
                               f'Remove "{title}" from your shelf?',
                               parent=win):
            books.pop(title, None)
            _photo_refs.pop(title, None)
            save_books()
            win.destroy()
            render_shelf()

    FlatButton(btn_row, text="Delete Book", command=delete_book,
               bg="#922B21", hover="#6E2014",
               padx=20, pady=7).pack(side="left")

    win.update_idletasks()
    w = win.winfo_width()
    h = win.winfo_height()
    x = root.winfo_x() + (root.winfo_width()  - w) // 2
    y = root.winfo_y() + (root.winfo_height() - h) // 2
    win.geometry(f"+{x}+{y}")


# =============================================================================
# SHELF RENDERER
# Draws the entire bookshelf — wall, planks, and all book spines — from scratch.
# =============================================================================

def render_shelf():
    """Clears the canvas and redraws everything: wall texture, wooden planks,
    and every book spine with its title text."""
    shelf_canvas.delete("all")

    cw = shelf_canvas.winfo_width()
    if cw < 50:
        cw = 740

    total_h = NUM_SHELVES * (SHELF_H + SHELF_BOARD) + 20
    shelf_canvas.configure(scrollregion=(0, 0, cw, total_h))

    # Wall background with subtle horizontal stripes
    shelf_canvas.create_rectangle(0, 0, cw, total_h, fill="#E8D5B0", outline="")
    for y in range(0, total_h, 40):
        shelf_canvas.create_line(0, y, cw, y, fill="#D9C49E", width=1)

    book_list  = list(books.items())
    book_index = 0

    for shelf_num in range(NUM_SHELVES):
        y_top    = shelf_num * (SHELF_H + SHELF_BOARD) + 10
        y_bottom = y_top + SHELF_H
        y_plank  = y_bottom
        y_plank2 = y_plank + SHELF_BOARD

        # Draw the wooden shelf plank with highlight and shadow
        shelf_canvas.create_rectangle(0, y_plank, cw, y_plank2,
                                       fill="#9C7248", outline="")
        shelf_canvas.create_rectangle(0, y_plank, cw, y_plank + 3,
                                       fill="#B8925A", outline="")
        shelf_canvas.create_rectangle(0, y_plank2 - 3, cw, y_plank2,
                                       fill="#7B5C3A", outline="")
        for gx in range(0, cw, 80):
            off = random.randint(-6, 6)
            shelf_canvas.create_line(gx + off, y_plank, gx + off + 20, y_plank2,
                                      fill="#7B5C3A", width=1)

        row_books  = book_list[book_index: book_index + BOOKS_PER_ROW]
        book_index += len(row_books)

        x = SHELF_PADDING
        for (title, data) in row_books:
            sw    = spine_width(title)
            sh    = SHELF_H - 10
            sy    = y_top + (SHELF_H - sh)
            color = get_color(title)

            # Spine: colored body with lighter left edge and darker right edge
            shelf_canvas.create_rectangle(x, sy, x + sw, y_bottom,
                                           fill=color, outline="#1A0A00", width=1)
            shelf_canvas.create_rectangle(x, sy, x + 3, y_bottom,
                                           fill=_lighten(color), outline="")
            shelf_canvas.create_rectangle(x + sw - 3, sy, x + sw, y_bottom,
                                           fill=_darken(color), outline="")

            # Title text rotated 90 degrees to read along the spine
            shelf_canvas.create_text(
                x + sw // 2, sy + sh // 2,
                text=title, fill="white",
                font=("Georgia", SPINE_FONT_SIZE, "bold"),
                angle=90, width=sh - 12,
                anchor="center", justify="center",
            )

            # Invisible rectangle on top to catch mouse clicks for this book
            tag = f"spine_{shelf_num}_{x}"
            shelf_canvas.create_rectangle(x, sy, x + sw, y_bottom,
                                           fill="", outline="", tags=(tag,))
            _t = title
            shelf_canvas.tag_bind(tag, "<Button-1>",
                                   lambda e, t=_t: open_book(t))
            shelf_canvas.tag_bind(tag, "<Enter>",
                                   lambda e: shelf_canvas.config(cursor="hand2"))
            shelf_canvas.tag_bind(tag, "<Leave>",
                                   lambda e: shelf_canvas.config(cursor=""))
            x += sw + PADDING_X


# =============================================================================
# ADD BOOK
# =============================================================================

def add_book():
    """Reads the title and synopsis from the input fields, adds the book to
    the dictionary, saves it to books.json, and redraws the shelf."""
    title    = entry_title.get().strip()
    synopsis = entry_synopsis.get("1.0", "end").strip()

    if not title:
        messagebox.showwarning("Missing title",
                               "Please enter a book title.", parent=root)
        return
    if not synopsis:
        messagebox.showwarning("Missing synopsis",
                               "Please enter a synopsis.", parent=root)
        return
    if title in books:
        messagebox.showwarning("Duplicate",
                               f'"{title}" is already on your shelf.', parent=root)
        return

    books[title] = {"synopsis": synopsis, "cover": None, "color": None}
    save_books()   # write to disk immediately so closing won't lose the book
    render_shelf()
    entry_title.delete(0, "end")
    entry_synopsis.delete("1.0", "end")
    entry_title.focus()


# =============================================================================
# MAIN WINDOW
# =============================================================================

root = tk.Tk()
root.title("My Bookshelf")
root.configure(bg="#2B1B0E")
root.geometry("820x720")
root.minsize(640, 520)

# Header
header = tk.Frame(root, bg="#2B1B0E", pady=14)
header.pack(fill="x")
tk.Label(header, text="My Bookshelf",
         font=("Georgia", 22, "bold"),
         bg="#2B1B0E", fg="#F5DEB3").pack()

# Shelf canvas + scrollbar
shelf_area = tk.Frame(root, bg="#2B1B0E")
shelf_area.pack(fill="both", expand=True, padx=16, pady=(4, 8))

shelf_canvas = tk.Canvas(shelf_area, bg="#E8D5B0",
                           highlightthickness=2, highlightbackground="#7B5C3A")
vsb = tk.Scrollbar(shelf_area, orient="vertical", command=shelf_canvas.yview)
shelf_canvas.configure(yscrollcommand=vsb.set)
vsb.pack(side="right", fill="y")
shelf_canvas.pack(side="left", fill="both", expand=True)

shelf_canvas.bind("<Configure>", lambda e: render_shelf())
shelf_canvas.bind_all("<MouseWheel>",
    lambda e: shelf_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

# Add Book panel
add_outer = tk.Frame(root, bg="#4A2E12", pady=2)
add_outer.pack(fill="x", padx=16, pady=(0, 12))

add_panel = tk.Frame(add_outer, bg="#3D2008", padx=16, pady=12)
add_panel.pack(fill="x", padx=2, pady=2)
add_panel.columnconfigure(1, weight=1)

tk.Label(add_panel, text="Add a New Book",
         font=("Georgia", 12, "bold"), bg="#3D2008", fg="#F5DEB3"
         ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

tk.Label(add_panel, text="Title",
         font=("Georgia", 10, "bold"), bg="#3D2008", fg="#D4A96A"
         ).grid(row=1, column=0, sticky="w", padx=(0, 10))

entry_title = tk.Entry(add_panel, font=("Georgia", 10),
                        bg="#FFF8EE", fg="#2B1B0E", insertbackground="#2B1B0E",
                        relief="flat", bd=0, highlightthickness=2,
                        highlightbackground="#9C7248", highlightcolor="#D4A96A")
entry_title.grid(row=1, column=1, sticky="ew", padx=(0, 12), ipady=5)

tk.Label(add_panel, text="Synopsis",
         font=("Georgia", 10, "bold"), bg="#3D2008", fg="#D4A96A"
         ).grid(row=2, column=0, sticky="nw", padx=(0, 10), pady=(8, 0))

entry_synopsis = tk.Text(add_panel, font=("Georgia", 10),
                          bg="#FFF8EE", fg="#2B1B0E", insertbackground="#2B1B0E",
                          relief="flat", bd=0, highlightthickness=2,
                          highlightbackground="#9C7248", highlightcolor="#D4A96A",
                          height=3, wrap="word")
entry_synopsis.grid(row=2, column=1, sticky="ew", padx=(0, 12), pady=(8, 0))

FlatButton(add_panel, text="Add Book +", command=add_book,
           bg="#B5451B", hover="#922B21", padx=16, pady=10,
           font=("Georgia", 10, "bold")
           ).grid(row=1, column=2, rowspan=2, sticky="ns")

root.after(100, render_shelf)
root.mainloop()
