// Keyed [modelSlug][generation][variant]
const VARIANT_DESCRIPTIONS = {
  '911': {
    'F-Body': {
      '911':                       'The original 911, launched in 1963 with a 2.0-liter air-cooled flat-six producing 130 horsepower in a lightweight coupe designed by Butzi Porsche. Early examples are prized for their unassisted, analog driving character and historical significance as the founding car of the 911 lineage.',
      '911S':                      'The high-performance F-Body variant, fitted with a higher-compression engine, Fuchs alloy wheels, and ventilated disc brakes over the base car. It has become one of the most desirable early 911s, with documented examples in excellent condition commanding significant collector premiums.',
      '911T':                      'The entry-level F-Body 911 used a lower-compression engine and simpler specification to reduce the purchase price while still delivering the core 911 experience. It remains the most affordable path into F-Body ownership and is appreciated for its authenticity and mechanical accessibility.',
      '911E':                      'Positioned between the T and S, the E offered mechanical fuel injection on later examples alongside a comfortable touring specification that balanced performance with usability. It is increasingly valued by collectors who seek the mid-range F-Body experience without the premium commanded by the 911S.',
      '911L':                      'Produced only for the 1968 model year, the 911L was the luxury-oriented variant positioned just above the T before the range was reorganized. Its single-year production run makes it genuinely rare and historically significant as a transitional model in early 911 development.',
      '911R':                      'Built in 1967 for racing homologation, only 23 911Rs were produced, making it one of the rarest and most consequential Porsches from any era. Factory-stripped to minimum weight with a 210-horsepower engine, surviving examples have sold for millions at auction.',
      'Carrera RS 2.7':            'Produced in 1972–1973 to homologate the car for Group 4 racing, the Carrera RS 2.7 featured a bored-out 2.7-liter engine producing 210 horsepower and the iconic "ducktail" rear spoiler. Approximately 1,580 were built, most in Touring specification alongside roughly 200 stripped-out 900-kilogram Lightweights, which command the largest premiums. It is widely regarded as one of the most important road cars Porsche ever produced.',
      'S/T':                       'The 911 S/T was a factory-built racing variant based on the 911S, stripped to minimum weight for events including the Targa Florio and Tour de France Automobile. Only approximately 70 were produced between 1970 and 1972, placing them among the rarest and most historically important F-Body 911s.',
      'Targa':'Introduced for 1967, the Targa answered feared US convertible regulations with a removable roof panel and a fixed stainless-steel roll hoop, initially behind a zip-out plastic rear window replaced by fixed glass from 1969. Early soft-window cars are the most sought-after F-Body Targas, and the body style carries a discount to equivalent coupes.',
    },
    'G-Body': {
      'Speedster':             'Produced in 1989 as a limited final expression of the G-Body 911, the Speedster featured a steeply raked windscreen and distinctive double-hump tonneau inspired by the 356 Speedster. Approximately 2,100 were built, and narrow-body manual examples are particularly sought after.',
      'Turbo 3.3 Slant Nose':  'A factory Sonderwunsch special, the Slant Nose (Flachbau) featured flush front fenders with pop-up headlights directly inspired by the 935 race car. Genuine factory-built examples are significantly rarer than standard 930 Turbos and command substantial premiums.',
      '930 Turbo':             'The 930 introduced turbocharging to the 911 lineup in 1975 with a 3.0-liter engine later enlarged to 3.3 liters and 300 horsepower, earning a fearsome reputation for its on-boost character. Its wide-body stance and whale-tail spoiler defined an era, and clean unmolested examples have appreciated sharply.',
      'Carrera 2.7 MFI':       'The early G-Body Carrera 2.7 carried the mechanically fuel-injected engine from the F-Body era into the new impact-bumper generation, representing direct continuity of the high-performance 911 lineage. It occupies a transitional position valued for its connection to the pre-impact bumper era.',
      'Carrera 2.7':           'The standard G-Body Carrera 2.7 used Bosch K-Jetronic fuel injection producing around 165 horsepower in the new body, serving as the performance flagship before the SC arrived. It remains an affordable and authentic entry into air-cooled G-Body 911 ownership.',
      'Carrera 3.2':           'Powered by the definitive 3.2-liter flat-six producing 231 horsepower, the Carrera 3.2 was the final and most refined naturally aspirated G-Body 911, produced from 1984 to 1989. It is widely regarded as one of the finest-driving air-cooled 911s, balancing engine character, reliability, and chassis dynamics.',
      'SC':                    'The 911SC used a 3.0-liter flat-six and served as the sole non-turbo 911 from 1978 to 1983, bridging the Carrera 2.7 era and the 3.2. Valued for mechanical robustness and clean proportions, Targa and Cabriolet variants are particularly popular.',
      '911S':                  'The G-Body 911S was produced in the early years of the generation as a more sporting specification over the standard 911 before Porsche simplified the lineup. Documented original examples are valued by collectors of early G-Body cars as a distinct and historically important variant.',
      '911':                   'The base G-Body 911 used the 2.7-liter engine in a lower state of tune and served as the entry-level 911 throughout the mid-1970s. Well-preserved examples represent some of the most affordable paths to air-cooled 911 ownership from this era.',
      'Targa':'The Targa roof was offered across nearly the whole G-Body range, from the base 911 and SC through the Carrera 3.2 and the 930 Turbo, using a removable panel above a fixed hoop. It is the most numerous open air-cooled 911 body style and generally trades below equivalent coupes, making it one of the most affordable routes into the generation.',
    },
    '964': {
      'Carrera':   'The 964 Carrera represented the 911\'s first comprehensive redesign in over two decades, with 85% new components including coil-spring suspension, power steering, and ABS alongside a 247-horsepower 3.6-liter engine. The rear-wheel-drive Carrera 2 with a manual gearbox is now the most sought-after base 964 for its pure driving character.',
      'Carrera RS': 'Built for Group N homologation, the 964 Carrera RS featured a lightweight body, a 260-horsepower 3.6-liter engine, and purpose-built suspension not shared with the standard car. Originally sold only in Europe in approximately 2,000 examples, it is among the most driver-focused and collectible 964s.',
      'RS 3.8':     'The street-legal Carrera RS 3.8 was built by Porsche\'s motorsport department at Weissach around an enlarged 300-horsepower 3.8-liter flat-six, wearing the Turbo widebody and a fixed rear wing. Approximately 55 were built, making it one of the rarest and most valuable road-going 964s; its competition counterpart, the RSR 3.8, is catalogued under the 911 race cars.',
      'RS America': 'Porsche\'s lightweight homologation special for the US market deleted air conditioning, rear seats, and sound deadening while retaining the standard 247-horsepower engine. Around 700 were produced for 1993–1994 and are increasingly collected as the American counterpart to the European Carrera RS.',
      'Turbo':      'The 964 Turbo used the 3.3-liter turbocharged engine carried over from the G-Body producing 320 horsepower, making it the last 911 Turbo to use the older architecture before the 3.6-liter arrived. Dramatic wide-body stance and a strong collector following have kept values firm.',
      'Turbo S':    'The rarest factory 964, the Turbo S was produced in only 86 examples as a stripped lightweight version of the Turbo with a 381-horsepower engine. Survivors are among the most valuable air-cooled 911s and appear at auction very infrequently.',
      'Speedster':  'The 964 Speedster used a steeply raked windscreen and dual-hump tonneau in both standard and wide-body Turbo-look specifications. Approximately 930 were produced, and wide-body Turbo-look examples command the highest values among 964 Speedster collectors.',
      'Carrera 2':'The Carrera 2 is the rear-wheel-drive 964, introduced a year after the all-wheel-drive Carrera 4 with the same 247-horsepower 3.6-liter engine in a lighter, mechanically simpler car. Manual C2 coupes are the most sought-after standard 964s; lots catalogued specifically as \'Carrera 2\' are grouped here rather than with the generic Carrera.',
      'Carrera 4':'The 964 Carrera 4 introduced all-wheel drive to the 911 at the generation\'s 1989 launch, using a sophisticated and comparatively heavy driveline with a locking center differential. It trades at a discount to the rear-drive Carrera 2 among driver-focused buyers, which makes it one of the more attainable ways into a 964.',
      'Targa':    'The 964 Targa carried the classic removable-panel-and-hoop format into the new generation in both Carrera 2 and Carrera 4 form. It was built in modest numbers before the glass-roof 993 replaced the design, making it the last of the traditional hoop Targas.',
    },
    '993': {
      'Carrera':   'The 993 Carrera delivered the definitive air-cooled 911 in its final form, with a 272-horsepower 3.6-liter flat-six, fully independent rear suspension, and a body that remains one of the most admired 911 silhouettes. Rear-wheel-drive Carrera 2 coupes with manual gearboxes have seen the sharpest appreciation as collectors pursue the last air-cooled generation.',
      'Carrera S':  'A wider-bodied 993 using the Turbo\'s platform components and flared rear arches, the Carrera S offered the wide-body stance with a naturally aspirated rear-wheel-drive drivetrain. Its rarity and unique specification have made it one of the most desirable naturally aspirated 993 variants.',
      'Carrera RS': 'Built for club racing homologation in 1995, the 993 Carrera RS used a 300-horsepower 3.8-liter engine with purpose-built suspension in a stripped, lightweight body. Around 1,014 were produced, and they are considered among the finest driver-focused Porsches of the air-cooled era.',
      'Turbo':      'The 993 Turbo was a landmark achievement, introducing twin-turbocharging and all-wheel drive to the 911 Turbo simultaneously, producing 408 horsepower in a dramatically more tractable package than the 930. Porsche\'s final air-cooled Turbo is consistently one of the most liquid and desired 911s on the collector market.',
      'Turbo S':    'The 993 Turbo S produced 450 horsepower in a higher-specification Turbo with additional aerodynamics and interior upgrades over the standard car. Approximately 345 were built, making them among the rarest and most valuable air-cooled Porsches at auction.',
      'GT2':        'The 993 GT2 used a twin-turbocharged 3.6-liter engine producing 430 horsepower in a rear-wheel-drive car without the Turbo\'s all-wheel-drive system, creating a demanding and thrilling driving experience. Production of approximately 173 road-legal examples makes them among the rarest and most extreme air-cooled 911s ever sold.',
      'Carrera 4': 'The 993 Carrera 4 used a lighter, simpler all-wheel-drive system than the 964\'s, shedding around 50 kilograms while adding genuine all-weather capability to the last air-cooled 911. It has historically trailed the rear-drive Carrera in value, though the gap has narrowed as the generation as a whole has appreciated.',
      'Carrera 4S':'The Carrera 4S combined the Turbo\'s wide body, suspension, and brakes with the naturally aspirated flat-six and all-wheel drive, giving the widebody stance without forced induction. It is among the most desirable 993s after the Turbo and RS, and clean manual examples are consistently strong sellers.',
      'Targa':     'The 993 Targa abandoned the roll hoop for a sliding glass roof panel that retracted beneath the rear window, the first 911 to use the design. Roughly 4,500 were built, and it remains a distinctive and comparatively affordable path into air-cooled 993 ownership.',
    },
    '996.1': {
      'Carrera':  'The 996.1 Carrera introduced Porsche\'s first water-cooled 911 engine — a 3.4-liter flat-six producing 296 horsepower — in an all-new body that proved controversial for its shared headlights with the Boxster. Clean, unmolested examples have gained renewed appreciation as accessible modern classics.',
      'Carrera S': 'A higher-specification Carrera available in limited configurations for the 996.1 generation, offering upgraded equipment over the base model. These represent relatively uncommon configurations within the 996.1 auction record.',
      'Turbo':     'The 996.1 Turbo used a twin-turbocharged 3.6-liter flat-six producing 415 horsepower with all-wheel drive in a far more tractable package than its air-cooled predecessors. It introduced a new era of accessible everyday supercar performance and remains one of the best-value turbocharged 911s available.',
      'GT3':       'The original 911 GT3 established the track-focused naturally aspirated lineage with a 360-horsepower 3.6-liter Metzger engine and a motorsport-derived chassis. Despite the styling controversy of its era, the 996.1 GT3 is now recognized as the founding car of one of Porsche\'s most celebrated model lines.',
      'Carrera 4':'The 996 Carrera 4 added all-wheel drive with a viscous-coupling front drive and standard PSM stability control to the first water-cooled 911. It typically sits below the rear-drive Carrera in value, making it one of the least expensive 911s on the market despite its all-weather usability.',
    },
    '996.2': {
      'Carrera':  'The 996.2 Carrera received distinct new headlights addressing the primary criticism of the 996.1, alongside an enlarged 3.6-liter engine producing 316 horsepower. It remains one of the most affordable modern 911s, with growing appreciation among collectors who value its honest driving experience.',
      'Carrera S': 'A higher-specification Carrera available in certain configurations within the 996.2 generation, offering upgraded equipment over the standard model. These represent relatively uncommon configurations among 996.2 Carreras found at auction.',
      'Turbo':     'The 996.2 Turbo carried the 415-horsepower twin-turbocharged engine with styling updates and the X50 power kit option raising output to 450 horsepower. Values have remained stable, making it one of the most compelling performance-per-dollar propositions in the modern 911 Turbo lineage.',
      'Turbo S':   'The 996 Turbo S arrived for 2004 with the 450-horsepower X50 engine as standard, ceramic composite brakes, Sport Chrono, and extensive additional equipment in approximately 1,300 examples. It represents the ultimate factory 996 Turbo specification and commands a firm premium over standard Turbo cars.',
      'GT3':       'The 996.2 GT3 upgraded to a higher-revving 3.6-liter Metzger engine producing 381 horsepower with refined aerodynamics and chassis tuning over the 996.1 car. It is recognized as an undervalued entry to the GT3 lineage, delivering genuine motorsport character at a significant discount to later generations.',
      'GT3 RS':    'The original GT3 RS, produced in limited numbers for 2003–2004 as the first wide-body track-focused 911, offered 381 horsepower in a car stripped beyond the standard GT3. Its combination of extreme rarity and pioneering RS specification has made it one of the most desirable 996-era collector cars.',
      'GT2':       'The 996 GT2 produced 483 horsepower from its twin-turbocharged 3.6-liter engine in a rear-wheel-drive 911, earning a fearsome reputation among performance car enthusiasts. Around 1,300 road-legal examples were built, and appreciation has been steady as the GT2 lineage gains historical recognition.',
      'Carrera 4': 'The facelifted Carrera 4 paired all-wheel drive with the enlarged 3.6-liter engine and the revised headlights that resolved the 996.1\'s most criticized feature. It is among the most affordable modern 911s, bought primarily as a usable all-weather car rather than as a collectible.',
      'Carrera 4S':'The 996 Carrera 4S arrived with the facelift wearing the Turbo\'s wide body, brakes, and suspension around the naturally aspirated 3.6-liter engine and all-wheel drive. Turbo looks at a fraction of Turbo money have made it the most popular 996 Carrera variant on the collector market.',
      'Targa':     'The 996 Targa revived the sliding glass roof and added a separately opening rear glass hatch for luggage access. Production was small next to coupes and cabriolets, making it one of the rarest body styles in an otherwise plentiful generation.',
    },
    '997.1': {
      'Carrera':  'The 997.1 Carrera restored the classic round headlight design and delivered a 321-horsepower 3.6-liter naturally aspirated flat-six in a much-praised return to form after the 996. Clean manual Carreras represent the most accessible naturally aspirated 997 on the market.',
      'Carrera S': 'The 997.1 Carrera S added a 3.8-liter engine producing 355 horsepower and PASM adaptive suspension, and is widely regarded as the sweet spot of the 997.1 naturally aspirated range. Manual-gearbox S models have seen consistent demand from buyers seeking the complete 997.1 experience.',
      'Turbo':     'The 997.1 Turbo produced 473 horsepower from its twin-turbocharged 3.6-liter engine with all-wheel drive and PASM, establishing a new benchmark for everyday supercar performance. The availability of a manual gearbox makes certain 997.1 Turbo examples particularly desirable.',
      'GT3':       'The 997.1 GT3 used a 409-horsepower 3.6-liter naturally aspirated engine with a motorsport-derived chassis and no all-wheel drive, cementing the GT3\'s reputation as Porsche\'s definitive driver\'s 911. It remains one of the most engaging 911s ever produced.',
      'GT3 RS':    'The 997.1 GT3 RS added a lightweight wide body, revised aerodynamics, and track-focused setup in the first RS to establish a clear identity separate from the standard GT3. Values for clean examples have climbed steadily, commanding a firm premium over comparable GT3 cars.',
      'GT2':       'Producing 523 horsepower from a twin-turbocharged 3.6-liter engine in a rear-wheel-drive 911, the 997.1 GT2 was the most powerful and demanding road-legal 911 at its 2007 launch. Approximately 1,200 were produced, and its brutal performance credentials have sustained consistent demand at auction.',
      'Carrera 4': 'From the 997 onward every Carrera 4 wore the wide body, giving the all-wheel-drive car a visual distinction over the rear-drive Carrera alongside the same 3.6-liter naturally aspirated engine. Wide-body looks and all-weather traction keep demand steady, though manual rear-drive cars remain the enthusiast\'s choice.',
      'Carrera 4S':'The 997.1 Carrera 4S combined the 355-horsepower 3.8-liter engine with all-wheel drive, PASM, and the wide body, making it the most comprehensively equipped naturally aspirated 997.1. Manual examples in good condition command a clear premium over Tiptronic cars.',
      'Targa':     'The 997 Targa was offered only as the all-wheel-drive Targa 4 and Targa 4S, with a large sliding glass roof and an opening rear hatch over the wide body. Built in small numbers relative to coupes and cabriolets, it is the rarest 997 body style.',
    },
    '997.2': {
      'Carrera':      'The 997.2 Carrera introduced direct fuel injection, boosting the 3.6-liter engine to 345 horsepower and making it the last naturally aspirated 911 Carrera before turbocharging became universal. Clean manual examples are increasingly viewed as the most accessible naturally aspirated modern 911.',
      'Carrera S':    'The 997.2 Carrera S used a revised 3.8-liter DFI engine producing 385 horsepower in the most refined naturally aspirated Carrera S before the 991.2 brought forced induction to the lineup. Values have firmed as collectors recognize it as the high-water mark of the large-displacement naturally aspirated Carrera S.',
      'Carrera GTS':  'Introduced for 2011, the 997.2 GTS offered a 408-horsepower 3.8-liter engine, the wider Carrera 4S body, and standard sport equipment at a competitive price over the Carrera S. It has become one of the most desirable 997.2 variants, with values tracking above comparable Carrera S examples.',
      'Turbo':        'The 997.2 Turbo adopted a new single-turbo-per-bank design with the 3.8-liter engine producing 500 horsepower — a significant step in performance and refinement over the 997.1. The availability of a manual gearbox on early examples makes certain 997.2 Turbos among the most collectible turbocharged 911s.',
      'Turbo S':      'The 997.2 Turbo S produced 530 horsepower as the most powerful standard-production 911 of its era, with standard PCCB ceramic brakes, Sport Chrono, and enhanced aerodynamics. It commands a firm premium over the base Turbo and is regarded as a benchmark supercar of the early 2010s.',
      'GT3':          'The 997.2 GT3 improved on its predecessor with a higher-revving 3.8-liter Metzger engine producing 435 horsepower, in the last GT3 powered by the naturally aspirated Metzger architecture. Clean examples continue to appreciate as the final generation of that specific engine lineage.',
      'GT3 RS':       'The 997.2 GT3 RS used a 450-horsepower 3.8-liter engine in a wide body with an aggressive aerodynamic package that set a new benchmark for street-legal 911 downforce. Values have risen firmly alongside the RS 4.0 as the last two naturally aspirated wide-body 997 GT3 variants.',
      'GT3 RS 4.0':   'The ultimate naturally aspirated 997, the GT3 RS 4.0 used a 4.0-liter racing-derived engine producing 500 horsepower in only 600 road-legal examples. It is widely regarded as one of the greatest driver\'s cars ever built and consistently achieves among the highest prices of any modern 911 at auction.',
      'GT2 RS':       'The 997.2 GT2 RS produced 620 horsepower from its turbocharged 3.6-liter engine in a rear-wheel-drive wide-body 911 that was the most powerful Porsche ever offered when launched in 2010. With only 500 produced, it has become one of the most valuable modern 911s at auction.',
      'Sport Classic': 'Produced in only 250 examples for 2010, the Sport Classic featured a ducktail spoiler, double-bubble roof, Fuchs-inspired wheels, and a 408-horsepower manual-only drivetrain as a tribute to classic 911 design. Values have roughly tripled since launch, establishing it as one of the most important modern 911 collector cars.',
      'Speedster':    'The 997.2 Speedster was produced in only 356 hand-built examples for 2011 with a manual-only GTS-spec engine in a bespoke open body. Its extremely limited production and connection to Porsche tradition have made it one of the most sought-after modern 911s.',
      'Carrera 4': 'The 997.2 Carrera 4 took the direct-injection 3.6-liter engine and the new PDK gearbox into the wide-body all-wheel-drive car. The DFI engine avoids the intermediate-shaft concerns of earlier water-cooled cars, which has helped 997.2 values hold up better than the 997.1\'s.',
      'Carrera 4S':'The 997.2 Carrera 4S used the 385-horsepower direct-injection 3.8-liter engine with all-wheel drive, PASM, and the wide body, available with either PDK or a manual gearbox. Manual cars are the ones collectors chase, and the 997.2 is widely regarded as the high point of the pre-991 era.',
      'Targa':     'The 997.2 Targa 4 and Targa 4S carried the sliding-glass-roof design into the direct-injection facelift with PDK availability. Low production and the practical all-weather roof give it a small but committed following.',
    },
    '991.1': {
      'Carrera':     'The 991.1 Carrera marked the 911\'s first significant dimensional change in decades alongside the final naturally aspirated 3.4-liter flat-six producing 350 horsepower in the base Carrera. Clean manual examples are viewed as among the most accessible genuinely naturally aspirated modern 911s.',
      'Carrera S':    'The 991.1 Carrera S used a 3.8-liter naturally aspirated engine producing 400 horsepower with PASM as standard and is considered the sweet spot of the naturally aspirated 991.1 range. Its naturally aspirated character has made it increasingly valued as turbocharging became universal with the 991.2.',
      'Carrera T':    'Introduced midcycle as a lightweight touring-focused variant, the Carrera T deleted rear seats and sound deadening while adding a shorter gear lever and mechanical rear differential. It is widely regarded as the most analog and driver-focused naturally aspirated 991.1 Carrera.',
      'Carrera GTS':  'The 991.1 GTS offered a 430-horsepower 3.8-liter engine in the wider Carrera 4S body with sport exhaust and PCCB as standard, delivering near-GT3 specification at a lower price. It has appreciated notably as the driver\'s choice within the naturally aspirated 991.1 lineup.',
      'Turbo':        'The 991.1 Turbo introduced rear-axle steering to the 911 alongside a turbocharged 3.8-liter engine producing 520 horsepower in a significantly more refined package than previous Turbos. Strong performance and broad usability have supported firm residuals on the secondary market.',
      'Turbo S':      'The 991.1 Turbo S produced 560 horsepower with standard PCCB, Sport Chrono, and rear-axle steering, establishing a new benchmark for all-weather high-performance driving. Values have held firmly, particularly for low-mileage examples in desirable specifications.',
      'GT3':          'The 991.1 GT3 controversially offered PDK only but compensated with a 475-horsepower 3.8-liter naturally aspirated engine and a best-in-class chassis for its era. It has been recognized as one of the great modern GT3s, with values rising consistently since its launch.',
      'GT3 RS':       'The 991.1 GT3 RS used a 4.0-liter naturally aspirated engine producing 500 horsepower in a wide body with front-lid cooling ducts and among the most comprehensive aerodynamic packages seen on a production 911. It is regarded as one of the purest and most extreme road-legal 911s ever built.',
      'R':            'Produced in only 991 numbered examples, the 911R combined the GT3 RS\'s 500-horsepower 4.0-liter engine with the standard Carrera body and a six-speed manual gearbox only, without the GT3\'s fixed wing. It has become one of the most sought-after modern Porsches, consistently exceeding its MSRP by a significant margin at auction.',
      'Carrera 4': 'The 991.1 Carrera 4 paired the 350-horsepower naturally aspirated 3.4-liter engine with all-wheel drive in the wide body, on the 911\'s longest wheelbase to that point. As one of the last naturally aspirated Carreras, it has drawn renewed interest from buyers avoiding turbocharged cars.',
      'Carrera 4S':'The 991.1 Carrera 4S combined the 400-horsepower naturally aspirated 3.8-liter engine with all-wheel drive, PASM, and the wide body. Manual-gearbox cars are increasingly prized as the final naturally aspirated all-wheel-drive Carrera S.',
      'Targa':     'The 991 Targa restored the classic wide roll hoop for the first time since the 993, adding a fully automatic folding fabric roof above it. Offered only with all-wheel drive, it is the most visually distinctive 991 body style and has a strong following among air-cooled enthusiasts.',
    },
    '991.2': {
      'Carrera':     'The 991.2 Carrera introduced a twin-turbocharged 3.0-liter flat-six producing 370 horsepower, replacing the naturally aspirated engine and fundamentally changing the character of the base 911 Carrera. Manual examples have developed a following among buyers who appreciate the turbocharged 991.2 on its own terms.',
      'Carrera S':    'The 991.2 Carrera S used a 420-horsepower version of the turbocharged 3.0-liter engine with Sport Exhaust standard and PASM adaptive suspension, refining the turbocharged Carrera formula significantly. It represents the most well-rounded everyday 991.2 configuration and holds up strongly on the secondary market.',
      'Carrera T':    'The 991.2 Carrera T stripped the turbocharged Carrera to its essence with a manual gearbox, mechanical LSD, deleted rear-axle steering, and simplified interior at a competitive price. It has become one of the most popular 991.2 configurations on the used market for its clarity of purpose.',
      'Carrera GTS':  'Fitted with a 450-horsepower turbocharged engine in the Carrera 4S wide body with standard rear-axle steering and sport exhaust, the 991.2 GTS represents the peak of the Carrera range before the GT cars. It commands a firm premium and is widely considered the most complete everyday 991.2.',
      'Turbo':        'The 991.2 Turbo produced 540 horsepower from its twin-turbocharged 3.8-liter engine with rear-axle steering and aerodynamic revisions over the 991.1, in a PDK-only grand tourer. It offers exceptional performance with strong residual values on the secondary market.',
      'Turbo S':      'The 991.2 Turbo S pushed to 580 horsepower with standard PCCB, Sport Chrono, and rear-axle steering in the most capable everyday 991 short of the GT cars. Values have remained strong, particularly for well-specified low-mileage examples.',
      'GT3':          'The 991.2 GT3 restored the manual gearbox option alongside the PDK, produced 500 horsepower from a 4.0-liter naturally aspirated engine, and offered a Touring variant that deleted the fixed wing. The Touring has become particularly sought after and commands additional premiums at auction.',
      'GT3 RS':       'The 991.2 GT3 RS used a 520-horsepower 4.0-liter engine in a wide body with active aerodynamics and a Weissach Package option alongside extensive carbon fiber and magnesium construction. Values have risen firmly as the last naturally aspirated wide-body GT3 RS before the 992 redesign.',
      'GT2 RS':       'The 991.2 GT2 RS produced 700 horsepower from a turbocharged 3.8-liter engine to become the most powerful road-going Porsche ever built, with a Weissach Package saving a further 30 kilograms. Among the 1,000 examples produced, well-specified cars have already traded significantly above original MSRP.',
      'Speedster':    'The 991.2 Speedster was produced in only 1,948 numbered examples for 2019 as a celebration of 70 years of Porsche, using the GT3\'s naturally aspirated 4.0-liter engine in a hand-built open body with a six-speed manual only. Values consistently exceed its approximately $280,000 MSRP, establishing it as one of the most desirable modern 911s.',
      'Carrera 4': 'The 991.2 Carrera 4 adopted the twin-turbocharged 3.0-liter flat-six producing 370 horsepower, replacing natural aspiration across the Carrera range. It is a usable modern 911 that trades at a discount to the naturally aspirated 991.1 among collectors.',
      'Carrera 4S':'The 991.2 Carrera 4S used the 420-horsepower turbocharged 3.0-liter engine with all-wheel drive, PASM, and the wide body. Manual examples are uncommon and carry a premium, as most buyers specified PDK.',
      'Targa':     'The 991.2 Targa continued the hoop-and-folding-roof design with the turbocharged flat-six, offered as the Targa 4, 4S, and the limited Targa 4 GTS. Values track close to equivalent cabriolets, with the GTS the most sought-after of the three.',
    },
    '992.1': {
      'Carrera':      'The 992.1 Carrera launched with a revised 3.0-liter twin-turbocharged engine producing 379 horsepower, a new 8-speed PDK, and the widened body shell standardized across the entire Carrera range for the first time. It represents the entry point to the 992 generation and the most widely available 992 on the used market.',
      'Carrera S':    'The 992.1 Carrera S used a 443-horsepower version of the turbocharged 3.0-liter engine with PASM, larger brakes, and standard Sport Exhaust as a meaningful step over the base Carrera. It is considered the most practical all-around choice in the 992.1 Carrera range.',
      'Carrera T':    'The 992.1 Carrera T offered the manual gearbox, mechanical rear differential, deleted rear seat, and lightweight specification of a focused driver\'s Carrera at a competitive price relative to the S. It has earned a loyal following as the most analog driver-focused specification in the 992.1 Carrera lineup.',
      'Carrera GTS':  'Powered by a 473-horsepower version of the turbocharged 3.0-liter engine with standard rear-axle steering, sport exhaust, and PASM Sport in the widened body, the 992.1 GTS is widely considered the performance sweet spot of the 992.1 Carrera range. Demand has been consistently strong, and values reflect the model\'s broad appeal.',
      'Turbo':        'The 992.1 Turbo used a 572-horsepower twin-turbocharged 3.8-liter engine with rear-axle steering, PDCC, and active aerodynamics as standard, comprehensively outperforming the outgoing 991.2 Turbo. Strong residuals and broad capability make it one of the most competitive all-around turbocharged grand tourers available.',
      'Turbo S':      'The 992.1 Turbo S produced 640 horsepower with standard PCCB, rear-axle steering, and an extensive active aerodynamics package in the most powerful turbocharged 992 Carrera. Values have held strongly, particularly for low-mileage desirably specified examples.',
      'GT3':          'The 992.1 GT3 introduced an all-new double-wishbone front suspension alongside a 510-horsepower naturally aspirated 4.0-liter engine with an available six-speed manual gearbox, drawing immediate critical acclaim. It is now considered one of the finest GT3s ever built, with values already reflecting its future classic status.',
      'GT3 RS':       'The 992.1 GT3 RS introduced an active aerodynamics system generating over 860 pounds of downforce and a 525-horsepower naturally aspirated 4.0-liter engine in the most extreme road-legal 911 ever produced. Weissach Package examples are particularly sought after.',
      'S/T':          'Produced in only 1,963 numbered examples to celebrate 60 years of the 911, the S/T combined the GT3\'s 510-horsepower naturally aspirated 4.0-liter engine with the wide GT3 RS body and a six-speed manual in the lightest road-going 992. Values have already exceeded original retail pricing at auction.',
      'Sport Classic': 'Reviving the spirit of the 997.2 Sport Classic, the 992 Sport Classic used a 394-horsepower GTS engine with a seven-speed manual gearbox, ducktail spoiler, double-bubble roof, and Fuchs-inspired wheels in approximately 1,250 examples. It has appreciated quickly as one of the most collectible and visually distinctive 992.1 variants.',
      'Dakar':        'Built in 2,500 examples, the 992 Dakar used a 480-horsepower GTS engine in an all-terrain-capable variant with raised ride height, drawing inspiration from Porsche\'s 1984 Paris-Dakar victory. Its radical departure from tradition and genuine off-road capability created a new collector category, with values holding at and above original retail.',
      'Carrera 4': 'Every 992 shares a single wide body, so the Carrera 4 is distinguished by its all-wheel-drive hardware rather than its stance, using the 379-horsepower turbocharged 3.0-liter engine with PDK. Cars are recent enough that most auction results sit near original transaction prices.',
      'Carrera 4S':'The 992.1 Carrera 4S used the 443-horsepower turbocharged 3.0-liter engine with all-wheel drive, PASM, and standard PDK, with a manual offered later in the run. Low-mileage manual examples are the ones that stand out in an otherwise flat early market.',
      'Targa':     'The 992 Targa continued the hoop with an automatic folding fabric roof, offered as the Targa 4 and Targa 4S plus the limited Heritage Design Edition. The Heritage cars sell well above standard Targas and were among the first 992s to appreciate past list.',
    },
    '992.2': {
      'Carrera':     'The 992.2 Carrera arrives for the 2025 model year with revised front and rear styling, updated infotainment, and refined powertrain calibration as the latest evolution of the water-cooled 911. As a current-production model, secondary market values track closely to MSRP.',
      'Carrera S':    'The 992.2 Carrera S continues with a higher-output turbocharged specification and updated chassis tuning as part of the mid-cycle 992 refresh. It remains the most versatile and broadly specified variant in the 992.2 Carrera range.',
      'Carrera T':    'The 992.2 Carrera T continues the driver-focused lightweight Carrera formula from the 992.1 with the manual gearbox and simplified specification updated for the refreshed generation. As a current model, values have not yet diverged from new pricing.',
      'Carrera GTS':  'The 992.2 GTS brings the high-output turbocharged Carrera to the refreshed generation with active chassis systems and the widened body as standard. It is expected to maintain the strong demand established by the 992.1 GTS as the enthusiast\'s choice in the Carrera range.',
      'Turbo':        'The 992.2 Turbo carries the 572-horsepower all-wheel-drive formula of its predecessor with cosmetic and technical updates consistent with the broader 992.2 refresh. As a current-production model, long-term collector values are still being established.',
      'Turbo S':      'The 992.2 Turbo S continues as the flagship turbocharged 911 Carrera with 640 horsepower and updated specification for the revised generation. Current-production status means secondary market pricing reflects near-MSRP values.',
      'GT3':          'The 992.2 GT3 arrives with aerodynamic and chassis calibration refinements to the acclaimed 992.1 platform, maintaining the naturally aspirated 4.0-liter engine and available six-speed manual gearbox. Early examples have attracted strong demand at near-MSRP pricing on the secondary market.',
      'GT3 RS':       'The 992.2 GT3 RS continues the active aerodynamics platform of its predecessor with updates consistent with the broader 992 facelift in the most extreme road-legal 992. Early secondary market examples are expected to follow the strong trajectory set by the 992.1 RS.',
      'Carrera 4': 'The facelifted 992.2 continues the all-wheel-drive Carrera with the turbocharged 3.0-liter flat-six, PDK, and the generation\'s revised lighting and digital interior. The cars are new enough that auction appearances remain uncommon and results closely track list pricing.',
      'Carrera 4S':'The 992.2 Carrera 4S carries the higher-output turbocharged 3.0-liter engine into the facelift with all-wheel drive, PASM, and updated electronics. Few have reached the secondary market, so results so far reflect dealer and list-adjacent pricing rather than an established collector value.',
      'Targa':     'The 992.2 Targa continues the roll hoop and automatic folding roof, offered in all-wheel-drive form alongside the Targa 4 GTS. As a current model it appears at auction only occasionally, typically at or near original retail.',
    },
  },
  '356': {
    'Pre-A': {
      'Coupe':    'The earliest 356 coupes were hand-built in Gmünd, Austria with aluminum bodywork before production moved to Stuttgart in 1950 and switched to steel bodies by Reutter. Split-window and bent-window cars are the most historically significant road cars Porsche produced, and the aluminum Gmünd coupes are among the most valuable 356s of all.',
      'Cabriolet':'The Pre-A Cabriolet was bodied principally by Reutter in Stuttgart with a lined folding roof and full weather equipment, sharing its running gear with the coupe. Split- and bent-window examples are genuinely rare, and values have climbed steadily as collectors pursue the earliest Porsches.',
      'Speedster':'Introduced for 1954 at the urging of US importer Max Hoffman, the Speedster used a low-cut windscreen, lightweight bucket seats, removable side curtains, and a minimal top to hit a lower price with a sportier specification. Pre-A Speedsters are the most sought-after body style of the era and lead the Pre-A market.',
      'Roadster': 'Roadster-bodied Pre-A cars are headed by the 1952-1953 America Roadster, a lightweight aluminum-bodied car built by Gläser for US competition use in roughly 16 examples. Survivors are exceptionally rare and appear at auction only through major collection sales.',
    },
    '356 A': {
      'Coupe':    'The 356 A arrived in 1955 with a curved one-piece windscreen and the new 1600 engine range, and it is the generation in which the 356 matured into a fully developed production car. Coupes are the most numerous body style and the most accessible entry into 356 ownership, with four-cam Carrera examples a tier apart.',
      'Cabriolet':'The 356 A Cabriolet paired the curved-windscreen body with a padded, lined folding top and full weather protection, bodied mainly by Reutter. It offers open 356 motoring with far more usability than a Speedster, and values have followed the Speedster market upward.',
      'Speedster':'The 356 A years were the definitive Speedster era, with the raked low windscreen and stripped specification carried over to the new body until the Convertible D replaced it in 1958. Speedster production totaled roughly 4,800 cars across all years, and they are the most recognizable and most strongly valued 356 variant.',
    },
    '356 B': {
      'Coupe':    'The 356 B brought raised headlights, higher bumpers, and the T5 and later T6 body revisions from 1959, with the 90-horsepower Super 90 joining the engine range. B coupes are plentiful and mechanically well supported, making them one of the better values in classic Porsche ownership.',
      'Roadster': 'The Roadster succeeded the Convertible D as the entry-level open 356, bodied by Drauz and later D\'Ieteren with a low windscreen and simplified trim. Production ended in 1962, leaving the Roadster considerably rarer than the Cabriolet and increasingly collected as a Speedster alternative.',
      'Cabriolet':'The 356 B Cabriolet continued the fully weatherproof open car with a lined folding top, available through the T5 and T6 body series with engines up to the Super 90. It is the most usable open 356 of the generation and trades well below Speedster and Roadster money.',
      'Notchback':'The Karmann Hardtop, universally known as the Notchback, used a cabriolet body with a permanently welded steel roof, built for 1961 and 1962 only. Its short production run and unusual silhouette make it the rarest regular-production 356 B body style.',
    },
    '356 C': {
      'Coupe':    'The 356 C arrived for 1964 as the final and most developed 356, with four-wheel disc brakes and the 75-horsepower C and 95-horsepower SC engines. As the best-braked and most refined of the line, C coupes are widely considered the best all-round driver\'s choice among 356s.',
      'Cabriolet':'The 356 C Cabriolet was the last open 356, combining disc brakes and the C or SC engine with the fully weatherproof Reutter body. Last-of-the-line status and relatively low production have made it one of the strongest-performing 356 Cabriolets on the market.',
    },
  },
  'cayman': {
    '987.1': {
      'base': 'The original 987.1 Cayman introduced a purpose-built fixed-roof mid-engined platform in 2005, using a 2.7-liter flat-six producing 245 horsepower in a body many considered more dynamically capable than the concurrent Boxster. Clean manual examples have become increasingly popular as modern classics valued for their taut mid-engined character.',
      'S':    'The 987.1 Cayman S used a 3.4-liter flat-six producing 295 horsepower, offering chassis dynamics that many drivers considered superior to the contemporary 911 Carrera. It is widely recognized as one of the finest driver\'s cars of its era and represents exceptional value for its performance credentials.',
    },
    '987.2': {
      'base': 'The 987.2 Cayman updated the original platform with a revised 2.9-liter DFI engine producing 265 horsepower and improved interior quality. It remains among the most accessible Porsche mid-engined sports cars with strong driving credentials.',
      'S':    'The 987.2 Cayman S upgraded to a 3.4-liter DFI engine producing 320 horsepower alongside interior improvements, maintaining its reputation as one of the finest everyday sports cars available. Comparative affordability and strong performance have sustained consistent demand on the used market.',
      'R':    'The 987.2 Cayman R shed 55 kilograms through deleted carpets, air conditioning, and audio while adding a higher-output engine and adjustable suspension. Approximately 2,000 were produced globally, making it the most collectible variant of the 987.2 generation.',
    },
    '981': {
      'base': 'The 981 Cayman introduced a longer wheelbase, wider track, and a 275-horsepower 2.7-liter flat-six in a significantly more capable chassis than its predecessor. It substantially raised the dynamic standard of the mid-engined Porsche and remains highly regarded for everyday sports car use.',
      'S':    'The 981 Cayman S used a 3.4-liter flat-six producing 325 horsepower with PASM and revised aerodynamics, offering genuine performance competitive with the contemporary 911 Carrera on a circuit. It is consistently regarded as one of the best-handling production cars of its era.',
      'GTS':  'The 981 Cayman GTS offered a 340-horsepower uprated engine with sport exhaust, the wider Boxster body, and Sport Design visuals at a competitive premium over the S. It has become the most sought-after naturally aspirated 981 Cayman for its comprehensive specification.',
      'GT4':  'The 981 Cayman GT4 used the 991 Carrera S\'s 3.8-liter engine producing 385 horsepower in a fully track-focused car with adjustable suspension, a fixed rear wing, and an exclusive six-speed manual gearbox. Immediately oversubscribed at launch and produced in limited numbers, it has become one of the most valuable mid-engined Porsches in the modern era.',
    },
    '718': {
      'base':   'The 718 Cayman replaced the naturally aspirated flat-six with a turbocharged 2.0-liter flat-four producing 300 horsepower, improving performance while generating controversy over the change in engine character. Buyer preference has shifted strongly toward the naturally aspirated GTS 4.0 and GT4 variants on the used market.',
      'S':      'The 718 Cayman S used a turbocharged 2.5-liter flat-four producing 350 horsepower with enhanced chassis tuning over the base car, offering strong straight-line performance despite the change in engine type. Values have been steady, though buyer demand continues to favor the naturally aspirated variants.',
      'GTS':    'The 718 Cayman GTS transitioned from the turbocharged four-cylinder to the naturally aspirated 4.0-liter flat-six producing 394 horsepower from the 2020 model year, transforming its desirability. GTS 4.0 examples have appreciated sharply and represent the driver\'s pick in the non-GT 718 Cayman range.',
      'GT4':    'The 718 Cayman GT4 restored the naturally aspirated flat-six to the performance Cayman, using a 4.0-liter engine producing 414 horsepower with a six-speed manual gearbox and a full aerodynamic package. It is considered one of the finest driver\'s cars in current production, with values strengthening consistently since launch.',
      'GT4 RS': 'The 718 Cayman GT4 RS used the motorsport-derived 4.0-liter flat-six from the 911 GT3 producing 493 horsepower, connected exclusively to a PDK transmission in the most powerful and track-capable production Cayman ever built. Produced in limited numbers, it commands a significant premium over MSRP on the secondary market.',
    },
  },
  'boxster': {
    '986': {
      'base': 'The 986 Boxster launched Porsche\'s modern mid-engined roadster era in 1996 with a 2.5-liter flat-six producing 201 horsepower in an open-air package sharing components with the 996. Clean examples represent outstanding value as accessible entry points to Porsche ownership with genuine mid-engined sports car dynamics.',
      'S':    'The 986 Boxster S added a 3.2-liter engine producing 250 horsepower, narrowing the performance gap with the 911 in a way that surprised many buyers at the time. It has emerged as the preferred 986 specification among enthusiasts, with values strengthening for documented manual examples.',
    },
    '987.1': {
      'base': 'The 987.1 Boxster refreshed the platform with a 2.7-liter engine producing 240 horsepower and revised styling that gave the car a more distinct visual identity. It remains an engaging and accessible entry-level Porsche with a strong enthusiast following and broad mechanical support.',
      'S':    'The 987.1 Boxster S used a 3.2-liter engine producing 280 horsepower with PASM available, offering near-Cayman S performance in an open-top roadster. It is the most desirable 987.1 Boxster specification and holds up well in both use and value.',
    },
    '987.2': {
      'base':   'The 987.2 Boxster updated the formula with a new 2.9-liter DFI engine producing 255 horsepower and improved interior quality in a refinement of the well-regarded 987.1. It is a capable and well-sorted open-air sports car that represents strong value in the used Porsche market.',
      'S':      'The 987.2 Boxster S used a 3.4-liter DFI engine producing 310 horsepower with revised suspension and styling updates. It is the most popular 987.2 Boxster configuration and consistently holds its value on the secondary market.',
      'Spyder': 'The 987.2 Boxster Spyder stripped the roadster to minimum weight by removing sound deadening, the power soft top, and most luxury features while fitting a manual-only transmission in a car weighing just 1,275 kilograms. Approximately 2,000 were produced for the 2011 model year, making it the most collectible 987.2 Boxster variant.',
      'GTS':    'The 987.2 Boxster GTS offered a 330-horsepower engine with sport exhaust, PASM, and visual upgrades in a high-specification version of the outgoing 987.2 platform. Produced in limited numbers at the end of the 987 generation, it is the most desirable naturally aspirated standard variant.',
    },
    '981': {
      'base':   'The 981 Boxster brought a longer wheelbase, wider track, and a 265-horsepower 2.7-liter flat-six to the roadster format, substantially improving dynamics and rigidity over the outgoing 987.2. It is widely regarded as the best-balanced entry-level Boxster to date.',
      'S':      'The 981 Boxster S used a 3.4-liter flat-six producing 315 horsepower with PASM and revised aerodynamics in an open-top package sharing the structural benefits of the 981 platform. Values have been consistent, supported by the model\'s reputation for strong all-around performance.',
      'GTS':    'The 981 Boxster GTS offered a 330-horsepower engine, standard sport exhaust, and the wider Spyder body in a high-specification roadster positioned just below the Spyder in price. It has become the most desirable naturally aspirated 981 Boxster, with values tracking the strong trajectory of the 981 Cayman GTS.',
      'Spyder': 'The 981 Spyder used the 3.8-liter engine from the Cayman GTS producing 375 horsepower in a focused open-top car with a manually operated fabric top. Its unique styling, strongest available engine, and open-air simplicity make it the most collectible 981 Boxster.',
    },
    '718': {
      'base':      'The 718 Boxster replaced the naturally aspirated flat-six with a turbocharged 2.0-liter flat-four producing 300 horsepower, improving straight-line performance at the cost of the engine\'s aural character. Buyer preference has shifted toward the naturally aspirated GTS 4.0 and Spyder among enthusiasts on the secondary market.',
      'S':         'The 718 Boxster S used a turbocharged 2.5-liter flat-four producing 350 horsepower in the mid-engined roadster platform, offering improved performance over the 981 S despite the change in engine type. Values have been steady, with demand oriented toward the naturally aspirated Spyder and GTS 4.0.',
      'GTS':       'The 718 Boxster GTS transitioned from the turbocharged four-cylinder to the naturally aspirated 4.0-liter flat-six producing 394 horsepower from the 2020 model year, dramatically improving its appeal. GTS 4.0 examples have appreciated sharply and represent the pick of the non-GT 718 Boxster range.',
      'Spyder':    'The 718 Spyder uses the same naturally aspirated 4.0-liter flat-six as the GT4 producing 414 horsepower in a lightweight roadster body with a simple manual fabric top. It has become one of the most desirable modern Porsches on the secondary market, with values well above original pricing for early examples.',
      'Spyder RS': 'The 718 Spyder RS combined the GT4 RS\'s 493-horsepower motorsport flat-six from the 911 GT3 with the open Spyder body in a PDK-only package, creating the most extreme and powerful Boxster ever built. Produced in very limited numbers, it commands a substantial premium at auction.',
    },
  },
  '911-race': {
    'F-Body': {
      'RSR':'The 1973 Carrera RSR was the works competition version of the Carrera RS, with a 2.8-liter and later 3.0-liter engine, riveted-on arches, plexiglass, and full race preparation. Period-campaigned cars with documented results at Daytona, Le Mans, or the Targa Florio are among the most valuable 911s of any kind.',
    },
    'G-Body': {
      'RSR':      'The 3.0 RSR carried the RSR lineage into the impact-bumper era from 1974, with a roughly 330-horsepower naturally aspirated flat-six, wide IROC-style bodywork, and 917-derived brakes. Built in small numbers for customer teams, it dominated GT racing worldwide in period and anchors serious 911 competition collections.',
      'RSR Turbo':'The 2.1-liter Carrera RSR Turbo of 1974 was Porsche\'s turbocharged prototype that finished second overall at Le Mans and directly previewed both the 930 Turbo and the 935. Only four were built, and they surface through factory and museum collections rather than open sale.',
    },
    '964': {
      'RSR 3.8':     'Built by Porsche Motorsport at Weissach around a 300-plus-horsepower 3.8-liter flat-six, the Carrera RSR 3.8 was the customer racing flagship of the 964 line, winning its class at Le Mans and taking overall victory at Spa and Suzuka in 1993. Approximately 51 were built, including a handful of road-registerable Strassenversion examples that rank among the most valuable 964s ever sold.',
      'Carrera Cup': 'The Carrera Cup 964s were lightweight one-make racers built for Porsche\'s Carrera Cup championships, including the short-lived Carrera Cup USA program whose cars were sold off with delivery mileage when the series folded. Low-mileage USA examples are prized as time-capsule factory race cars.',
    },
    '993': {
      'GT2 R':       'The GT2 R was the pure competition version of the 993 GT2, stripped for GT racing with increased boost and a full cage. It contested international GT championships in the mid-1990s and appears at auction far less often than the road-going GT2.',
      'Cup 3.8 RSR': 'The 993 Cup 3.8 RSR evolved the one-make Cup car into full RSR specification for customer GT racing, with a 3.8-liter engine and wider bodywork. It bridged the gap between the Carrera Cup and the factory GT2 program.',
      'Carrera Cup': 'The 993 Carrera Cup cars continued Porsche\'s one-make racing formula with the last air-cooled 911, using a 3.8-liter naturally aspirated flat-six and lightweight body.',
    },
    '996': {
      'GT3 Cup':     'The 996 GT3 Cup launched the modern era of Porsche one-make racing, powered by the Mezger GT3 engine. Hundreds raced worldwide in Supercup and national Carrera Cup series, making it the most accessible entry into factory-built Porsche race cars.',
      'GT3 RSR':     'The 996 GT3 RSR was the factory customer GT car for endurance racing, winning its class at Le Mans, Sebring, and Daytona. It combined the Mezger engine with wide RSR bodywork and sequential gearbox.',
      'Carrera Cup': 'Early 996-generation one-make Cup cars, campaigned in national Carrera Cup championships before the GT3 Cup naming took hold.',
    },
    '997': {
      'GT3 RSR':     'The 997 GT3 RSR was Porsche\'s customer GT racing weapon of the ALMS and Le Mans era, with a 4.0-liter Mezger engine and dramatic wide-body aero. Ex-works and podium-finishing chassis carry significant provenance premiums.',
      'GT3 Cup':     'The 997 GT3 Cup was built in greater numbers than any previous Porsche race car, powering Supercup and Carrera Cup grids worldwide. Well-documented, low-hour examples remain the standard track-day and club racing choice.',
    },
    '991': {
      'RSR':         'The 991 RSR was a mid-engined revolution in the 911\'s racing lineage, developed by the factory for the FIA WEC and IMSA. Genuine examples are rarely offered publicly and represent the pinnacle of modern 911 GT racing.',
      'GT2 RS Clubsport': 'The GT2 RS Clubsport is a track-only customer racing version of the 991 GT2 RS, with 700 horsepower, a welded-in cage, and no road registration. Two hundred were built, plus thirty Manthey-developed Clubsport 25 examples, and low-hour cars trade near their original list price.',
      'GT3 Cup':     'The 991 GT3 Cup continued the one-make formula with a 4.0-liter flat-six and factory-sealed drivetrain, racing in Supercup and Carrera Cup series worldwide.',
    },
    '992': {
      'GT3 Cup':     'The 992 GT3 Cup is the current generation of Porsche\'s one-make racer, the first Cup car with the 992\'s wider body and a 510-horsepower 4.0-liter flat-six.',
    },
  },
  // Variant-models (924/944/968/928/914) have no generation level, so these
  // are keyed [modelSlug][variant] directly.
  '914': {
    '914/6':'The 914/6 used the 110-horsepower 2.0-liter flat-six from the 911T in the mid-engined 914 chassis, assembled by Porsche rather than Karmann and fitted with five-lug wheels and 911 brakes. Approximately 3,300 were built across 1970 and 1971, and they are the most collectible 914s by a wide margin.',
    'base': 'The four-cylinder 914, sold with 1.7-, 1.8-, and 2.0-liter Volkswagen-sourced engines, was Porsche\'s mid-engined entry model and the best-selling car in the company\'s range at the time, with well over 100,000 built. Long overlooked, clean 2.0-liter examples have appreciated as the mid-engined handling and period design find a new audience.',
  },
  '924': {
    'Carrera GTS':'A 1981 evolution of the Carrera GT built to extend the 924\'s Group 4 homologation, the GTS produced 245 horsepower with a lightweight body, no power assistance, and a single-plate clutch. Fifty-nine were built, fifteen of them in Clubsport specification, making it one of the rarest road-legal Porsches of the era.',
    'Carrera GT': 'Built in 1981 to homologate the 924 for Group 4, the Carrera GT paired a 210-horsepower intercooled turbocharged engine with riveted-on flared arches and a raised scoop in the hood. Approximately 400 were produced, and they have appreciated sharply as the most attainable of the 924 homologation specials.',
    'Turbo':      'The 924 Turbo answered criticism of the base car\'s Audi-sourced engine with a Porsche-developed turbocharged unit producing 170 and later 177 horsepower, identified by its NACA-ducted hood and four-bolt wheels. Survivors are scarce next to the base car, and the Turbo is now the entry point into the collectible 924s.',
    'base':       'The 924 was Porsche\'s first front-engined, water-cooled production car and the model that carried the company through the late 1970s, using a 2.0-liter Audi-derived engine with a rear transaxle for near-equal weight distribution. The later 924S, which took the 944\'s 2.5-liter engine, is the most desirable of the naturally aspirated cars and is grouped here.',
  },
  '944': {
    'Turbo S':'The 1988 Turbo S raised boost to 250 horsepower with a larger turbocharger, uprated suspension, a limited-slip differential, and the brakes from the 928 S4. It is the most capable and most collectible 944, and documented Silver Rose examples command the strongest prices in the model line.',
    'Turbo':  'The 944 Turbo used a 220-horsepower turbocharged 2.5-liter four behind a flush-nose front end with uprated running gear, and was quick enough in period to run with contemporary 911s. Values have climbed steadily as the 944 Turbo is recognized as one of the best-handling Porsches of the 1980s.',
    'S2':     'The S2 enlarged the 16-valve four to 3.0 liters and 208 horsepower, the largest four-cylinder in production at the time, and adopted the Turbo\'s flush nose and brakes. It delivers much of the Turbo\'s pace without boost complexity and has become a steadily appreciating enthusiast choice.',
    'base':   'The 944 replaced the 924 with Porsche\'s own 2.5-liter four, wider bodywork, and the transaxle layout, becoming the company\'s volume model through the 1980s. The 16-valve 944S sits above the base car and is grouped here; well-kept examples of either remain among the most affordable routes into Porsche ownership.',
  },
  '968': {
    'Turbo S':   'The 968 Turbo S used an eight-valve 3.0-liter turbocharged engine producing 305 horsepower in a Club Sport-based lightweight body, built as the road counterpart to the Turbo RS race program. Only fourteen were produced, making it the rarest transaxle Porsche and a seven-figure car on the rare occasion one surfaces.',
    'Club Sport':'The Club Sport deleted the rear seats, electric adjustment, and much of the sound deadening while adding firmer suspension and Recaro buckets, cutting around 100 kilograms from the standard car. It is the enthusiast\'s choice of the late transaxle era and the most sought-after 968 that can realistically be bought.',
    'base':      'The 968 was the final transaxle Porsche, taking the 944\'s chassis with new 928-influenced bodywork and a 236-horsepower 3.0-liter VarioCam four that remains one of the most powerful naturally aspirated production four-cylinders ever built. Produced only from 1992 to 1995 in modest numbers, it is rarer than the 944 and increasingly collected as the line\'s last word.',
  },
  '928': {
    'GTS':       'The final 928, built from 1992, used a 5.4-liter V8 producing 345 horsepower with widened rear bodywork, the big-brake specification, and a revised interior. Produced in small numbers and rarer still with the manual gearbox, the GTS is comfortably the most valuable 928 and the one that has appreciated most.',
    'GT':        'The 928 GT combined the 5.0-liter V8 in a 326-horsepower state of tune with a manual gearbox, limited-slip differential, and firmer suspension as the driver-focused model of the late run. Manual-only production in limited numbers has made it the enthusiast\'s pick between the S4 and the GTS.',
    'S4':        'The S4 brought the definitive 5.0-liter 32-valve V8 producing 316 horsepower along with revised nose and tail aerodynamics, and it defined the 928 through the late 1980s. It is the most numerous of the desirable late cars and the most accessible route to the full 928 experience.',
    'Club Sport':'An ultra-rare lightweight built mainly for 1988, the 928 Club Sport stripped sound deadening, rear seats, and electrical equipment from the S4 and added a higher-revving engine with revised gearing. Only a handful were built, and the model almost never reaches public auction.',
    'base':      'The original 928 and 928 S introduced Porsche\'s front-engined V8 grand tourer, winning European Car of the Year in 1978 as a car intended to eventually replace the 911. Early cars are the most affordable 928s, offering the distinctive shark bodywork and a V8 that rewards careful, documented maintenance.',
  },
}

