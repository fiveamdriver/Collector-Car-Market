"""
Facelift boundaries that do not fall in the same model year for every 911.

The year ladder in get_911_generation files a car by model year alone, which is
right for the Carrera but wrong for the models that changed over a year early or
late. Each case below was fact-checked on 2026-11-03 (see generations.py).

Run from backend/:  ../venv/bin/python -m unittest tests.test_facelift_boundaries -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.generations import get_911_generation as gen
from app.utils.variants import match_variant


class TestModelSpecificBoundaries(unittest.TestCase):
    CASES = [
        # 997 GT2 was 997.1 only (on sale Nov 2007, MY2008-09).
        (2009, "17k-Mile 2009 Porsche 911 GT2", "997.1"),
        (2009, "2009 Porsche 997 GT2", "997.1"),
        (2008, "2008 Porsche 911 GT2", "997.1"),
        # ...but the GT2 RS is 997.2.
        (2011, "2011 Porsche 911 GT2 RS", "997.2"),
        (2010, "2010 Porsche 911 GT2 RS", "997.2"),
        # 997.2 Turbo arrived for MY2010.
        (2009, "2009 Porsche 911 Turbo Cabriolet", "997.1"),
        (2009, "2009 Porsche 911 Turbo", "997.1"),
        (2010, "2010 Porsche 911 Turbo", "997.2"),
        # 2009 Carrera family is 997.2.
        (2009, "2009 Porsche 911 Carrera S Coupe", "997.2"),
        (2009, "2009 Porsche 911 Targa 4S", "997.2"),
        # 991 Turbo arrived for MY2014; 2013 Turbos are 997.2.
        (2013, "2013 Porsche 911 Turbo S Coupe", "997.2"),
        (2013, "2013 Porsche 911 Turbo S Cabriolet", "997.2"),
        (2014, "2014 Porsche 911 Turbo S", "991.1"),
        (2013, "2013 Porsche 911 Targa 4S", "997.2"),
        (2014, "2014 Porsche 911 Targa 4S", "991.1"),
        (2013, "2013 Porsche 911 Carrera 4S Coupe", "991.1"),
        # "Turbo" that isn't a Turbo doesn't move anything.
        (2009, "2009 Porsche 911 Carrera S Turbo-Look", "997.2"),
        # 964 Speedster was MY1994 only.
        (1990, "1990 Porsche 911 Speedster", "G-Body"),
        (1994, "1994 Porsche 911 Speedster", "964"),
        # 996 GT3 RS exists only as a 996.2.
        (2001, "2001 Porsche 911 GT3 RS", "996.2"),
        (2001, "2001 Porsche 911 GT3", "996.1"),
        # One 996 Turbo card and one 996 GT2 card, both on 996.2.
        (2001, "2001 Porsche 911 Turbo", "996.2"),
        (2000, "2000 Porsche 911 Turbo", "996.2"),
        (2001, "2001 Porsche 911 GT2", "996.2"),
        (2001, "2001 Porsche 911 Carrera", "996.1"),
    ]

    def test_cases(self):
        for year, title, expected in self.CASES:
            with self.subTest(title=title):
                self.assertEqual(gen(year, title), expected)


class TestNamedChassis(unittest.TestCase):
    CASES = [
        (1998, "1998 Porsche 911 Carrera 4 Type 996 Coupé", "996.1"),
        (1994, "1994 Porsche 911 Carrera 2 Type 993 Coupé", "993"),
        (1989, "1989 Porsche 964 Carrera 2 Coupé", "964"),
        (2016, "2016 Porsche 911 Type 991.2 Turbo S Coupé", "991.2"),
        (2009, "2009 Porsche 911 'Type 997.1' Turbo Cabriolet", "997.1"),
        # A code outside its chassis's years is a style, not a chassis.
        (1973, "1973 Porsche 911 993 backdate", "F-Body"),
        (1985, "1985 Porsche 911 Carrera 964-Style", "G-Body"),
        # The ladder already agrees: the code doesn't override .1/.2.
        (2008, "2008 Porsche 997 GT2", "997.1"),
    ]

    def test_cases(self):
        for year, title, expected in self.CASES:
            with self.subTest(title=title):
                self.assertEqual(gen(year, title), expected)


class TestOverlapYears(unittest.TestCase):
    """MY2005 (996/997) and MY2012 (997/991) sold two chassis at once."""
    CASES = [
        (2005, "2005 Porsche 911 Carrera Coupe 6-Speed", None, "997.1"),
        (2005, "2005 Porsche 911 Carrera Cabriolet 6-Speed", None, "997.1"),
        (2005, "2005 Porsche 911 Carrera S", None, "997.1"),
        (2005, "2005 Porsche 911 Carrera 4S Cabriolet", None, "996.2"),
        (2005, "2005 Porsche 911 Turbo S", None, "996.2"),
        (2005, "2005 Porsche 911 GT3", None, "996.2"),
        (2005, "2005 Porsche 911 Targa", None, "996.2"),
        (2012, "2012 Porsche 911 Carrera S Coupe 7-Speed", None, "991.1"),
        (2012, "2012 Porsche 911 Carrera S Coupe", None, "991.1"),
        (2012, "2012 Porsche 911 Carrera Cabriolet", None, "991.1"),
        (2012, "2012 Porsche 911 Carrera S Coupe 6-Speed", None, "997.2"),
        (2012, "2012 Porsche 911 Carrera Coupe Black Edition", None, "997.2"),
        (2012, "2012 Porsche 911 Carrera GTS", None, "997.2"),
        (2012, "2012 Porsche 911 Carrera 4S Coupe", None, "997.2"),
        (2012, "2012 Porsche 911 Turbo S", None, "997.2"),
        # VIN serial outranks the title: 7xxxxx is a 997 even in a 2012 Carrera.
        (2012, "49k-Mile 2012 Porsche 911 Carrera Coupe", "WP0AA2A96CS706070", "997.2"),
        (2012, "2012 Porsche 911 Carrera S", "WP0AB2A91CS120001", "991.1"),
        (2005, "2005 Porsche 911 Carrera", "WP0AA29945S620001", "996.2"),
        # ...including a VIN written in the title (Bonhams style, letter O).
        (2005, "2005 Porsche 911 Carrera Coupe Chassis no. WPOAA29945S620001", None, "996.2"),
    ]

    def test_cases(self):
        for year, title, vin, expected in self.CASES:
            with self.subTest(title=title, vin=vin):
                self.assertEqual(gen(year, title, vin), expected)


class TestVinModelYear(unittest.TestCase):
    """European lots are titled by production year; the VIN carries the model year."""
    CASES = [
        # Bonhams "2016 ... Turbo S", VIN year H = MY2017 -> 991.2
        (2016, "2016 Porsche 911 Turbo S Coupe Chassis no. WP0ZZZ99ZHS161323", None, "991.2"),
        # VIN family beats a title that names no chassis (Broad Arrow 1994 993)
        (1994, "1994 Porsche 911 Carrera Coupe", "WP0ZZZ99ZRS310663", "993"),
        # 2013 997.2 Turbo S, serial 7
        (2013, "2013 Porsche 911 Turbo S Coupe", "WP0AD2A97DS766111", "997.2"),
        # 2012 991 Carrera S, serial 1
        (2012, "2012 Porsche 911 Carrera S Coupe", "WP0AB2A92CS120608", "991.1"),
        # G-Body VIN on a lot titled by registration year
        (1990, "1990 Porsche 911 Speedster", "WP0222912KS151096", "G-Body"),
        # Bonhams "2010 GT3 RS", VIN year B = MY2011 -> still 997.2
        (2010, "2010 Porsche 911 GT3 RS", "WPOZZZ99ZBS780358", "997.2"),
        # A VIN two+ years off the lot is a typo: ignored
        (2008, "2008 Porsche 911 GT2", "WP0AD29935S778090", "997.1"),
        # An invalid character (I) means no VIN
        (2018, "2018 Porsche 911 GT3", "WP0AC2A9XJSI76242", "991.2"),
        # Porsche Classic: GT3 (2009-12) is the 3.8 997.2; GT3 RS (2007-2009) is 997.1
        (2009, "2009 Porsche 911 GT3", None, "997.2"),
        (2009, "2009 Porsche 911 GT3 RS", None, "997.1"),
    ]

    def test_cases(self):
        for year, title, vin, expected in self.CASES:
            with self.subTest(title=title, vin=vin):
                self.assertEqual(gen(year, title, vin), expected)


class TestCarrera4Boundary(unittest.TestCase):
    def test_40th_anniversary_is_not_a_carrera_4(self):
        pats = ["Carrera 4S", "Carrera 4", "Carrera S", "Carrera"]
        self.assertEqual(match_variant(pats, "2004 Porsche 911 Carrera 40th Anniversary"), "Carrera")
        self.assertEqual(match_variant(pats, "2004 Porsche 911 Carrera 4 Cabriolet"), "Carrera 4")
        self.assertEqual(match_variant(pats, "2004 Porsche 911 Carrera 4S"), "Carrera 4S")

    def test_carrera_4_gts_is_a_gts(self):
        pats = ["Carrera 4S", "Carrera 4", "Carrera S", "Carrera GTS", "Carrera"]
        self.assertEqual(match_variant(pats, "2011 Porsche 911 Carrera 4 GTS Coupé"), "Carrera GTS")


if __name__ == "__main__":
    unittest.main()
