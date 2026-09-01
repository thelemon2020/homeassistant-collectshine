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

Assist has to be told which sentences to listen for, and an integration cannot add them to its
matcher. So this part is a click rather than a file:

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fthelemon2020%2Fhomeassistant-collectshine%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fcollectshine%2Ffind_record.yaml)

Import it, create an automation from it, and try *"find Kind of Blue"*. The sentences are an input
on the blueprint, so you can add your own phrasings in the automation editor without touching a
file. No restart — a new automation is live as soon as it is saved.

The blueprint hands the base station the **raw transcript**, filler words and all. That is
deliberate: the matching happens there, against your actual collection, which is why a misheard
artist name can still be recognised. It speaks the base station's own answer back, so *"I found a
few"* and *"the shelf lights are off"* reach you instead of a cheerful *"Done"*.

> ⚠️ **Don't add a bare `"play {name}"`.** It is greedy, and it will swallow utterances meant for
> your media players. Prefer a bounded phrase like `"put {name} on the record player"`.

### Using an LLM voice assistant instead

Nothing to set up. The integration registers a `CollectShineFindRecord` intent, and an LLM-backed
conversation agent can reach it from your own words without any sentences at all.

### Writing the sentences yourself

If you would rather not use the blueprint, the older route still works — create
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

The `en` subfolder is required — a file one level up is silently never loaded. Then call the
`conversation.reload` action, and try *"find Kind of Blue"*.

### From an automation

```yaml
action:
  - action: collectshine.find_record
    data:
      query: "blue train by john coltrane"
    response_variable: found
  - if: "{{ not found.lit }}"
    then:
      - action: notify.mobile_app
        data:
          message: "{{ found.speech }}"
```

`outcome` is one of `matched`, `ambiguous`, `not_found` or `empty_query`. When several records fit,
nothing is lit and `speech` names the choices — say it again with the artist and the second attempt
will land.

**`outcome` is not the same as "you can see it."** It says the words resolved to one record, which
is a decision about the sentence, not an observation of the shelf. Three things can still leave you
looking at an unchanged wall, and each has a different fix:

| `spotlight` | `lights_on` | What happened |
|---|---|---|
| `lit` | `true` | The record is lit. |
| `lit` | `false` | Master power is off, so the spotlight is stored and shows nothing. |
| `not_on_shelf` | either | The record is in no segment — there is no light to turn on. Shelve it in the app. |
| `unreachable` | either | Its controller could not be reached. |

`found.lit` folds all of that into the one boolean worth branching on, and is deliberately false
when it cannot be sure — including against a base station older than 0.61.0, which sent no
`spotlight` field and sometimes reported success when nothing had happened.

`speech` always says which of these it was, so passing it straight to a notification (as above)
tells you what went wrong without decoding anything.

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
