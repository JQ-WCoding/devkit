# Reading the input

| Input | How |
|---|---|
| Local or attached `.pptx` | `extract_deck.py` reads it directly: presentation order from `ppt/presentation.xml` `sldIdLst` (not the `slideN` file name), text, speaker notes, and the pictures embedded in each slide into `<deck>/media/` (not a render: a screen drawn with shapes or tables gives no picture) |
| `.pptx` page with no picture, or only logos, icons or fragments | Ask for a PDF export or a capture of that page for the mockup; text and notes still come from the pptx |
| `.pdf` | `extract_deck.py` records the pages (text and PNGs too when `pdftotext` / `pdftoppm` are installed). Otherwise read the requested pages with `Read` (`pages="N"`): one read gives both the text and the mockup |
| Images (`.png`, `.jpg` …) or a folder of them | One page per image, folder sorted by name. Read each image; the text comes from the image |
| `.ppt`, `.key`, `.docx`, `.hwp` | Not read directly. Ask for a `.pptx` or `.pdf` export (or slide images) |
| Google Slides link | With a Slides connector: `read_presentation` (slide `objectId` order = page number) and a page thumbnail at the largest width, saved with `curl` into `<work>/<screen ID>/img/p<N>.png`. With a Drive connector only: read the text (`read_file_content`), save the result to a file and pass it to `extract_deck.py`. Neither: ask for a PDF export |
| Drive link to a pptx/pdf | Download through the Drive connector if it allows (size limits apply) and pass the file to `extract_deck.py`; else read its text export as above and ask for a PDF of the target pages for the mockups |
| Figma or other design tool links | Use a connected tool for that service if there is one; else ask for PNG or PDF exports of the frames |
| Pasted text only | Save it to a file in the scratchpad and pass it to `extract_deck.py`; ask for the mockup images |

- Keep originals the user will reuse in the profile's deck folder (kept out of Git at step 0), not in the scratchpad.
- Large tool results (document text) are saved to a file whose path the result gives; pass that path on instead of copying the text.
- If two sources disagree (text export vs image), the image wins; note the disagreement in the spec.

## Fallbacks for tools

| Missing | Fallback |
|---|---|
| Document connector | Ask for the file (pptx/pdf) or page images |
| Browser tool | The user runs the screen checklist and sends captures; mockup comparison is `not run` until they arrive |
| Read-only DB query tool | `00_check.sql` for the user to run; results `unverified` until they come back |
| Profile DB agent | The main session does step 3 with the same rules |
| `.devkit/runtime.json` | The user starts the app; screen checks wait for it |
