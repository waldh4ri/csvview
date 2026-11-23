# csvview

Fast, fully client-side CSV/TSV viewer. Nothing is uploaded: files are parsed in your browser.

**Live:** https://waldh4ri.github.io/csvview/

- Millions of rows (virtual scrolling), search (plain/regex), per-column filters and value pickers
- Files larger than 500 MB: the text is indexed while it streams in and kept in 128M-char chunks, so the limit is your RAM (an 890 MB / 8M-row file loads in ~10 s and uses ~2 GB)
- Automatic integer / decimal / timestamp detection with typed sorting and range filters
- Column resize, reorder (drag a header or Ctrl+←/→) and hide; right-click a header for sort / hide / move / stats
- Double-click a cell (or press Space) to see its full content, with JSON pretty-printing
- Row details panel, export of the filtered view (respects column order and hidden columns)

Open the page and drop a file, or use `csvview.py data.csv` to launch the viewer locally from a terminal.
