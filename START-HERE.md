# Little Crossword — my personal iPhone app

No App Store, no Netlify, no paid AI API, no subscription. Works offline once installed.

## What you get

- The compact lavender/charcoal, five-Across + five-Down crossword you approved.
- iPhone's own keyboard, delete/backspace along the chosen answer, clue navigation, written hints beneath clues.
- **Classic Daily**: one crossword for each calendar date, selected automatically on your iPhone. Works offline.
- **Themed Daily**: a rotating theme with edited clues, also offline.
- **In the News**: a crossword linked to fresh BBC RSS headlines when a free GitHub Action has published one. If no verified headline update is available, you can play the clearly labelled offline **Newsroom** mini instead. This is not an AI generator.
- Practice archive with 24 checked mini crosswords, and local saving/completion progress.

Important limitation: Classic/Themed use a **24-puzzle curated library** (and theme-specific rewrites). The same answer grid will eventually recur. The app will not make thousands of new AI crosswords automatically without an AI model or a larger prewritten library. It never passes an old puzzle off as today's news.

## Install for free using your Mac and iPhone

GitHub Pages hosts the app for free for public repositories. You do NOT publish it to the Apple App Store. The GitHub Pages URL itself is publicly accessible to anyone who knows it, even though this is intended for your personal use. No personal data is uploaded by the app: your letters and completion history stay in your iPhone's local browser storage.

### A. Put the app online once, from your Mac

1. Create a free GitHub account at https://github.com if you do not already have one.
2. Download `Little-Crossword-Personal-iPhone.zip` and open it. macOS often unzips it automatically. Inside is a folder named `Little-Crossword-Personal`; the `index.html` file must stay alongside `app.js`, `generator.js`, `daily.js`, and the `icons`, `data` and `.github` folders.
3. Install the **free GitHub Desktop app** from https://desktop.github.com. Sign in with your GitHub account.
4. In GitHub Desktop select **File → Add Local Repository… → Choose…**, then select the `Little-Crossword-Personal` folder. Because it is not yet a Git repository, choose **Create a repository here** if prompted. Alternatively choose **File → New Repository…** and select the downloaded folder as its local path.
5. In GitHub Desktop click **Publish repository**. Give it a name such as `little-crossword`. **Untick “Keep this code private”**. GitHub Free's GitHub Pages requires a public repository. Confirm Publish.
6. In Safari or Firefox on your Mac open the new repository on github.com, select **Settings → Pages**. Under **Build and deployment**, choose **Deploy from a branch**, then **main**, folder **/(root)**, and **Save**.
7. Open the URL that appears in **Settings → Pages** once deployment finishes. It will usually resemble `https://YOUR-GITHUB-USERNAME.github.io/little-crossword/`. **Use the actual URL shown by GitHub**; it is not the same as the repository's github.com URL.

### B. Install on your iPhone

8. Open that GitHub Pages website URL on your **iPhone in Safari**.
9. Tap Safari's **Share** button (or the page-menu button then Share). Scroll to **Add to Home Screen**.
10. Leave **Open as Web App** enabled. Name it **Little Crossword** and tap **Add**.
11. Open the new Home Screen icon. Play Classic and Themed while online once so the offline app resources cache. You can then play those editions and the practice archive without an internet connection.

**Safari note:** If you cannot see “Add to Home Screen”, scroll to the bottom of the Share sheet, tap **Edit Actions** and add it.

## Enable daily headlines (optional and free)

The included `.github/workflows/daily-news.yml` runs each morning on GitHub Actions without an AI API key, retrieves public BBC RSS headlines, and creates a news-linked crossword from **already verified answer grids**. It writes `data/news.json`; the site uses it only for the matching UK date. When the news feed cannot be accessed, or there is no recent headline that matches a suitable answer, your offline Newsroom mini still works. Headline clues are rule-based fill-in-the-blank puzzles, not AI-generated current-affairs trivia.

- On GitHub visit the repository → **Actions** and confirm that workflows are permitted. On first setup open **Update daily headline crossword** and choose **Run workflow** to test it.
- If the run says it cannot push, go to **Settings → Actions → General → Workflow permissions** and choose **Read and write permissions**, or keep the explicit `contents: write` permission in the included workflow.
- GitHub Actions scheduled runs are not guaranteed to start at the exact minute; if the public RSS service fails, today's news mini may be unavailable.
- No other hosting provider, OpenAI key, token, or charge is needed. GitHub's free account limits and terms apply.

## Updating in future

To change the app files later, replace them within the same `Little-Crossword-Personal` folder on your Mac. In GitHub Desktop, **Commit** the changes and choose **Push origin**. GitHub Pages will republish the site. You do not need to delete the iPhone Home Screen icon. Existing progress should remain when using the *same website address* and browser storage.

## Troubleshooting

- **Website shows GitHub's 404:** Verify Pages is set to main/root and give it time to deploy.
- **It downloads a file instead of opening:** You opened `index.html` in Files, not the hosted HTTPS URL. Open the GitHub Pages URL in Safari.
- **News says offline:** The app works normally; the scheduled feed update has not succeeded for today. Check **Actions** on your repository.
- **Edits not appearing:** Fully close and reopen the Home Screen app while online. Service worker updates are normally activated after reopening.
- **Progress isn't moving over from Netlify:** Browser storage is isolated by website address; a new GitHub Pages address cannot read the saved data from the old Netlify origin.
- **App is visible to others:** GitHub Pages on the free public-repository option is not password-protected. Don't put personal secrets or private data into the repository.

## What's in the folder

`index.html`, `style.css`, `app.js`, `generator.js`, `daily.js`, `sw.js`, `manifest.webmanifest` — complete PWA.  
`icons/` — Home Screen icon.  
`data/` — optional generated daily headline JSON.  
`scripts/build_news.py` — BBC RSS headline matcher (no API key).  
`.github/workflows/daily-news.yml` — optional morning GitHub workflow.

Version: Personal v10, 6 November 2026.
