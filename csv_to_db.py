import cs50
import csv

# Create empty shows3.db
open("dso.db", "w").close()

# Open that file for SQLite
db = cs50.SQL("sqlite:///dso.db")

db.execute("CREATE TABLE dso (object TEXT, type TEXT, con TEXT, ra NUMERIC, dec NUMERIC, mag NUMERIC, subr NUMERIC, u2k NUMERIC,\
    ti NUMERIC, size_max TEXT, size_min TEXT, pa NUMERIC, class TEXT)")

# Open title.basics.tsv
with open("DSO_database.csv", "r") as dsos:

    # Create DictReader
    reader = csv.DictReader(dsos)

    for row in reader:
        object = row["OBJECT"]
        type = row["TYPE"]
        con = row["CON"]
        ra = row["RA"]
        dec = row["DEC"]
        mag = row["MAG"]
        subr = row["SUBR"]
        u2k = row["U2K"]
        ti = row["TI"]
        size_max = row["SIZE_MAX"]
        size_min = row["SIZE_MIN"]
        pa = row["PA"]
        classification = row["CLASS"]

        db.execute("INSERT INTO dso (object, type, con, ra, dec, mag, subr, u2k, ti, size_max, size_min, pa, class) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        object, type, con, ra, dec, mag, subr, u2k, ti, size_max, size_min, pa, classification)
