# Go live: www.boombaland.com

Status on 31 Oct 2026: **stage 1, localhost only.** Nothing is bought, pushed, published or signed in to. The site runs at
http://127.0.0.1:8766/ from `python3 -m http.server 8766 --bind 127.0.0.1` in this folder.

Values marked ✅ were read on the cited docs page on 31 Oct 2026. Values marked ⚠ could not be confirmed on an official
page. Check those at the moment you use them.

> **Timing decision for the PO.** Content freeze is **Wed 4 Nov** and launch is **Thu 19 Nov**.
> - If the domain and DNS are live **before the 1.0 build is cut**, step 4a can ship in 1.0. Then the game and both store
>   listings launch on the new URLs.
> - If not, 1.0 ships with the github.io URLs. Those must then keep working for as long as 1.0 is installed (step 5),
>   and the game links move in 1.0.1.

---

## 1. Buy the domain (PO, at Porkbun)

1. Register `boombaland.com` at https://porkbun.com. WHOIS privacy is free at Porkbun, so leave it on.
2. Add **Email Hosting** for the domain at checkout or afterwards, if step 3 option A is chosen.
3. Leave the DNS at Porkbun (the default). Every record below is entered at Porkbun under **Domain Management ›
   boombaland.com › Details › DNS Records**.

## 2. Hosting: GitHub Pages with the custom domain

### 2.1 Which repo

**Recommended (A): a new public repo, `tdbruijndatasight/boombaland-site`, holding this folder.** The old repo
`tdbruijndatasight/boomworld-legal` stays up as a redirect shell (step 5). This keeps every old URL answering, including
the game's clock check, and you can roll back by pointing DNS back.

**Alternative (B): replace the contents of `boomworld-legal` with this site** and set the custom domain on that repo.
- This is one repo instead of two.
- GitHub is widely observed to 301-redirect `tdbruijndatasight.github.io/boomworld-legal/<path>` to the custom domain once
  the repo has one. That is **⚠ not stated on the docs pages read** (see the research note in step 5). Test it with
  `curl -I` before relying on it.
- The site's links are root paths (`/assets/...`). Before the custom domain works, the site would be served under
  `/boomworld-legal/` and would show **without styles or images**. In option B, do step 2.2 (DNS) first and push second.

### 2.2 DNS records at Porkbun

Source: GitHub, "Managing a custom domain for your GitHub Pages site",
https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site ✅

**Delete Porkbun's default parking records first** (usually an `ALIAS` on the apex and a `CNAME` on `*`, both pointing
to `pixie.porkbun.com`). ⚠ This step is not in Porkbun's GitHub article. GitHub warns that extra A/AAAA/ALIAS/CNAME
records on the domain can block the HTTPS certificate ✅
(https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https).

| Type | Host | Answer | TTL |
|---|---|---|---|
| A | *(blank, the apex)* | `185.199.108.153` | 600 |
| A | *(blank)* | `185.199.109.153` | 600 |
| A | *(blank)* | `185.199.110.153` | 600 |
| A | *(blank)* | `185.199.111.153` | 600 |
| AAAA | *(blank)* | `2606:50c0:8000::153` | 600 |
| AAAA | *(blank)* | `2606:50c0:8001::153` | 600 |
| AAAA | *(blank)* | `2606:50c0:8002::153` | 600 |
| AAAA | *(blank)* | `2606:50c0:8003::153` | 600 |
| CNAME | `www` | `tdbruijndatasight.github.io` (the user name only, **no repo name**) | 600 |
| TXT | `_github-pages-challenge-tdbruijndatasight` | the code GitHub shows in step 2.3 | 600 |

