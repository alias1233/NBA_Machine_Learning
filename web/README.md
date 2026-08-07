# web

The website. SvelteKit, TypeScript, and Svelte 5 runes.

It shows a prediction for one player statistic in one game. A prediction is a probability for every
whole number outcome, so the page draws the whole shape and works out over and under odds for any
line without asking the server again.

**`docs/WEBSITE_DESIGN_DOCUMENT.md` is the design authority for this folder.** Read it before
changing anything here. It holds every colour, size, spacing value and user-facing string, its rules
are numbered so a review can cite them, and where it and this code disagree, it is right.

## Running it

The site cannot answer anything on its own. It needs the prediction service in `../python` running
first.

```sh
cd ../python && uv run uvicorn nba_ml.api:app        # in one terminal
cp .env.example .env                                 # once
npm install && npm run dev                           # in another
```

`NBA_API_URL` in `.env` says where the service listens. It is read at runtime rather than at build
time, so one built image works in development and on the server.

```sh
npm run dev       # development server
npm run build     # production build, into build/
npm start         # serves that build, which is what the container will do
npm run check     # TypeScript and Svelte checks
npm test          # checks lib/odds.ts against the Python it was ported from
node scripts/contrast.mjs   # checks the palette against its contrast floors
```

If no game is listed to predict on, the schedule has not been collected. Run `nba-collect schedule`
in `../python`, or put a made up game on it with `nba-schedule add-mock`.

## Layout

```
src/app.css                    every colour, size, space and duration the site uses
src/app.html                   the theme declaration and the three font preloads
src/lib/site.ts                the site name and the landing description, held once
src/lib/types.ts               the shapes the service sends, named as they cross the wire
src/lib/models.ts              the model families, and which of them are published
src/lib/collage.ts             the landing collage tiles and where each one sits
src/lib/games.ts               writing a scheduled game out for a reader
src/lib/odds.ts                expected value, line odds, the drawn range, the rounding
src/lib/odds.test.ts           the check that the port still agrees with the Python
src/lib/motion.ts              rolling a figure to its new value
src/lib/ads.ts                 the two ad slots, and whether ads run at all
src/lib/server/api.ts          the only place that calls the service
src/lib/components/            the pieces with behaviour in them
src/routes/+layout.svelte      the shell: header, models menu, footer, disclaimer
src/routes/+page.svelte        the landing screen, one viewport and no scroll
src/routes/models/             every family, then one folder per family
src/routes/about/              how it works, the one page allowed to explain
src/routes/privacy/            required before ads can run
src/routes/api/                player search and rosters, the two things the browser fetches
static/collage/                the landing images, each shipped one with a row in credits.txt
static/fonts/                  Instrument Serif, Inter Tight and JetBrains Mono, Latin only
```

Six rules hold this together.

**`app.css` is the machine-readable copy of the design document.** Every token lives there and
nothing else holds a raw colour, size, radius or duration. Changing the look means editing that one
block.

**There are two containers, the panel and the block.** A panel is quiet and holds what the reader
operates. A block is loud, inverts the theme, and holds what the reader came for. Both are classes
in `app.css`. A block uses the block ink family, and the one thing that nests inside it is a
`--surface` area for data or an image. Alternating the two is what gives a page its composition.

**The prediction service is never reachable from a browser.** It listens on the internal network
only. Everything goes through `src/lib/server/api.ts`, which runs on the server. The exceptions are
player search and the rosters of a chosen game, which both have to happen without a page load, so
they go through this site's own `/api` routes.

**The form is the pending request and the URL is the answered one.** Editing a field or choosing a
game card changes the form. Only the submit button copies the form into the URL, and that is what
runs a prediction. A card choice and the chosen line are written with a history replace, so neither
fills the back button, and a prediction is a push, because it is somewhere you can go back from.
Loading any of those URLs gives the same page back, server rendered and shareable.

**Read `location.href`, never `page.url`, before a shallow write.** SvelteKit's `replaceState` does
not refresh `page.url`, so a second write built from `page.url` puts back whatever the first one
replaced. This cost a real bug in the card picker and the line handle.

**A model family is one entry and one folder.** `src/lib/models.ts` lists the families and the root
layout filters them down to the ones with a published model, which is what the header menu and
`/models` are both built from. Adding a family means one entry there and one folder under
`src/routes/models/`.

## Describing a game

A game is its date, its two teams and the part of the season, however the reader named it. Those
four parameters are always on the page, always in the URL, and always submitted. A card writes the
same four, so there is one way to name a game and no precedence to keep straight.

While the described game is one of the upcoming ones, the player picker is a list of the two teams'
players and the roster controls are live. Editing a team or the date breaks the match, and the
picker becomes a search over the whole league.

## Placeholders in place

Each is an open decision in section 16 of the design document, and each holds its space so that
filling it in shifts no layout.

- The site name and the landing description, in `src/lib/site.ts`.
- The collage tiles. One test picture is in place and the other five paint the duotone gradient.
  Filling one in is `image` on an entry in `src/lib/collage.ts` plus its row in
  `static/collage/credits.txt`.
- The family graphic and the favicon.
- The accuracy table on About, which waits on the three untrained models.
- The privacy wording. Ads stay off until it is real, and `ADS_ENABLED` in `src/lib/ads.ts` is the
  one line that turns them on.

## What is not here yet

When the PostgreSQL prediction cache is built, it is read inside `predictPlayerStat` in
`src/lib/server/api.ts`, before the call to the service. Nothing above that function changes.

`docs/TODO.md` has the order the rest of the work happens in.
