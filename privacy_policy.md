**Privacy Policy**

What the app does

bcfeed connects to your Gmail account to read “New release from…” emails sent by Bandcamp, extract release details, and generate a local HTML dashboard. The app also optionally fetches Bandcamp embed metadata via a local proxy.


Data the app accesses

- Gmail messages that match the Bandcamp release notification query.
- No other emails, contacts, files, or calendars are accessed.


How the app uses the data

- Parses release details (date, artist, title, Bandcamp link) to build the dashboard.
- Stores read/unread state and caches release/embed metadata locally on your device to improve performance and avoid repeated Gmail/API requests.


Data storage and sharing

- All parsed data, caches, and state are stored locally on your machine (e.g., app data directory and output.html).
- No data is sent to external servers other than Google (for Gmail access) and Bandcamp (for embed/player data).
- The app does not give the developer access to any of your data. We do not (and cannot) sell, share, or transfer your data to third parties.


Data retention and control

- Caches and state persist locally until you clear them (e.g., via the app’s Reset/Clear Cache controls or by deleting the local data directory).
- You can revoke the app’s Gmail access at any time via your Google Account’s security settings.


Security

- OAuth is used to access Gmail; the app does not see or store your Google credentials.
- All processing is local; if you run the optional local proxy, it listens only on your machine unless you configure otherwise.


Contact

If you have questions or requests about this policy, contact TJ Hertz on keinobjekt@gmail.com.
