"""
Which variant cards each street-911 generation has, and how a variant maps when a
car moves generation. Mirrors frontend/src/data/taxonomy.js for the generations a
facelift-boundary move can land in; used by data/migrate_facelift_boundaries.py
and by enrichment (app/services/derived.py) when a VIN re-files a car.
"""

# Cards per generation — mirrors frontend/src/data/taxonomy.js for the
# generations a boundary move can land in.
CARDS = {
    "G-Body": None,  # G-Body variants are year-derived; only Speedster moves here
    "964": {"Carrera 2", "Carrera 4", "Carrera RS", "RS 3.8", "RS America",
            "Turbo", "Turbo 3.6", "Turbo S", "Speedster", "Targa", "Cabriolet"},
    "993": {"Carrera", "Carrera 4", "Carrera S", "Carrera 4S", "Carrera RS",
            "Turbo", "Turbo S", "GT2", "Targa", "Cabriolet"},
    "996.1": {"Carrera", "Carrera 4", "GT3", "Cabriolet"},
    "996.2": {"Carrera", "Carrera 4", "Carrera 4S", "Turbo", "Turbo S", "GT3",
              "GT3 RS", "GT2", "Targa", "Cabriolet"},
    "997.1": {"Carrera", "Carrera 4", "Carrera S", "Carrera 4S", "Turbo", "GT3",
              "GT3 RS", "GT2", "Targa", "Cabriolet"},
    "997.2": {"Carrera", "Carrera 4", "Carrera S", "Carrera 4S", "Carrera GTS",
              "Turbo", "Turbo S", "GT3", "GT3 RS", "GT3 RS 4.0", "GT2 RS",
              "Sport Classic", "Speedster", "Targa", "Cabriolet"},
    "991.1": {"Carrera", "Carrera 4", "Carrera S", "Carrera 4S", "Carrera GTS",
              "Turbo", "Turbo S", "GT3", "GT3 RS", "R", "Targa", "Cabriolet"},
    "991.2": {"Carrera", "Carrera 4", "Carrera S", "Carrera 4S", "Carrera T",
              "Carrera GTS", "Turbo", "Turbo S", "GT3", "GT3 RS", "GT2 RS",
              "Speedster", "Targa", "Cabriolet"},
    "992.1": {"Carrera", "Carrera 4", "Carrera S", "Carrera 4S", "Carrera T",
              "Carrera GTS", "Turbo", "Turbo S", "GT3", "GT3 RS", "S/T",
              "Sport Classic", "Dakar", "Targa", "Cabriolet"},
    "992.2": {"Carrera", "Carrera 4", "Carrera S", "Carrera 4S", "Carrera T",
              "Carrera GTS", "Turbo", "Turbo S", "GT3", "GT3 RS", "Targa", "Cabriolet"},
}
# Same car, different card name in the target generation.
EQUIV = {
    ("Carrera 2", "993"): "Carrera",
    ("Carrera 3.2", "964"): "Carrera 2",
    ("Carrera", "964"): "Carrera 2",
}


def target_variant(variant: str, new_gen: str) -> str | None:
    cards = CARDS.get(new_gen)
    if cards is None:
        return variant if variant == "Speedster" else None
    if variant in cards:
        return variant
    return EQUIV.get((variant, new_gen))




# Model years (US-market MY; European MY where it ran longer) each variant card
# was built, per phase. Sources, checked 2026-11-03: Porsche Classic model pages
# (996, 997), Wikipedia generation pages, Stuttcars research hubs, Porsche USA
# 2025 lineup release, Rennlist production threads. Used by
# data/audit_generations.py to decide whether a car's placement is ambiguous.
VARIANT_MY = {
    "996.1": {"Carrera": (1999, 2001), "Carrera 4": (1999, 2001),
              "Cabriolet": (1999, 2001), "GT3": (1999, 2001)},
    "996.2": {"Carrera": (2002, 2004), "Carrera 4": (2002, 2004), "Carrera 4S": (2002, 2005),
              "Targa": (2002, 2005), "Cabriolet": (2002, 2005), "Turbo": (2001, 2005),
              "Turbo S": (2005, 2005), "GT2": (2001, 2005), "GT3": (2003, 2005),
              "GT3 RS": (2004, 2005)},
    "997.1": {"Carrera": (2005, 2008), "Carrera S": (2005, 2008), "Carrera 4": (2006, 2008),
              "Carrera 4S": (2006, 2008), "Targa": (2007, 2008), "Cabriolet": (2005, 2008),
              "Turbo": (2007, 2009), "GT3": (2007, 2008), "GT3 RS": (2007, 2009),
              "GT2": (2008, 2009)},
    "997.2": {"Carrera": (2009, 2012), "Carrera S": (2009, 2012), "Carrera 4": (2009, 2012),
              "Carrera 4S": (2009, 2013), "Targa": (2009, 2013), "Cabriolet": (2009, 2013),
              "Carrera GTS": (2011, 2012), "Turbo": (2010, 2013), "Turbo S": (2011, 2013),
              "GT3": (2009, 2012), "GT3 RS": (2010, 2011), "GT3 RS 4.0": (2011, 2012),
              "GT2 RS": (2011, 2012), "Sport Classic": (2010, 2010), "Speedster": (2011, 2011)},
    "991.1": {"Carrera": (2012, 2016), "Carrera S": (2012, 2016), "Carrera 4": (2013, 2016),
              "Carrera 4S": (2013, 2016), "Cabriolet": (2012, 2016), "Targa": (2014, 2016),
              "Carrera GTS": (2015, 2016), "Turbo": (2014, 2016), "Turbo S": (2014, 2016),
              "GT3": (2014, 2016), "GT3 RS": (2016, 2016), "R": (2016, 2016)},
    "991.2": {"Carrera": (2017, 2019), "Carrera S": (2017, 2019), "Carrera 4": (2017, 2019),
              "Carrera 4S": (2017, 2019), "Cabriolet": (2017, 2019), "Targa": (2017, 2019),
              "Carrera GTS": (2017, 2019), "Carrera T": (2018, 2019), "Turbo": (2017, 2019),
              "Turbo S": (2017, 2019), "GT3": (2018, 2019), "GT3 RS": (2019, 2019),
              "GT2 RS": (2018, 2019), "Speedster": (2019, 2019)},
    "992.1": {"Carrera": (2020, 2024), "Carrera S": (2020, 2024), "Carrera 4": (2020, 2024),
              "Carrera 4S": (2020, 2024), "Cabriolet": (2020, 2024), "Targa": (2021, 2024),
              "Carrera GTS": (2022, 2024), "Carrera T": (2023, 2024), "Turbo": (2021, 2025),
              "Turbo S": (2021, 2025), "GT3": (2022, 2024), "GT3 RS": (2023, 2025),
              "S/T": (2024, 2025), "Dakar": (2023, 2024), "Sport Classic": (2023, 2023)},
    "992.2": {"Carrera": (2025, 2099), "Carrera S": (2025, 2099), "Carrera 4S": (2026, 2099),
              "Cabriolet": (2025, 2099), "Targa": (2025, 2099), "Carrera GTS": (2025, 2099),
              "Carrera T": (2025, 2099), "Turbo S": (2026, 2099), "GT3": (2025, 2099)},
}


def built_in(gen: str, variant: str, model_year: int) -> bool:
    """True if `variant` was built as a `gen` car in `model_year` (per VARIANT_MY)."""
    span = VARIANT_MY.get(gen, {}).get(variant)
    return bool(span) and span[0] <= model_year <= span[1]
