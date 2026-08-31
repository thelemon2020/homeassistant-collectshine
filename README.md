# CollectShine for Home Assistant

Ask for a record out loud and watch one LED come on.

A [CollectShine](https://collectshine.com) base station owns your record collection and drives LED
strips along the shelves. This integration puts it on your home network as a Home Assistant device,
so "find Kind of Blue" lights the exact record — through Assist, or through Alexa, Google or Siri
if you already bridge them.

Everything happens on the LAN. Nothing about your collection goes through the cloud to make this
work.

> **CollectShine Plus.** The base station requires an active subscription for agent access.

## What you get

| Entity | What it is |
|---|---|
| `light.<name>_shelf` | Master power for every shelf. On/off only — see [why](#why-the-light-is-onoff-only). |
| `sensor.<name>_now_playing` | What is on the turntable, with `release_id` in its attributes. |
| `sensor.<name>_last_played` | The one before that. |
| `binary_sensor.<name>_flip_due` | Side A has run out. |
| `sensor.<name>_collection_size` | How many records the base station holds. |
| `button.<name>_dig` | Let the shelf choose — a light runs along the strip and stops on a record. |
| `button.<name>_clear_highlight` | Put the lighting back to normal. |

Plus a `collectshine.find_record` service and a `CollectShineFindRecord` intent.

## Installing

**HACS** → three-dot menu → Custom repositories → add this repository as an **Integration**, then
install and restart Home Assistant.

**By hand** — copy `custom_components/collectshine` into your `config/custom_components/` and
restart.

Then **Settings → Devices & Services**. Your base station is usually found on its own; if not,
add it manually with its address (`collectshine-3f2a.local` or its IP).

You will be asked for an agent token. Get one from the CollectShine app under
**Settings → AI agent access** — it is shown once. The base station stores only a hash of it, and
you can revoke it there at any time.

## Talking to it

The integration registers the intent; the sentences that reach it are yours to write, because a
custom integration cannot add sentences to Assist's matcher. Create
`config/custom_sentences/en/collectshine.yaml`:

```yaml
language: "en"
intents:
  CollectShineFindRecord:
    data:
      - sentences:
          - "find [me] [the] [record] {name}"
          - "find [me] {name} on [the] [record] shelf"
          - "where is [my] [copy of] {name}"
          - "light up {name}"
          - "put {name} on the record player"
        slots:
          name: "{name}"
lists:
  name:
    wildcard: true
```

Restart, and try *"find Kind of Blue"*.

`wildcard: true` hands the base station the raw transcript, filler words and all. That is
deliberate — the matching happens there, against your actual collection, where a misheard artist
name can still be recognised.

> ⚠️ **Don't add a bare `"play {name}"`.** It is greedy, and it will swallow utterances meant for
> your media players. Prefer a bounded phrase like `"put {name} on the record player"`.

### From an automation

```yaml
action:
  - action: collectshine.find_record
    data:
      query: "blue train by john coltrane"
    response_variable: found
  - if: "{{ found.outcome == 'ambiguous' }}"
    then:
      - action: notify.mobile_app
        data:
          message: "{{ found.speech }}"
```

`outcome` is one of `matched`, `ambiguous`, `not_found` or `empty_query`. When several records fit,
nothing is lit and `speech` names the choices — say it again with the artist and the second attempt
will land.

### Through Alexa or Google

Home Assistant does the bridging, not this integration.

- **Entities work anywhere.** Expose `light.<name>_shelf` and *"Alexa, turn on the record shelf"*
  works immediately over the ordinary smart-home bridge.
- **Free-form "find Kind of Blue" needs Assist to be reachable.** The smart-home bridge only
  exposes entities, so this needs Home Assistant Cloud's Alexa conversation route — or just use
  Assist directly, from a Voice PE satellite or the companion app.
- **Fully local** — Assist with local speech-to-text involves no third party at all. It is also the
  setup where the base station's fuzzy matching earns its keep, since local recognisers are weaker
  on proper nouns than Amazon's.

## Notes

### Why the light is on/off only

Your LED controllers run stock WLED, and Home Assistant's WLED integration already exposes colour,
effects and palettes better than a passthrough here could. What CollectShine owns, and WLED cannot,
is master power across every controller at once and the record-level spotlight.

Master power matters more than it looks: a colour, palette or spotlight sent to a strip that is
switched off is accepted by the hardware and shows **nothing at all**, with no error. If you find a
record and see no light, check this switch first — the spoken answer will tell you too.

### One base station

The intent uses the first configured base station. Households have one shelf far more often than
several, and an intent carries no way to say which. If you run two, the service is the way to
address them for now.

### Why not one entity per record

It would be neat — "Alexa, turn on Kind of Blue" for free. It also means two thousand entities in
your recorder, and it moves matching to Home Assistant's entity matcher, which is tuned for
"kitchen light" rather than *Lift Your Skinny Fists Like Antennas to Heaven*. The matching belongs
on the base station, next to the collection.

## Requirements

Home Assistant 2024.12 or newer, a paired CollectShine base station on the same network with
firmware advertising API version 1, and an active CollectShine Plus subscription.
