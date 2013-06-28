PdbMine:Mining the PDB database jointly with MEDLINE
=======

# Getting the list of PDB entries 

The PDB webservices are a bit troublesome to navigate in. The easiest way to get every entry with a corresponding citation is to use [advanced seach](http://www.rcsb.org/pdb/search/advSearch.do). 

Select "Citation" as a query type, then check filter to only keep "Primary citation", check the count, generate the results. Once results have been generated, export the table as a "Primary citation report". 

# Getting the PDB entries

We get them from the PDB ftp site. 

Run pdb-get-multi-thread.py, pointing to the correct list of PDB entries (first lines, CITATIONFILE variable)

Adjust the number of threads available depending on the machine used. 


# Cleaning the data 

* Journal names 