- All 8 IPs are ✅ from the GitHub page above. GitHub recommends the A records even when the AAAA records are added.
- On www: "point directly to `<user>.github.io`" ✅. Don't use the `*.pages.github.io` name shown in repo settings.
- Porkbun has a **Quick DNS Config › "Github"** button that adds the `www` CNAME from your user name ✅
  (https://kb.porkbun.com/article/64-how-to-connect-your-domain-to-github-pages). The article does not list the apex
  A records, so enter them by hand from the table.

### 2.3 Verify the domain on GitHub (stops domain takeover)

Source: https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages ✅

1. Go to GitHub profile **Settings › Pages** (the account settings, not the repo) and choose **Add a domain**. Enter
   `boombaland.com`.
2. GitHub shows a TXT name `_github-pages-challenge-tdbruijndatasight` and a value. Add it at Porkbun (table above).
3. Click **Verify**. Leave the TXT record in place afterwards, because GitHub re-checks it.

### 2.4 Publish and switch on HTTPS

1. Create the repo (option A) and push this folder to `main`. It holds `CNAME` (`www.boombaland.com`), `.nojekyll`
   and `404.html`.
2. In the repo, open **Settings › Pages**:
   - Under **Source**, choose **Deploy from a branch**, branch `main`, folder `/ (root)`.
   - Under **Custom domain**, enter `www.boombaland.com` and save. With branch publishing, GitHub keeps or commits the
     `CNAME` file. With GitHub Actions publishing, the `CNAME` file is ignored and the setting alone counts ✅.
3. Wait for the DNS check to go green. Then tick **Enforce HTTPS**. This "can take up to 24 hours" to become available ✅.
   If it stalls, remove the custom domain, save, add it again and save ✅.
4. GitHub redirects the apex `boombaland.com` to `www.boombaland.com` by itself, because `www` is the configured domain
   and both record sets exist ✅
   (https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/about-custom-domains-and-github-pages).
5. Check it from the terminal:
   ```
   dig +short www.boombaland.com      # tdbruijndatasight.github.io. + 185.199.x.153
   dig +short boombaland.com          # the four 185.199.x.153
   curl -sI https://boombaland.com/ | head -3           # 301 -> https://www.boombaland.com/
   curl -sI https://www.boombaland.com/privacy/ | head -1  # 200
   curl -s  https://boombaland.com/app-ads.txt          # follows to www; must print the AdMob line
   python3 -I tools/check_links.py https://www.boombaland.com
   ```

## 3. The support mailbox support@boombaland.com

**Mailbox needs** (from the legal pages): one address that the PO reads and that can send replies, for support, data
deletion requests (privacy §7.1, 30 days) and press.

### Option A (recommended): Porkbun Email Hosting

Sources: https://kb.porkbun.com/article/47-how-to-use-porkbun-email-when-your-dns-is-hosted-elsewhere ✅,
https://kb.porkbun.com/article/179-how-to-turn-on-dkim-dmarc ✅,
https://kb.porkbun.com/article/146-email-client-configuration-settings ✅,
https://porkbun.com/products/email ✅

- **Price ⚠.** The product page says "as low as $3.00 / month", with a 15-day trial, 10 GB and 20 forwards. A KB
  article says "$3/month per address (billed yearly)" (about $36 a year). Check the price at checkout.
- **Records.** With the DNS at Porkbun, the email setup adds these. Check that each one is there:

| Type | Host | Answer | Priority |
|---|---|---|---|
| MX | *(blank)* | `fwd1.porkbun.com` | 10 |
| MX | *(blank)* | `fwd2.porkbun.com` | 20 |
| TXT | *(blank)* | `v=spf1 include:_spf.porkbun.com ~all` | |
| TXT | `default._domainkey` | the DKIM key Porkbun shows (copy it from the DNS Records page) | |
| TXT | `_dmarc` | Porkbun's value, added by **Configure DMARC** (which also turns on DKIM ✅). If you write it yourself, start with `v=DMARC1; p=none; rua=mailto:support@boombaland.com` and move to `p=quarantine` after 2–4 clean weeks. ⚠ That value is a suggestion; Porkbun's page gives none. | |

  There can be only **one** SPF record on the domain ✅. If another sender is added later, merge it into that record.
- **Outlook (new Outlook or classic) › Add account › `support@boombaland.com` › Advanced › IMAP:**

| | Server | Port | Security |
|---|---|---|---|
| Incoming (IMAP) | `imap.porkbun.com` | 993 | SSL/TLS |
| Outgoing (SMTP) | `smtp.porkbun.com` | 587 | STARTTLS (465 with SSL/TLS also works; 50587 STARTTLS if 587 is blocked) |
| (POP, not recommended) | `pop.porkbun.com` | 995 | SSL/TLS |

  The user name is the full address `support@boombaland.com`, with the mailbox password set at Porkbun. Do the same on
  the iPhone: Settings › Mail › Accounts › Add Account › Other.

### Option B: Microsoft 365 Business Basic

Source for DNS: https://learn.microsoft.com/en-us/microsoft-365/admin/get-help-with-domains/create-dns-records-at-any-dns-hosting-provider ✅

- **Price ⚠.** No official Dutch price could be loaded. Check https://www.microsoft.com/nl-nl/microsoft-365/business/microsoft-365-business-basic
  (per user per month, annual commitment, excl. VAT). It includes Exchange (50 GB), Outlook on the web and mobile,
  Teams, and 1 TB of OneDrive.
- **Records** (the exact targets are shown in the Microsoft 365 admin centre under Settings › Domains):

| Type | Host | Answer |
|---|---|---|
| MX | *(blank)* | the value from the admin centre, normally `boombaland-com.mail.protection.outlook.com` (⚠ form not on the page), priority 0 |
| TXT | *(blank)* | `v=spf1 include:spf.protection.outlook.com -all` ✅ |
| CNAME | `autodiscover` | `autodiscover.outlook.com` (⚠ copy it from the admin centre) |
| CNAME | `selector1._domainkey` / `selector2._domainkey` | the DKIM targets from the admin centre (optional, recommended) |
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:support@boombaland.com` (suggestion) |

- Use **one** of option A or option B. Two MX sets on one domain split the mail.
- Outlook then signs in with the Microsoft account. No IMAP settings are needed.

## 4. Everything that must change after go-live

### 4a. In the game (BombWorld repo, `origin/coordinator/integrate-1028` at `31c1cec10`)

Found with `git grep -n -E 'boomworld-legal|github\.io|info\.tomdebruijn@gmail\.com'` (scratch logs, backlog and old QA
notes left out):

| File:line | What | Change to |
|---|---|---|
| `Assets/_Project/Code/Menu/Data/Legal/LegalConfig.asset:15` | `privacyPolicyUrl` | `https://www.boombaland.com/privacy/` |
| `Assets/_Project/Code/Menu/Data/Legal/LegalConfig.asset:16` | `termsUrl` | `https://www.boombaland.com/terms/` |
| `Assets/_Project/Code/Menu/Data/Legal/LegalConfig.asset:17` | `supportUrl` | `https://www.boombaland.com/support/` |
| `Assets/_Project/Code/Menu/Services/HttpDateNetworkTime.cs:18` | `DefaultUrl`, the **clock check**: a HEAD request whose `Date` header the anti-cheat clock trusts (D-33.383) | `https://www.boombaland.com/`. It is still GitHub Pages, so privacy policy §2 ("our website (hosted by GitHub)") stays true. If hosting ever leaves GitHub, that sentence must change too. |
| `Assets/_Project/Code/Menu/Tests/EditMode/GameNameTests.cs:33` | an allow-list entry: the old-name test lets `boomworld-legal` through as the legal site's repo name | keep it while the old repo or its URLs are mentioned anywhere. It is harmless after that. |
| `Assets/_Project/Code/Menu/Tests/EditMode/GameNameTests.cs:69, :145, :146` | asserts the old privacy and terms URLs | the new URLs |
| `Assets/_Project/Code/Menu/Tests/EditMode/LegalImportTests.cs:48, :49, :50` | asserts the three old URLs | the new URLs |
| `legal/PRIVACY_POLICY.md:8, :384, :446, :457, :483` | the policy's source and its store notes. Line 457 is Play's **Delete account URL** (`…/support/#delete-your-account-and-data`). | `https://www.boombaland.com/…` (the `#delete-your-account-and-data` anchor exists on the new support page) |
| `legal/PRIVACY_POLICY.md:362, :388` | the contact address | `support@boombaland.com` |
| `legal/TERMS_OF_SERVICE.md:6, :160` / `:165` | the URL / the contact address | the new URL / `support@boombaland.com` |
| `legal/README.md:85–88, :135–137` | the publishing notes and the open app-ads.txt problem | the new site. The app-ads.txt problem is solved by the custom domain (step 4c). |

There is no `mailto:` with the old address in `Assets/`. The game opens the support **page**, and that page carries the
new address.

### 4b. App Store Connect (Boombaland, `com.datasight.bombworld.ios`)

Source: https://developer.apple.com/help/app-store-connect/reference/platform-version-information ✅ and
https://developer.apple.com/help/app-store-connect/reference/app-information ✅

| Field | Where | New value |
|---|---|---|
| Support URL (required) | the version page (Platform version information) | `https://www.boombaland.com/support/` |
| Marketing URL | the version page | `https://www.boombaland.com/`. AdMob reads the developer site for iOS from this field (step 4c). |
| Privacy Policy URL | **App Information** (app level) | `https://www.boombaland.com/privacy/` |
| User Privacy Choices URL (optional) | App Information | `https://www.boombaland.com/privacy/` (if used) |

⚠ Support and Marketing URL are per-version fields. Change them on a version that is still editable: the 1.0 submission
if it has not been sent yet, otherwise the next version. Apple's page does not say whether App Information can be
edited while a version is live. Do this before or together with the next submission.

### 4c. Google Play Console (Boombaland, `com.datasight.boomworld`)

Source: https://support.google.com/googleplay/android-developer/answer/9859152 ✅

| Field | Where | New value |
|---|---|---|
| Email address | **Grow users › Store presence › Store settings › Store listing contact details** ✅ | `support@boombaland.com` |
| Website | same place ✅ | `https://www.boombaland.com/`. **AdMob reads app-ads.txt from this domain.** |
| Privacy policy | **Policy and programs › App content › Privacy policy** (⚠ path from memory, not on the page read) | `https://www.boombaland.com/privacy/` |
| Delete account URL | **App content › Data safety** (⚠ path) | `https://www.boombaland.com/support/#delete-your-account-and-data` |

### 4d. AdMob app-ads.txt

Source: https://support.google.com/admob/answer/9363762 ✅

- AdMob takes the developer website from the store listing (Play: Website; App Store: Marketing URL) and fetches
  `https://<domain>/app-ads.txt`. It **drops `www.`**, so it reads `https://boombaland.com/app-ads.txt`. That apex
  URL redirects to `www` (step 2.4), and redirects are allowed ✅.
- `app-ads.txt` in this site is byte-for-byte the old repo's file:
  `google.com, pub-2311579250532127, DIRECT, f08c47fec0942fa0`.
- After the store fields change, AdMob takes up to 24 hours to crawl ✅. Check **AdMob › Apps › app-ads.txt** for
  "Verified". On the github.io URL this never could verify, because AdMob reads only the host root (`legal/README.md:135`).

### 4e. The legal pages' contact address

This is done in this site: `info.tomdebruijn@gmail.com` became `support@boombaland.com` on every page (privacy: 3,
terms: 2, support: 4 occurrences, footers included). Everything else in the wording is verbatim
(`tools/build.py` asserts it).
- The pages' "Last updated" dates were **not** changed. If the PO counts the new address as a change to the policy,
  bump the date on privacy, terms and support.
- `support@boombaland.com` must be **receiving mail before this site goes live**, because it is now the legal contact
  and the deletion route.

## 5. Old github.io URLs: the redirect plan

GitHub Pages has no server-side redirects. The docs list only the automatic apex↔www redirect ✅, and nothing about
`_redirects` files or HTTP status control. So with option A, the old repo `boomworld-legal` becomes a set of
**redirect stubs**. Each stub is a page that answers **200** with a meta refresh, a canonical link and a script redirect.
Search engines treat an instant meta refresh plus a canonical link like a permanent redirect.

Replace each file in `boomworld-legal` (after the new site is live and HTTPS works):

| Old file | Redirects to |
|---|---|
| `index.html` | `https://www.boombaland.com/` |
| `privacy/index.html` | `https://www.boombaland.com/privacy/` |
| `terms/index.html` | `https://www.boombaland.com/terms/` |
| `support/index.html` | `https://www.boombaland.com/support/` (the script keeps `#delete-your-account-and-data`) |
| `app-ads.txt` | keep the file as it is (it is harmless) |
| `.nojekyll` | keep |

The stub for `privacy/index.html` (the others change only the two URLs and the title):

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Boombaland Privacy Policy has moved</title>
<link rel="canonical" href="https://www.boombaland.com/privacy/">
<meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url=https://www.boombaland.com/privacy/">
<script>location.replace("https://www.boombaland.com/privacy/" + location.hash);</script>
</head>
<body>
<p>The Boombaland Privacy Policy has moved to
<a href="https://www.boombaland.com/privacy/">https://www.boombaland.com/privacy/</a>.</p>
</body>
</html>
```

Why the old repo must stay up, and keep answering 200 at its root:

1. **The 1.0 game's clock check** sends `HEAD https://tdbruijndatasight.github.io/boomworld-legal/` (if 1.0 ships before
   step 4a). A stub answers 200 with a `Date` header, so 1.0 keeps working. Do not delete the repo while any build with
   the old `DefaultUrl` is in use.
