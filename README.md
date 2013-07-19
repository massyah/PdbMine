PdbMine: Mining the PDB database jointly with MEDLINE
========================================================

Accompanying code and databases for Article _Timely deposition of macromolecular structures is necessary for peer review_, by Robbie P. Joosten, Hayssam Soueidan, Lodewyk Wessels and Anastassis Perrakis. 

This study starts with a list of PDB entries that you want to analyze. For the article, we took all PDB entries listed on [the PDB website](http://www.rcsb.org/pdb/home/home.do) as of the 01st June 2013. Based on these entries, the corresponding MEDLINE entries are downloaded parsed and both the PDB and the MEDLINE entries are stored in a local SQLite3 database. 



# Getting the list of PDB entries 

The PDB webservices are a bit troublesome to navigate in. The easiest way to get every entry with a corresponding 'citation' (e.g. a MEDLINE indexed article) is to use [advanced seach](http://www.rcsb.org/pdb/search/advSearch.do). 

Select "Citation" as a query type, then check filter to only keep "Primary citation", check the count, generate the results. Once results have been generated, export the table as a "Primary citation report". 

# Getting the PDB entries

We get them from the PDB ftp site. 

Run [pdb-get-multi-thread.py](pdb-get-multi-thread.py), pointing to the correct list of PDB entries (first lines, CITATIONFILE variable)

Adjust the number of threads available depending on the machine used. 

Clean the pdb-entries folder by removing any empty file:

    find . -type f -empty | xargs rm


# Inserting the entries in a local SQLite3 databases
Once the entries have been downloaded, we run [medline-get.py](medline-get.py) then :

    pdb_store_entries_not_in_db()
    get_medlines_for_pdbs() # Takes a while, as this will download all entries from MEDLINE corresponding to PDB entries 



# Date processing 
Once entries have been processed, parsed and inserted in the database, we compute the earliestpublication and earliestpublicdate by sourcing [medline-get.py](medline-get.py) and then :

    correct_ahead_of_print()
    add_earliest_public_date()
    add_earliest_publication_date()



Results from these steps are stored in the provided [SQLite database:local-medline-pdb.db](local-medline-pdb.db). For convenience, the joined databaes are available as an R data.frame (actually [data.tables](http://cran.r-project.org/web/packages/data.table/index.html)) in [data/pdb.medline.RData](data/pdb.medline.RData)
# Analysis
All data aggregations and figure generation are performed in R and are described in [deposit_time_analysis.Rmd](deposit_time_analysis.Rmd)


# Impact factor table 

For copyright reasons, this table cannot be made available. The impact factor table that we used correponds to the 2013 Thomson Reuters estimate. 
