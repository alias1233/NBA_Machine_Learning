# web

The website. SvelteKit, TypeScript, and Svelte 5 runes.

## Running it

The process that runs the machine learning pipeline in `../python` needs to be running first.

```sh
cd ../python && uv run uvicorn nba_ml.api:app        # in one terminal
cp .env.example .env                                 # once
npm install && npm run dev                           # in another
```

`NBA_API_URL` in `.env` says where the service listens. It is read at runtime.

```sh
npm run dev       # development server
npm run build     # production build, into build/
npm start         # serves that build, which is what the container will do
npm run check     # TypeScript and Svelte checks
npm test          # checks lib/odds.ts, the only place an answer is turned into what a reader reads
```

If no game is listed to predict on, the schedule has not been collected. Run `nba-collect schedule`
in `../python`, or put a made up game on it with `nba-schedule add-mock`.

## Layout

```
src/app.css                    every color, size, space and duration the site uses
src/app.html                   theme declaration and the three font preloads
src/lib/site.ts                site name and the hero description
src/lib/types.ts               shapes the service sends
src/lib/models.ts              model families
src/lib/collage.ts             hero collage tiles, in the order the hero grid places them
src/lib/graphics.ts            family graphics, found by filename
src/lib/assets/model_graphics/ one image per family, named after it
src/lib/games.ts               writing a scheduled game out for a reader
src/lib/odds.ts                expected value, line odds, category shares, the drawn range, the rounding
src/lib/motion.ts              rolling a figure to its new value
src/lib/ads.ts                 the two ad slots, and whether ads run at all
src/lib/server/api.ts          the only place that calls the python service
src/lib/components/            the pieces with behavior in them
src/routes/+layout.svelte      the shell: header, models menu, footer, disclaimer
src/routes/+page.svelte        the home page: the hero, then the Models section under it
src/routes/models/             a redirect to the models, then one folder per family
src/routes/about/              how the models work
src/routes/privacy/            required before ads can run
src/routes/api/                player search, rosters, and a model's held-out figures
static/collage/                the hero images
static/fonts/                  Instrument Serif, Inter Tight and JetBrains Mono, Latin only
```
