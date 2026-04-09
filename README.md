# BookShelfProject

A little desktop app I built for my intro Python class that lets you manage your bookshelf visually. You can add books, upload cover images, and delete ones you don't want anymore. Everything saves automatically so nothing gets lost when you close it.

## How to run it

Make sure you have Python 3 installed, then open Terminal and run:

```bash
pip3 install Pillow
```

That only needs to be done once. 

## Folder structure

```
bookshelf_v2/
├── bookshelf_app.py       (run this)
├── README.md
└── data/
    ├── books.json         (where your books are saved)
    └── covers/            (where cover images get stored)
```

## How to use it

**Browsing your shelf** - all your books show up as colored spines on the shelf. Click any spine to open it and see the full details.

**Adding a book** - fill in the title and synopsis at the bottom of the window and hit "Add Book +". It saves immediately.

**Uploading a cover** - click a book spine to open it, then hit "Upload Cover". Pick any image from your computer and it'll show up right away and stay there even after you close the app.

**Deleting a book** - open the book and hit "Delete Book". It'll ask you to confirm first.

## Notes

- If you want to start completely fresh, just delete data/books.json and the app will start with an empty shelf
- Cover images get copied into data/covers/ automatically when you upload them, so even if you delete the original photo the cover stays in the app
- The app prints some info to the Terminal when it opens so you can see exactly where it's reading and saving your data, handy for debugging

---

Built with Python, Tkinter, and Pillow.