2. **1.0's in-game Privacy, Terms and Support buttons** open the old URLs, and the stubs forward them.
3. Store reviewers and old links in search results land on the new pages.

With option B (the site pushed into `boomworld-legal` with a custom domain), GitHub serves the redirect itself if the
behaviour observed elsewhere holds. Check it after the switch:
`curl -sI https://tdbruijndatasight.github.io/boomworld-legal/privacy/` should give `301` with
`Location: https://www.boombaland.com/privacy/`. Also check `curl -sI https://tdbruijndatasight.github.io/boomworld-legal/`.
If either does not redirect, fall back to option A.

## 6. Launch-day edits to this site

1. In `assets/site.js` (`STORE_LINKS`), fill in the App Store URL (`https://apps.apple.com/app/id<Apple ID>`) and the
   Play URL (`https://play.google.com/store/apps/details?id=com.datasight.boomworld`). The buttons switch from
   "Coming 19 November" to "Download now".
2. Optionally, replace the text buttons with the official badges (IMAGE_NEEDS.md #10), and change the "Coming 19
   November" date plank in `tools/build.py`. Run `python3 -I tools/build.py` (set `LEGAL_SRC` only to re-port the legal
   pages), then `python3 -I tools/check_links.py`, then commit and push.

## How this folder is built

- These are plain static files with no build step at serve time. `tools/build.py` writes the HTML so that the header,
  footer and `<head>` stay the same on every page, and the output is committed.
- `tools/make_images.sh` re-creates `assets/img` and `assets/press` from the approved sources (it uses macOS `sips` and
  `ffmpeg`). Images are AVIF with a JPEG or PNG fallback.
- `tools/check_links.py [base-url]` crawls the site and fails on any local link, image or anchor that does not return
  200, and on missing alt text, a missing `lang`, a missing title or description, or a wrong `h1` count.
- `python3 -m http.server` does not serve `404.html` for missing paths. GitHub Pages does.