export default VARIANT_DESCRIPTIONS

// Keyed [generation][variant], or [modelSlug][variant] for the variant-models
// at the end — only variants with confirmed limited production numbers
export const PRODUCTION_NUMBERS = {
  'F-Body': {
    'Carrera RS 2.7': 1583,
  },
  'G-Body': {
    'Speedster':  2104,
    'RSR Turbo':  4,
  },
  '964': {
    'Carrera RS': 2282,
    'RS 3.8':     55,
    'RSR 3.8':    51,
    'RS America': 701,
    'Turbo S':    81,
    'Speedster':  936,
  },
  '993': {
    'Carrera RS': 1104,
    'Turbo S':    345,
    'GT2':        194,
  },
  '996.1': {
    'GT3': 1868,
  },
  '996.2': {
    'GT3':    2313,
    'GT3 RS': 682,
    'GT2':    1287,
  },
  '997.1': {
    'GT3':    3329,
    'GT3 RS': 1909,
    'GT2':    1242,
  },
  '997.2': {
    'GT3':          2256,
    'GT3 RS':       1619,
    'GT3 RS 4.0':   600,
    'GT2 RS':       500,
    'Sport Classic': 256,
    'Speedster':    356,
  },
  '991.1': {
    'R': 991,
  },
  '991.2': {
    'GT2 RS':   3751,
    'Speedster': 1948,
  },
  '992.1': {
    'S/T':          1963,
    'Sport Classic': 1250,
    'Dakar':        2500,
  },
  // 924 — keyed by model slug: variant-models have no generation level.
  '924': {
    'Carrera GTS':59,
    'Carrera GT': 406,
  },
  // 968 — keyed by model slug: variant-models have no generation level.
  '968': {
    'Turbo S':14,
  },
  // 914 — keyed by model slug: variant-models have no generation level.
  '914': {
    '914/6': 3338,
  },
}

