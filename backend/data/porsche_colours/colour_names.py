"""
German chart names -> Porsche's English names, for the overview charts
(factory_palettes_overview.json). Only names whose English form is certain are
mapped; "src" says why. Anything absent stays untranslated, and a palette with
untranslated colours is treated as partial by the dry run (weaker evidence).

bilingual = printed side by side in a Porsche brochure (993/996 MY1998-99 cards
            or the 964/993 cards with short codes, same model year)
standard  = Porsche's own long-standing English name for that paint
inferred  = paired by model year (the only colour of that kind new on both the chart
            and the same-year card); treated like the others but flagged here
"""

DE_EN = {
    "schwarz": ("Black", "bilingual"),
    "schwarz-met.": ("Black Metallic", "bilingual"),
    "schwarz-perlcolor": ("Black Metallic", "bilingual"),
    "indischrot": ("Guards Red", "bilingual"),
    "inidischrot": ("Guards Red", "bilingual"),      # Porsche's typo in the 993 chart
    "grandprixweiß": ("Grand Prix White", "standard"),
    "speedgelb": ("Speed Yellow", "standard"),
    "pastellgelb": ("Pastel Yellow", "bilingual"),
    "firnweiß": ("Glacier White", "bilingual"),
    "arktissilber-met.": ("Arctic Silver Metallic", "bilingual"),
    "polarsilber-met.": ("Polar Silver Metallic", "standard"),
    "polarsilber-met": ("Polar Silver Metallic", "standard"),
    "oceanblau-met.": ("Ocean Blue Metallic", "bilingual"),
    "zenitblau-met.": ("Zenith Blue Metallic", "bilingual"),
    "arenarot-met.": ("Arena Red Metallic", "bilingual"),
    "arenarot-perlcolor": ("Arena Red Metallic", "bilingual"),
    "libelltürkis-met.": ("Ocean Jade Metallic", "bilingual"),
    "paladio-met.": ("Mirage Metallic", "bilingual"),
    "paladio-perlcolor": ("Mirage Metallic", "bilingual"),
    "vesuvio-met.": ("Vesuvio Grey Metallic", "bilingual"),
    "vesuvio-perlcolor": ("Vesuvio Grey Metallic", "bilingual"),
    "basaltschwarz met.": ("Basalt Black Metallic", "standard"),
    "GT-silber met.": ("GT Silver Metallic", "standard"),
    "atlasgrau met.": ("Atlas Grey Metallic", "standard"),
    "carraraweiß": ("Carrara White", "standard"),
    "biarritzweiß": ("Biarritz White", "standard"),
    "fayencegelb": ("Fayence Yellow", "standard"),
    "lapisblau-met.": ("Lapis Blue Metallic", "standard"),
    "carmonarot met.": ("Carmon Red Metallic", "standard"),
    "sealgrau-met.": ("Seal Grey Metallic", "standard"),
    "meridian-met.": ("Meridian Metallic", "standard"),
    "lagogrün metallic": ("Lagoon Green Metallic", "standard"),
    "tannengrün-met.": ("Forest Green Metallic", "standard"),
    "cobaltblau-met.": ("Cobalt Blue Metallic", "bilingual"),
    "nachtblau-met.": ("Midnight Blue Metallic", "bilingual"),
    "nachtblau-perlcolor": ("Midnight Blue Metallic", "bilingual"),
    "nachtblau perlcolor": ("Midnight Blue Metallic", "bilingual"),
    "schiefer-met.": ("Slate Grey Metallic", "bilingual"),
    "irisblau-met.": ("Iris Blue Metallic", "bilingual"),
    "irisblau-perlcolor": ("Iris Blue Metallic", "bilingual"),
    "aventuragrün-perlcolor": ("Aventura Green Metallic", "bilingual"),
    "amazonasgrün-perlcolor": ("Amazon Green Metallic", "bilingual"),
    "rivierablau": ("Riviera Blue", "bilingual"),
    "amarantviolett": ("Amaranth Violet", "bilingual"),
    "blautürkis": ("Blue Turquoise", "bilingual"),
    "türkis-perlcolor": ("Turquoise Metallic", "bilingual"),
    "viola-met.": ("Viola Metallic", "standard"),
    "viola-perlcolor": ("Viola Metallic", "standard"),
    "violettchromaflair": ("Violet Chromaflair", "standard"),
    "dunkelblau": ("Dark Blue", "standard"),
    "wimbledongrün-met.": ("Wimbledon Green Metallic", "bilingual"),
    "orientrot-met.": ("Orient Red Metallic", "standard"),
    "maritimblau": ("Maritime Blue", "bilingual"),
    "mintgrün": ("Mint Green", "bilingual"),
    "signalgrün": ("Signal Green", "bilingual"),
    "korallenrot-met.": ("Coral Red Metallic", "bilingual"),
    "korallenrot-met": ("Coral Red Metallic", "bilingual"),
    "oakgrün-met.": ("Oak Green Metallic", "bilingual"),
    "oakgrün-met": ("Oak Green Metallic", "bilingual"),
    "amethyst-perlcolor": ("Amethyst Metallic", "bilingual"),
    "horizontblau-met.": ("Horizon Blue Metallic", "bilingual"),
    "sternrubin": ("Rubystone Red", "bilingual"),
    "himbeerrot-met.": ("Rhodamine Red Metallic", "inferred"),   # only red metallic new on both the MY1993 chart and the MY1993 card (A7)
    "hombeerrot-met.": ("Rhodamine Red Metallic", "inferred"),
    "veilchenblau-met.": ("Violet Blue Metallic", "inferred"),
    "steingrau-met.": ("Stone Grey Metallic", "standard"),
    "cassisrot-met.": ("Cassis Red Metallic", "standard"),
    "diamantblau-met.": ("Diamond Blue Metallic", "standard"),
    "marineblau-met.": ("Marine Blue Metallic", "standard"),
    "veneziablau-met": ("Venetian Blue Metallic", "standard"),
    "cherryrot": ("Cherry Red", "standard"),
    "limonengelb": ("Lime Yellow", "standard"),
    "silber-met.": ("Silver Metallic", "standard"),
    "preußischblau-met.": ("Prussian Blue Metallic", "standard"),
    "granatrot-met.": ("Garnet Red Metallic", "standard"),
    "weißgold-met.": ("White Gold Metallic", "standard"),
    "meteor-met.": ("Meteor Metallic", "standard"),
    "irischgrün": ("Irish Green", "bilingual"),
    "signalorange": ("Signal Orange", "standard"),
    "blutorange": ("Blood Orange", "standard"),
    "gulfblau": ("Gulf Blue", "standard"),
    "gulforange": ("Gulf Orange", "standard"),
    "vipergrün": ("Viper Green", "standard"),
    "signalgelb": ("Signal Yellow", "standard"),
    "hellelfenbein": ("Light Ivory", "bilingual"),
    "elfenbein": ("Ivory", "standard"),
    "albertblau": ("Albert Blue", "standard"),
    "mexicoblau": ("Mexico Blue", "standard"),
    "talbotgelb": ("Talbot Yellow", "standard"),
    "minervablau": ("Minerva Blue", "standard"),
}

# Chart entries that are not a colour: "nach Muster (Wahl)" (code 099) is
# Porsche's own "to sample, customer's choice" — the PTS order itself.
NOT_A_COLOUR = {"nach Muster (Wahl)"}
