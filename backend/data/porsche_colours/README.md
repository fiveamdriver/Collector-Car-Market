# Porsche factory exterior colours (standard + special)

The reference for "is this colour a factory colour for this car and model year?"
A colour listed here for a car's model and model year is a factory colour,
**never paint-to-sample**, special-colour tier included.

Sources: Porsche Classic's official colour PDFs (porsche.com → Classic → models →
colour information), downloaded 2026-11-03 by the repo owner into
`~/Porsche Website coLORS/`. The PDFs are Porsche's and are **not committed**
(public repo); what's committed is facts extracted from them, each with its
source file and page.

| File | What | How it was made |
|---|---|---|
| `factory_palettes_overview.json` | 1,620 rows: chart, paint code, German name, paint system, model year | `parse_overview_charts.py` over `pdftotext -layout` of the `*-overview-paint-colours.pdf` charts ("Lackfarben bei Porsche-Fahrzeugen", printed 2002): F/G-Body 911, 964, 993, 996 Carrera, 996 Turbo, 986 Boxster. Every X is assigned to the nearest year column; the parser raises if one is >5 chars off. Spot-checked against the rendered pages (996 p1, 993 p3, 964 p4): exact. |
| `brochure_transcription.py` | 20 brochures, 273 entries: English names, short codes, tier (solid / metallic / special) | Hand transcription of the scanned model-year brochures (no text layer). File + page on every brochure. |

Caveats
- The overview charts stop at the year they were printed (2002): the 996 column for
  MY2005 is empty and the 993 chart ends at MY1997. Brochures fill some of that.
- Brochures list the standard range (and, for the 997, "special exterior colours");
  the overview charts list every factory colour. Use both.
- Several file names don't match their content: "964-1995" is the MY1995 993/928
  brochure, "997-2006" is the 997 Turbo brochure, "997-2012" is the 991.1 launch
  brochure, "993-1998" and "996-1998" are the same brochure. Recorded per entry.
- Not covered yet: 991, 992, 997 MY2011, GT/RS-specific palettes beyond the 996 GT2.