// Keyed [modelSlug] — standalone models (specialty, restomod, race) have no
// generation or variant level, so their hero copy lives here.
export const MODEL_DESCRIPTIONS = {
  '959':          'Developed from Porsche\'s Group B rally program, the 959 introduced twin sequential turbocharging, computer-controlled all-wheel drive, and adjustable ride height in a 444-horsepower road car that was the fastest production car in the world at launch. Two hundred ninety-two customer cars were built between 1986 and 1988, and values have climbed well past seven figures as the 959\'s technical significance has been recognized.',
  'carrera-gt':   'The Carrera GT used a 5.7-liter V10 derived from an abandoned Le Mans prototype program, producing 603 horsepower through a six-speed manual gearbox behind a carbon-fiber monocoque. Approximately 1,270 were built between 2004 and 2006, and it is widely regarded as the last of the analog supercars, with values rising sharply over the past decade.',
  '918-spyder':   'The 918 Spyder paired a 4.6-liter V8 with two electric motors for 887 combined horsepower and all-wheel drive, resetting expectations for what a hybrid performance car could do. Exactly 918 were built for 2014 and 2015, and Weissach Package cars command a consistent premium whenever they reach auction.',
  'singer':       'Singer Vehicle Design reimagines 964-generation 911s to commission, with hand-formed carbon bodywork, air-cooled engines developed with Ed Pink and Williams, and interiors trimmed entirely to the client\'s specification. Cars are built in small numbers at prices well into seven figures, and the secondary market regularly clears original build cost for the most desirable commissions, led by the Dynamics and Lightweighting Study.',
  'gunther-werks': 'Gunther Werks reimagines the 993-generation 911 with full carbon bodywork and a naturally aspirated 4.0-liter flat-six built by Rothsport producing around 500 horsepower. The 400R coupe was limited to 25 cars with the Speedster Remastered following in a similarly short run, and demand has consistently outstripped the build slots available.',
  'emory':        'Emory Motorsports builds Outlaw 356s and 911-based specials, most distinctively around its own Emory-Rothsport Special flat-four, assembled from 911 flat-six components and fitted to heavily reworked 356 bodies. Each car is a one-off commission, and Emory Outlaws now sell for multiples of standard 356 money, having largely created the modified-Porsche market as it exists today.',
  '911-gt1':      'Built to contest the GT1 class at Le Mans from 1996 to 1998, the 911 GT1 was a mid-engined, twin-turbocharged prototype wearing 911 bodywork, and it won the race outright in 1998. Roughly 20 road-legal Straßenversion cars were built to satisfy homologation, and both those and the surviving race chassis rank among the most valuable modern Porsches.',
  '917':          'The 917 was Porsche\'s assault on outright victory at Le Mans, with a 4.5-liter and later 5.0-liter flat-twelve in a tubular spaceframe weighing little more than 800 kilograms. Porsche famously assembled 25 cars at once in 1969 to satisfy homologation, and the type delivered the company\'s first overall Le Mans wins in 1970 and 1971; chassis with period results are eight-figure cars.',
  '910':          'The 910 of 1966 and 1967 was the works prototype that moved Porsche to 13-inch wheels and a lightweight fiberglass body over a tubular frame, campaigned with both flat-six and flat-eight engines. Twenty-nine were built, and they finished 1-2-3 at the 1967 Nürburgring 1000 Kilometres and won that year\'s Targa Florio.',
  '956':          'The 956 brought an aluminum monocoque and ground-effect aerodynamics to Group C, winning Le Mans four years running from 1982 and setting a Nürburgring lap record that stood for decades. Twenty-eight were built, ten for the works team and the remainder for customers, and documented race-winning chassis trade in the eight figures.',
  '962':          'The 962 evolved the 956 with a longer wheelbase that moved the driver\'s feet behind the front axle for IMSA compliance, winning Le Mans in 1986 and 1987 and dominating IMSA GTP through the decade. Porsche built around 90 chassis, with many more assembled by Kremer, Joest, and other customer teams, making the 962 the most prolific and most campaigned of all Porsche prototypes.',
  '935':          'Developed from the 930 Turbo for Group 5, the 935 reached 845 horsepower in its most extreme factory form and won Le Mans outright in 1979 in the hands of the privateer Kremer K3. Porsche built roughly 35 customer cars alongside the works entries, and period-raced examples — particularly the slant-nose 935/77 and the later evolutions — are among the most valuable 911-derived racing cars.',
  '934':          'The 934 was the Group 4 racing version of the 930 Turbo, retaining the road car\'s steel bodywork and even its electric windows while producing 485 horsepower from a turbocharged 3.0-liter flat-six. Thirty-one were built for 1976, followed by ten uprated 934/5s for American competition, and they remain mainstays of historic GT racing.',
  '908':          'The 908 was Porsche\'s three-liter prototype from 1968 to 1971, built when a new capacity limit finally let the company contest outright victory with an engine of its own design. It won the Targa Florio, the Nürburgring 1000 Kilometres, and the 1970 Sebring 12 Hours, and the open 908/03 Spyders are the most sought-after cars of the family.',
  '907':          'The 907 brought right-hand drive and low-drag long-tail bodywork to Porsche\'s prototype program for 1967 and 1968, powered first by flat-six and then by flat-eight engines. It delivered Porsche\'s first outright Daytona victory with a 1-2-3 finish in 1968, then won that year\'s Sebring 12 Hours and Targa Florio.',
  '906':          'The 906, or Carrera 6, was the first Porsche designed from the outset around a tubular spaceframe and fiberglass bodywork, homologated for Group 4 with a 210-horsepower two-liter flat-six. Sixty-five were built in 1966 and the type won the Targa Florio outright that year, making it one of the most usable and most collectible of the works-derived racers.',
  '904':          'The 904 Carrera GTS was the first Porsche to bond a fiberglass body to a steel box-section chassis, built for Group 3 homologation around the four-cam Carrera engine and widely held to be the most beautiful car the company ever produced. One hundred six were built for 1964, and the 904 won the Targa Florio outright in its debut season.',
  '550':          'The 550 Spyder was Porsche\'s first purpose-built racing car, a lightweight open two-seater powered by the Fuhrmann four-cam flat-four that delivered class wins at Le Mans and in the Carrera Panamericana. Around 90 were built from 1953 to 1956 ahead of 40 spaceframe 550As, and they are among the most valuable and most widely replicated Porsches ever made.',
  'rs60':         'The RS60 was the 1960 evolution of Porsche\'s 718 sports racer, reworked to meet new regulations demanding a taller windscreen and a luggage compartment, and it won both the Targa Florio and the Sebring 12 Hours that season. Works cars were built in very small numbers and are seldom offered, with the Sebring-winning chassis among the most significant Porsches in private hands.',
  '718-rsk':      'The 718 RSK of 1957 to 1959 refined the 550A around a revised spaceframe and the mid-mounted four-cam flat-four, taking class honors at Le Mans and a remarkable third overall in 1958. Built in small numbers for the works team and privateers, the RSK is a cornerstone of Porsche\'s giant-killing reputation in international sports car racing.',
  'rs-spyder':    'The RS Spyder was Porsche\'s LMP2 prototype from 2005 to 2010, powered by a 3.4-liter V8 that regularly beat the larger LMP1 cars outright in the American Le Mans Series. Built in limited numbers for Penske and a handful of customer teams, it is the most modern Porsche prototype available to private collectors and is eligible for a growing set of historic prototype events.',
}

// Keyed [modelSlug] — whole-model production totals for standalone models.
// Only figures that are unambiguous across sources; models whose published
// totals vary (917, 935, 962, 550, 908, 907, 718 RSK, RS60, 911 GT1) and the
// build-to-order coachbuilders are deliberately absent rather than guessed.
export const MODEL_PRODUCTION = {
  '959':        292,
  'carrera-gt': 1270,
  '918-spyder': 918,
  '956':        28,
  '934':        31,
  '910':        29,
  '906':        65,
  '904':        106,
}
